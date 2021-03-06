#!/usr/bin/env python

# Copyright (c) 2019 Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import argparse
import keystone_common
import glance_common
import neutron_common
import cinder_common
import utils
import time
from auth_stack2 import AuthStack
from novaclient.client import exceptions as nova_exc
import traceback




def get_nova(destination):
    auth = AuthStack()
    client = auth.get_nova_client(destination)
    return client


def get_security_groups(destination):
    nova = get_nova(destination)
    groups = nova.security_groups.list()
    return groups


def print_security_groups(destination):
    groups = get_security_groups(destination)
    groups.sort(key=lambda x: x.name)
    newlist = sorted(groups, key=lambda x: x.name)
    print "Name:                  Description:"
    for group in newlist:
        print '{:20}'.format(group.name), " ", group.description


def compare_and_create_security_groups():
    from_groups = get_security_groups('from')
    to_groups = get_security_groups('to')
    # print from_groups
    # print to_groups

    new_groups = []
    from_names = map(lambda from_groups: from_groups.name, from_groups)
    to_names = map(lambda to_groups: to_groups.name, to_groups)
    for name in from_names:
        if name not in to_names:
            from_group = filter(lambda from_groups: from_groups.name == name, from_groups)
            to_group = create_security_group('to', from_group[0])
            group_pair = {'old': from_group[0], 'new': to_group}
            new_groups.append(group_pair)
    for new_group in new_groups:
        create_security_rules('to', new_group['old'], new_group['new'], new_groups)


def create_migration_security_group(destination):
    nova = get_nova(destination)
    new_group = nova.security_groups.create(name='migration', description='Allow all ingress traffic during migration')
    print "Added migration security group"
    tcp_rule = nova.security_group_rules.create(parent_group_id=new_group.id, ip_protocol='tcp',
                                            from_port=1, to_port=65535)
    print "Added allow all TCP ingress traffic rule to migration security group"
    udp_rule = nova.security_group_rules.create(parent_group_id=new_group.id, ip_protocol='udp',
                                                from_port=1, to_port=65535)
    print "Added allow all UDP ingress traffic rule to migration security group"

    icmp_rule = nova.security_group_rules.create(parent_group_id=new_group.id, ip_protocol='icmp',
                                                from_port=-1, to_port=-1)
    print "Added allow all ICMP ingress traffic rule to migration security group"


    return new_group


def create_security_group(destination, from_group):
    #print from_group.rules
    nova = get_nova(destination)
    to_group = nova.security_groups.create(name=from_group.name, description=from_group.description)
    #print to_group
    #need to create rules after all the groups are created since rules can use groups.
    #create_security_rules(destination, from_group, to_group)
    #print to_group.rules
    print "Security group ", to_group.name, "created."
    return to_group


#{u'from_port': None, u'group': {u'tenant_id': u'19fb979c91c54817a6c76c9e74e23cdd', u'name': u'default'}, u'ip_protocol': None, u'to_port': None, u'parent_group_id': u'e0bf1497-3bbc-4ad5-bed7-de25cc4f4eab', u'ip_range': {}, u'id': u'6c31bbf0-ef53-4091-933a-357fc7625212'}
def create_security_rules(destination, from_group, to_group, new_groups):
    nova = get_nova(destination)

    if from_group.rules:
        for rule in from_group.rules:
            try:
                if 'name' in rule['group']:
                    named_group = find_group_by_name('to', rule['group']['name'])
                    if 'ip_range' in rule:
                        if 'cidr' in rule['ip_range']:
                            cidras = rule['ip_range']['cidr']
                            rule = nova.security_group_rules.create(parent_group_id=to_group.id, ip_protocol=rule['ip_protocol'],
                                                                    from_port=rule['from_port'], to_port=rule['to_port'],
                                                                    cidr=cidras, group=named_group.id)
                            # print rule
                        else:
                            group_id = find_new_group_id_by_group_name(new_groups, rule['group']['name'])
                            rule = nova.security_group_rules.create(parent_group_id=to_group.id, ip_protocol=rule['ip_protocol'],
                                                                    from_port=rule['from_port'], to_port=rule['to_port'],
                                                                    group_id=named_group.id)
                            # print rule
                else:
                    if 'ip_range' in rule:
                        if 'cidr' in rule['ip_range']:
                            cidras = rule['ip_range']['cidr']
                            rule = nova.security_group_rules.create(parent_group_id=to_group.id, ip_protocol = rule['ip_protocol'],
                                                            from_port = rule['from_port'], to_port=rule['to_port'], cidr=cidras)#,
                            # print rule
                        else:
                            group_id = find_new_group_id_by_group_name(new_groups, rule['group']['name'])
                            rule = nova.security_group_rules.create(parent_group_id=to_group.id, ip_protocol=rule['ip_protocol'],
                                                                    from_port=rule['from_port'], to_port=rule['to_port'])
                            # print rule
            except Exception, e:
                print "Trying to create rule ", e


def update_default_group_rules():
    from_groups = get_security_groups('from')
    to_groups = get_security_groups('to')
    from_default = get_default_group(from_groups)
    to_default = get_default_group(to_groups)
    new_groups = []
    group_pair = {'old': from_default, 'new': to_default}
    new_groups.append(group_pair)
    create_security_rules('to', from_default, to_default, new_groups)


def update_all_group_rules():
    from_groups = get_security_groups('from')
    to_groups = get_security_groups('to')
    for from_group in from_groups:
        to_group = get_group_by_name(to_groups, from_group.name)
        new_groups = []
        group_pair = {'old': from_group, 'new': to_group}
        new_groups.append(group_pair)
        create_security_rules('to', from_group, to_group, new_groups)


def get_default_group(groups):
    for group in groups:
        if group.name == 'default':
            return group


# def get_group_by_name(groups, name):
#     for group in groups:
#         if group.name == name:
#             return group


def find_oppposite_group_name_by_id(from_group_id):
    from_nova = get_nova('from')
    from_group = from_nova.security_groups.get(from_group_id)
    to_groups = get_security_groups('to')
    for to_g in to_groups:
        if to_g.name == from_group.name:
            return to_g

    return None


def get_group_by_name(groups, name):
    for group in groups:
        if group.name == name:
            return group
    return None


def find_group_by_name(destination, name):
    groups = get_security_groups(destination)
    group = get_group_by_name(groups, name)
    return group


# Rules that include other groups do not have group id, only name. So, we must find
# group id based on its name. This will not work if there are duplicate group names...
def find_new_group_id_by_group_name(group_pairs, name):
    for pair in group_pairs:
        if pair['old'].name == name:
            return pair['new'].id


def get_vm_list(destination):
    nova = get_nova(destination)
    #network = neutron_common.get_network_by_name('to', 'foobar1')
    #print network[0]
    # servers = nova.servers.list(search_opts={'all_tenants':'1'})
    servers = nova.servers.list()
    # for s in servers:
        #server = nova.servers.get(s.id)
        #print server
        #print s
        #print s.networks
        #print s.addresses
        #for key in s.addresses:
        #print key
    return servers


def print_vm_list_ids(destination):
    vms = get_vm_list(destination)
    vms.sort(key=lambda x: x.status)
    newlist = sorted(vms, key=lambda x: x.status)

    print "VMs sorted by status (id status flavor_id name):"
    for vm in newlist:
        print vm.id, " ", vm. status, " ", vm.flavor['id'], vm.name


def print_vm_list_ids_without_volumes(destination):
    vms = get_vms_without_volumes(destination)
    vms.sort(key=lambda x: x.status)
    newlist = sorted(vms, key=lambda x: x.status)

    print "VMs without volumes sorted by status (id status flavor_id name):"
    for vm in newlist:
        print vm.id, " ", vm.status, " ", vm.flavor['id'], vm.name


def print_vm_list_ids_without_bootable_volumes(destination):
    vms = get_vms_without_boot_volumes(destination)
    vms.sort(key=lambda x: x.status)
    newlist = sorted(vms, key=lambda x: x.status)

    print "VMs without bootable volumes sorted by status (id status flavor_id name):"
    for vm in newlist:
        print vm.id, " ", vm.status, " ", vm.flavor['id'], vm.name


def print_vm_list_ids_with_bootable_volumes(destination):
    vms = get_vms_with_boot_volumes(destination)
    vms.sort(key=lambda x: x.status)
    newlist = sorted(vms, key=lambda x: x.status)

    print "VMs with bootable volumes sorted by status (id status flavor_id name):"
    for vm in newlist:
        print vm.id, " ", vm.status, " ", vm.flavor['id'], vm.name


def print_flavor_list(destination):
    to_flavors = get_flavor_list(destination)
    for f in to_flavors:
        print '{:5}'.format(f.id), f.name

# todo: check that it is not used and remove
# def compare_and_create_vms():
#     from_vms = get_vm_list('from')
#     to_vms = get_vm_list('to')
#     from_names = map(lambda from_vms: from_vms.name, from_vms)
#     to_names = map(lambda to_vms: to_vms.name, to_vms)
#     for name in from_names:
#         if name not in to_names:
#             from_vm_list = filter(lambda from_vms: from_vms.name == name, from_vms)
#             for from_vm in from_vm_list:
#                 #print from_vm
#
#                 create_vm(from_vm)
            #new_flavor = create_flavor('to', from_flavor[0])
            #new_flavor.set_keys(from_flavor[0].get_keys())
            #print "New flavor created: "
            #print new_flavor


# todo: add try catch for when multiple security groups are present.
# client lets add groups by name only...
def create_vm(from_vm, image='default', hypervisor_order=None):
    nova = get_nova('to')
    auth = AuthStack()
    # flavor = get_flavor_by_id('to', from_vm.flavor['id'])
    flavor = get_flavor_by_name('to', from_vm.flavor['id'])
    if flavor is None:
        print "Error: Cannot continue for this VM without proper flavor"
        return None
    if image == 'default':
        image = glance_common.get_image_by_original_id('to', from_vm.image['id'])
    interfaces = from_vm.interface_list()
    macs = utils.get_macs_from_libvirt(auth.nfs_libvirt_location + from_vm.id)
    networks = from_vm.networks
    ordered_interfaces = neutron_common.order_ports_by_macs(macs, interfaces)

    # for interface in interfaces:
    #     print '{:16}'.format(server.name), '{:38}'.format(server.id), '{:38}'.format(interface.port_id), \
    #         '{:10}'.format(interface.port_state), '{:18}'.format(interface.mac_addr),
    #     for ip in interface.fixed_ips:
    #         print '{:16}'.format(ip['ip_address'])

    nics = []
    hypervisor = None
    if hypervisor_order:
        for hyp in hypervisor_order:
            if hyp['uuid'] == from_vm.id:
                hypervisor = 'nova::'+ hyp['hyp']
                break

    for interface in ordered_interfaces:
        for ip in interface.fixed_ips:
            port = neutron_common.find_port_by_ip('to', ip['ip_address'])
            # nic = {'net-id': net['id'], 'v4-fixed-ip': ip}
            if port:
                if not port['device_owner'].startswith('network:floatingip'):
                    nic = {'port-id': port['id']}
                    nics.append(nic)
            else:
                # todo: VIPS?
                # from_port = neutron_common.find_port_by_ip('from', ip)
                # new_port = neutron_common.create_ip_ports('to', from_port)
                # nic = {'port-id': new_port['port']['id']}
                # nics.append(nic)
                net = neutron_common.find_corresponding_network_name_by_id(interface.net_id)
                nic = {'net-id': net['id'], 'v4-fixed-ip': ip['ip_address']}
                nics.append(nic)

    # for network, nets in networks.iteritems():
    #     for ip in nets:
    #         # print nets
    #         port = neutron_common.find_port_by_ip('to', ip)
    #         # nic = {'net-id': net['id'], 'v4-fixed-ip': ip}
    #         if port:
    #             if not port['device_owner'].startswith('network:floatingip'):
    #                 nic = {'port-id': port['id']}
    #                 nics.append(nic)
    #         else:
    #             #todo: VIPS?
    #             # from_port = neutron_common.find_port_by_ip('from', ip)
    #             # new_port = neutron_common.create_ip_ports('to', from_port)
    #             # nic = {'port-id': new_port['port']['id']}
    #             # nics.append(nic)
    #             net = neutron_common.get_network_by_name('to', network)
    #             nic = {'net-id': net['id'], 'v4-fixed-ip': ip}
    #             nics.append(nic)

    print "nics"
    print nics
    metadata = from_vm.metadata
    metadata.update({'original_vm_id':from_vm.id})

    #include original image info as metadata:
    try:
        img = glance_common.get_image('from', from_vm.image['id'])
        metadata.update({'original_image_id': img.id})
        metadata.update({'original_image_name': img.name})
    except Exception, e:
        print "No original image info for this VM"
        metadata.update({'original_image_id': "not found"})
        metadata.update({'original_image_name': "not found"})

    scheduler_hints = find_server_group_by_old_uuid(from_vm.id)
    print "Scheduler hint:", scheduler_hints
    #attaching security groups during server creation does not seem to work, so moved to a separate task
    keypairs = get_keypairs('to')
    key_name = from_vm.key_name
    found = False
    for key in keypairs:
        if key.name == key_name:
            found = True
            break
    if found:
        server = nova.servers.create(name=from_vm.name, image=image, flavor=flavor.id, nics=nics,
                                 meta=metadata, key_name=key_name, availability_zone=hypervisor, scheduler_hints=scheduler_hints)
    else:
        server = nova.servers.create(name=from_vm.name, image=image, flavor=flavor.id, nics=nics,
                                     meta=metadata, availability_zone=hypervisor, scheduler_hints=scheduler_hints)

    print "Server created:", from_vm.name


def create_vm_with_network_mapping(from_vm, image='default', network_name='none'):
    nova = get_nova('to')

    flavor = get_flavor_by_name('to', from_vm.flavor['id'])
    if flavor is None:
        print "Error: Cannot continue for this VM without proper flavor"
        return None
    if image == 'default':
        image = glance_common.get_image_by_original_id('to', from_vm.image['id'])
    # networks = from_vm.networks

    net = neutron_common.get_network_by_name('to', network_name)
    nics = [{'net-id': net['id'] }]

    #include original image info as metadata:
    img = glance_common.get_image('from', from_vm.image['id'])
    metadata = from_vm.metadata
    metadata.update({'original_vm_id':from_vm.id})
    metadata.update({'original_image_id': img.id})
    metadata.update({'original_image_name': img.name})
    #attaching security groups during server creation does not seem to work, so moved to a separate task
    server = nova.servers.create(name=from_vm.name, image=image, flavor=flavor.id, nics=nics,
                                 meta=metadata, key_name=from_vm.key_name)
    print "Server created:", server.name
    return server


def create_vm_from_volume_with_network_mapping(from_vm, volume, network_name='none', key='default', user_data='default'):
    nova = get_nova('to')

    flavor = get_flavor_by_name('to', from_vm.flavor['id'])
    if flavor is None:
        print "Error: Cannot continue for this VM without proper flavor"
        return None
    # if image == 'default':
    #     image = glance_common.get_image_by_original_id('to', from_vm.image['id'])
    # networks = from_vm.networks

    net = neutron_common.get_network_by_name('to', network_name)
    nics = [{'net-id': net['id'] }]

    #include original image info as metadata:
    metadata = from_vm.metadata
    metadata.update({'original_vm_id':from_vm.id})
    # metadata.update({'original_volume_id': volume.id})
    # metadata.update({'original_image_name': img.name})

    #attaching security groups during server creation does not seem to work, so moved to a separate task

    # block_device_mapping = {'vda':'uuid of the volume you want to use'}
    block_device_mapping = {volume.metadata['original_device']: volume.id}

    print block_device_mapping
    if key == 'default':
        key = from_vm.key_name
        server = nova.servers.create(name=from_vm.name, image="", flavor=flavor.id, block_device_mapping=block_device_mapping, nics=nics,
                                     meta=metadata, key_name=key, userdata=user_data)
    else:
        server = nova.servers.create(name=from_vm.name, image="", flavor=flavor.id,
                                     block_device_mapping=block_device_mapping, nics=nics,
                                     meta=metadata, key_name=key, userdata=user_data)
    print "Server created:", server.name
    return server


def create_vm_from_volume_with_network_mapping_no_original_device(from_vm, volume, network_name='none', key='default', user_data='default'):
    nova = get_nova('to')

    flavor = get_flavor_by_name('to', from_vm.flavor['id'])
    if flavor is None:
        print "Error: Cannot continue for this VM without proper flavor"
        return None

    net = neutron_common.get_network_by_name('to', network_name)
    nics = [{'net-id': net['id'] }]

    #include original image info as metadata:
    metadata = from_vm.metadata
    metadata.update({'original_vm_id':from_vm.id})

    #attaching security groups during server creation does not seem to work, so moved to a separate task

    # block_device_mapping = {'vda':'uuid of the volume you want to use'}
    block_device_mapping = {'/dev/vda': volume.id}

    # print block_device_mapping
    if key == 'default':
        key = from_vm.key_name
        server = nova.servers.create(name=from_vm.name, image="", flavor=flavor.id, nics=nics, block_device_mapping=block_device_mapping,
                                     meta=metadata, key_name=key, userdata=user_data)
    else:
        server = nova.servers.create(name=from_vm.name, image="", flavor=flavor.id,
                                     block_device_mapping=block_device_mapping, nics=nics,
                                     meta=metadata, key_name=key, userdata=user_data)
    print "Server created:", server.name
    return server


def create_vm_from_image_with_network_mapping(from_vm, image, network_name='none', key='default', user_data='default'):
    nova = get_nova('to')

    flavor = get_flavor_by_name('to', from_vm.flavor['id'])
    if flavor is None:
        print "Error: Cannot continue for this VM without proper flavor"
        return None
    # if image == 'default':
    #     image = glance_common.get_image_by_original_id('to', from_vm.image['id'])
    # networks = from_vm.networks

    net = neutron_common.get_network_by_name('to', network_name)
    nics = [{'net-id': net['id'] }]

    #include original image info as metadata:
    metadata = from_vm.metadata
    metadata.update({'original_vm_id':from_vm.id})
    # metadata.update({'original_volume_id': volume.id})
    # metadata.update({'original_image_name': img.name})

    if key == 'default':
        key = from_vm.key_name
        server = nova.servers.create(name=from_vm.name, image=image, flavor=flavor.id, nics=nics,
                                     meta=metadata, key_name=key, userdata=user_data)
    else:
        server = nova.servers.create(name=from_vm.name, image=image, flavor=flavor.id, nics=nics,
                                     meta=metadata, key_name=key, userdata=user_data)
    print "Server created:", server.name
    return server


def attach_security_groups(id_file):
    # ready = check_vm_are_on('to', id_file)
    # if ready:
    ids = utils.read_ids_from_file(id_file)
    nova = get_nova('from')
    for uuid in ids:
        try:
            old_server = nova.servers.get(uuid)
            new_server = get_vm_by_original_id('to', uuid)
            groups = old_server.security_groups
            set_groups = set(map(lambda d: d['name'], groups))
            print "Attaching security groups to:", new_server.name
            for group in set_groups:
                try:
                    new_server.add_security_group(group)
                except Exception, e:
                    if str(e).find("Duplicate items in the list"):
                        print "Server has security group", group
                    else:
                        print "Group:", group
                        print "Something happened while trying to attach security group. Moving to the next group. " + str(e)
        except Exception, e:
            print str(e)
    # else:
    #     print "All VMs must be powered on for this action to proceed"


# Attaches special migration security group that allows VMs
# on FROM and TO environments communicate during the migration.
# This group should be removed after the migration.
def attach_security_migration_group(id_file):
    ids = utils.read_ids_from_file(id_file)
    nova = get_nova('from')
    for uuid in ids:
        try:
            group = find_group_by_name('to', 'migration')
            if not group:
                group = create_migration_security_group('to')
            new_server = get_vm_by_original_id('to', uuid)
            print "Attaching migration security group to:", new_server.name
            new_server.add_security_group('migration')
        except Exception, e:
            if str(e).find("Duplicate items in the list"):
                print "Server has migration group."
            else:
                print str(e)


def attach_volumes(id_file):
    # ready = check_vm_are_on('to', id_file)
    nova = get_nova("to")

    # if ready:
    ids = utils.read_ids_from_file(id_file)
    for uuid in ids:
        try:
            vm = get_vm_by_original_id('to', uuid)
            to_volumes = cinder_common.get_volume_list_by_vm_id("to", uuid)
            for to_v in to_volumes:
                if 'image_name' in to_v.metadata:
                    print "this volume was a vm image, do not attach", to_v.metadata['image_name']
                else:
                    if not to_v.attachments:
                        # print to_v.metadata['original_device']
                        nova.volumes.create_server_volume(vm.id, to_v.id, to_v.metadata['original_device'])
                        print "Volume id: " + to_v.id + " attached to VM id: " + vm.id

        except Exception, e:
            print str(e)
            traceback.print_exc()
    # else:
    #     print "All VMs must be powered on for this action to proceed"


def migrate_vms_from_image(id_file, hypervisor_order_file=None):
    ids = utils.read_ids_from_file(id_file)
    hypervisor_order = None
    if hypervisor_order_file:
        hypervisor_order = utils.read_ids_with_hyps_file(hypervisor_order_file)
    nova_from = get_nova("from")
    to_vms = get_vm_list('to')

    for uuid in ids:
        try:
            server = nova_from.servers.get(uuid)
            if server.status == 'SHUTOFF':
                print "Finding image for server with UUID:", uuid
                new_name = "migration_vm_image_" + server.id
                # print new_name
                image = glance_common.get_image_by_name("to", new_name)
                if image:
                    print "Found image with name: ", image.name
                    # need to check for VMs that were already re-created on the TO side:
                    dup_vms = filter(lambda to_vms: to_vms.name == server.name, to_vms)
                    duplicate = False
                    for dup in dup_vms:
                        if 'original_vm_id' in dup.metadata:
                            if dup.metadata['original_vm_id'] == server.id:
                                print "Duplicate VM on TO side already found, skipping VM:", server.name, server.id
                                duplicate = True
                    if duplicate is False:
                        create_vm(server, image=image, hypervisor_order=hypervisor_order)
                else:
                    print "Did not find image in 'to' environment with name:", new_name
            else:
                print "1 Server with UUID:", uuid, " is not shutoff. It must be in SHUTOFF status for this action."
        except nova_exc.NotFound:
            print "2 Server with UUID", uuid, "not found"
            print str(nova_exc)
            traceback.print_exc()


def migrate_vms_from_image_with_network_mapping(id_file, custom_network='none'):
    ids = utils.read_ids_from_file(id_file)
    nova_from = get_nova("from")
    to_vms = get_vm_list('to')

    for uuid in ids:
        try:
            server = nova_from.servers.get(uuid)
            if server.status == 'SHUTOFF':
                print "Finding image for server with UUID:", uuid
                new_name = "migration_vm_image_" + server.id
                # print new_name
                image = glance_common.get_image_by_name("to", new_name)
                if image:
                    print "Found image with name: ", image.name
                    # need to check for VMs that were already re-created on the TO side:
                    dup_vms = filter(lambda to_vms: to_vms.name == server.name, to_vms)
                    duplicate = False
                    for dup in dup_vms:
                        if 'original_vm_id' in dup.metadata:
                            if dup.metadata['original_vm_id'] == server.id:
                                print "Duplicate VM on TO side already found, skipping VM:", server.name, server.id
                                duplicate = True
                    if duplicate is False:
                        create_vm_with_network_mapping(server, image=image, network_name=custom_network)
                else:
                    print "Did not find image in 'to' environment with name:", new_name
            else:
                print "1 Server with UUID:", uuid, " is not shutoff. It must be in SHUTOFF status for this action."
        except nova_exc.NotFound:
            print "2 Server with UUID", uuid, "not found"


def boot_from_volume_vms_from_image_with_network_mapping(id_file, custom_network='none', key='default', user_data='default'):
    ids = utils.read_ids_from_file(id_file)
    nova_from = get_nova("from")
    to_vms = get_vm_list('to')

    for uuid in ids:
        try:
            server = nova_from.servers.get(uuid)
            # if server.status == 'SHUTOFF':
            if server.__dict__['os-extended-volumes:volumes_attached']:
                print "Verifying Volumes for VM ID: " + uuid
                from_vols = server.__dict__['os-extended-volumes:volumes_attached']
                # for vol in from_volumes:
                #     print vol['id']
                #     from_vols = "foo"
                from_volumes = cinder_common.get_volumes_from_vm_attachment_list("from", from_vols)
                #these need to be in place!
                to_volumes = cinder_common.verify_to_vm_volumes(uuid, from_volumes)
                boot_volume = cinder_common.find_bootable_volume(to_volumes)
                if boot_volume:
                    #     # need to check for VMs that were already re-created on the TO side:
                    dup_vms = filter(lambda to_vms: to_vms.name == server.name, to_vms)
                    duplicate = False
                    for dup in dup_vms:
                        if 'original_vm_id' in dup.metadata:
                            if dup.metadata['original_vm_id'] == server.id:
                                print "Duplicate VM on TO side already found, skipping VM:", server.name, server.id
                                duplicate = True
                    if duplicate is False:
                        create_vm_from_volume_with_network_mapping(server, volume=boot_volume, network_name=custom_network, key=key, user_data=user_data)
            else:
                print "Original VM doesn't have volumes attached, cannot proceed to launch new VM from volume"
            # else:
            #     print "1 Server with UUID:", uuid, " is not shutoff. It must be in SHUTOFF status for this action."
        except nova_exc.NotFound:
            print "2 Server with UUID", uuid, "not found"


def boot_from_volume_vms_with_network_mapping(id_file, custom_network='none', key='default', user_data='default'):
    ids = utils.read_ids_from_file(id_file)
    nova_from = get_nova("from")
    to_vms = get_vm_list('to')

    for uuid in ids:
        try:
            server = nova_from.servers.get(uuid)
            # if server.status == 'SHUTOFF':
            if server:
                volumes = cinder_common.get_volume_list_by_vm_id('to', uuid)
                boot_volume = None
                for vol in volumes:
                    if vol.name.startswith('migration_vm_image_'):
                        boot_volume = vol
                if boot_volume:
                    dup_vms = filter(lambda to_vms: to_vms.name == server.name, to_vms)
                    duplicate = False
                    for dup in dup_vms:
                        if 'original_vm_id' in dup.metadata:
                            if dup.metadata['original_vm_id'] == server.id:
                                print "Duplicate VM on TO side already found, skipping VM:", server.name, server.id
                                duplicate = True
                    if duplicate is False:
                        create_vm_from_volume_with_network_mapping_no_original_device(server, volume=boot_volume,
                                                                   network_name=custom_network, key=key,
                                                                   user_data=user_data)

                else:
                    print 'boot volume not found'

            # else:
            #     print "1 Server with UUID:", uuid, " is not shutoff. It must be in SHUTOFF status for this action."
        except nova_exc.NotFound:
            print "2 Server with UUID", uuid, "not found"


def boot_from_vms_from_image_with_network_mapping(id_file, custom_network='none', key='default', user_data='default'):
    ids = utils.read_ids_from_file(id_file)
    nova_from = get_nova("from")
    to_vms = get_vm_list('to')

    for uuid in ids:
        try:
            server = nova_from.servers.get(uuid)
            if server.status == 'SHUTOFF':
                image_name = "migration_vm_image_" + server.id
                image = glance_common.get_image_by_name('to', image_name)
                #     # need to check for VMs that were already re-created on the TO side:
                dup_vms = filter(lambda to_vms: to_vms.name == server.name, to_vms)
                duplicate = False
                for dup in dup_vms:
                    if 'original_vm_id' in dup.metadata:
                        if dup.metadata['original_vm_id'] == server.id:
                            print "Duplicate VM on TO side already found, skipping VM:", server.name, server.id
                            duplicate = True
                if duplicate is False:
                    create_vm_from_image_with_network_mapping(server, image, network_name=custom_network, key=key, user_data=user_data)

            else:
                print "1 Server with UUID:", uuid, " is not shutoff. It must be in SHUTOFF status for this action."
        except nova_exc.NotFound:
            print "2 Server with UUID", uuid, "not found"


def get_flavor_by_id(destination, flavor_id):
    try:
        nova = get_nova(destination)
        fl = nova.flavors.get(flavor=flavor_id)
        # fpp = nova.flavor_access.list(flavor=flavor_id)
        # print fpp
        return fl
    except Exception, e:
        print str(e)
        print "Error: Flavor with ID:", flavor_id, "could not be found"
        return None


def get_flavor_by_name(destination, flavor_id):
    try:
        from_nova = get_nova("from")
        nova = get_nova("to")
        flavor = get_flavor_by_id("from", flavor_id)
        name = flavor.name
        flavors = nova.flavors.list()
        for fl in flavors:
            if fl.name == name:
                return fl
    except Exception, e:
        print str(e)
        print "Error: Flavor with name:", name, "could not be found"
        return None


# nova flavor-list --all for checking all flavors for admin, private and public
def get_flavor_list(destination):
    nova = get_nova(destination)

    # There is no api flag for "--all", so need to make separate calls...
    flavors_public = nova.flavors.list(detailed=True, is_public=True)
    flavors_private = nova.flavors.list(detailed=True, is_public=False)
    for f in flavors_private:
        if f not in flavors_public:
            flavors_public.append(f)
    # flavors = flavors_private + flavors_public
    # print flavors
    return flavors_public


def compare_and_create_flavors():
    from_flavors = get_flavor_list('from')
    to_flavors = get_flavor_list('to')
    from_names = map(lambda from_flavors: from_flavors.name, from_flavors)
    to_names = map(lambda to_flavors: to_flavors.name, to_flavors)
    for name in from_names:
        if name not in to_names:
            from_flavor = filter(lambda from_flavors: from_flavors.name == name, from_flavors)
            new_flavor = create_flavor('to', from_flavor[0])
            new_flavor.set_keys(from_flavor[0].get_keys())
            print "New flavor created:", new_flavor.name


def create_flavor(destination, flavor):
    nova = get_nova(destination)
    swap = 0
    if isinstance(flavor.swap, (int, long)):
        swap = flavor.swap

    new_flavor = nova.flavors.create(name=flavor.name,
                                     ram=flavor.ram,
                                     vcpus=flavor.vcpus,
                                     disk=flavor.disk,
                                     flavorid=flavor.id,
                                     ephemeral=flavor.ephemeral,
                                     swap=swap,
                                     rxtx_factor=flavor.rxtx_factor,
                                     is_public=flavor.is_public)
    if flavor.is_public is False:
        from_nova = get_nova('from')
        access = from_nova.flavor_access.list(flavor=flavor.id)
        for acc in access:
            to_tenant = keystone_common.find_opposite_project_id(acc.tenant_id)
            nova.flavor_access.add_tenant_access(flavor=new_flavor.id, tenant=to_tenant['to_id'])
    return new_flavor


def get_quotas(destination, tenant):
    nova = get_nova(destination)
    quotas = nova.quotas.defaults(tenant)
    #print quotas
    return quotas


def compare_and_report_quotas():
    from_tenants = keystone_common.get_from_project_list()
    print "Differences in individual quotas for each project:"
    for from_tenant in from_tenants:

        from_quotas = get_quotas('from', from_tenant.id)
        to_tenant = keystone_common.find_opposite_project_id(from_tenant.id)
        to_quotas = get_quotas('to', to_tenant['to_id'])
        print "\nFrom project id:", from_tenant.id, "To project id:", to_tenant['to_id']
        compare_quotas(from_quotas, to_quotas)


def compare_quotas(from_quotas, to_quotas):

    if from_quotas.instances != to_quotas.instances:
        print "From instance quota: ", from_quotas.instances
        print "To instance quota: ", to_quotas.instances
    if from_quotas.cores != to_quotas.cores:
        print "From cores quota: ", from_quotas.cores
        print "To cores quota: ", to_quotas.cores
    if from_quotas.ram != to_quotas.ram:
        print "From ram quota: ", from_quotas.ram
        print "To ram quota: ", to_quotas.ram
    if from_quotas.floating_ips != to_quotas.floating_ips:
        print "From floating_ips quota: ", from_quotas.floating_ips
        print "To floating_ips quota: ", to_quotas.floating_ips
    if from_quotas.fixed_ips != to_quotas.fixed_ips:
        print "From fixed_ips quota: ", from_quotas.fixed_ips
        print "To fixed_ips quota: ", to_quotas.fixed_ips
    if from_quotas.metadata_items != to_quotas.metadata_items:
        print "From metadata_items quota: ", from_quotas.metadata_items
        print "To metadata_items quota: ", to_quotas.metadata_items
    if from_quotas.injected_files != to_quotas.injected_files:
        print "From injected_files quota: ", from_quotas.injected_files
        print "To injected_files quota: ", to_quotas.injected_files
    if from_quotas.injected_file_content_bytes != to_quotas.injected_file_content_bytes:
        print "From injected_file_content_bytes quota: ", from_quotas.injected_file_content_bytes
        print "To injected_file_content_bytes quota: ", to_quotas.injected_file_content_bytes
    if from_quotas.injected_file_path_bytes != to_quotas.injected_file_path_bytes:
        print "From injected_file_path_bytes quota: ", from_quotas.injected_file_path_bytes
        print "To injected_file_path_bytes quota: ", to_quotas.injected_file_path_bytes
    if from_quotas.key_pairs != to_quotas.key_pairs:
        print "From key_pairs quota: ", from_quotas.key_pairs
        print "To key_pairs quota: ", to_quotas.key_pairs
    if from_quotas.security_groups != to_quotas.security_groups:
        print "From security_groups quota: ", from_quotas.security_groups
        print "To security_groups quota: ", to_quotas.security_groups
    if from_quotas.security_group_rules != to_quotas.security_group_rules:
        print "From security_group_rules quota: ", from_quotas.security_group_rules
        print "To security_group_rules quota: ", to_quotas.security_group_rules

    return


# this does not work, see comment bellow.
def compare_and_update_quotas():
    from_tenants = keystone_common.get_from_project_list()
    for from_tenant in from_tenants:
        print "from project id "
        print from_tenant.id
        from_quotas = get_quotas('from', from_tenant.id)
        to_tenant = keystone_common.find_opposite_project_id(from_tenant.id)
        print "to tenant_id"
        print to_tenant['to_id']
        to_quotas = get_quotas('to', to_tenant['to_id'])
       # print to_quotas
        update_quotas(from_tenant, from_quotas, to_tenant, to_quotas)


#there seems to be at least one bug related to quotas.
#i think this was fixed in for some things, but not for update through API: https://review.openstack.org/#/c/144866/
def update_quotas(from_tenant, from_quotas, to_tenant, to_quotas):
    print from_quotas
    print to_quotas

    if from_quotas.instances != to_quotas.instances:
        print from_quotas.instances
        to_quotas.update(tenant_id=to_tenant['to_id'], instances=from_quotas.instances)
        #print to_quotas
    return


# Find VM by pre-migration VM id
def get_vm_by_original_id(destination, original_id):
    vms = get_vm_list(destination)
    for vm in vms:
        if vm.metadata:
            if 'original_vm_id' in vm.metadata:
                original_vm_id = vm.metadata['original_vm_id']
                if original_vm_id == original_id:
                    return vm
    return None


def get_to_vm_list_by_original_ids(id_file):
    all_vms = get_vm_list('to')
    ids = utils.read_ids_from_file(id_file)
    vms = []
    for vm in all_vms:
        for original_id in ids:
            if 'original_vm_id' in vm.metadata:
                original_vm_id = vm.metadata['original_vm_id']
                if original_vm_id == original_id:
                    vms.append(vm)
    return vms


def get_from_vm_list_by_ids(id_file):
    all_vms = get_vm_list('from')
    ids = utils.read_ids_from_file(id_file)
    vms = []
    for vm in all_vms:
        for id in ids:
            if vm.id == id:
                vms.append(vm)
    return vms


def get_keypairs(destination):
    nova = get_nova(destination)
    keys = nova.keypairs.list()
    # print keys
    return keys


def compare_and_create_keypairs():
    from_keys = get_keypairs('from')
    to_keys = get_keypairs('to')
    from_names = map(lambda from_keys: from_keys.name, from_keys)
    to_names = map(lambda to_keys: to_keys.name, to_keys)
    for name in from_names:
        if name not in to_names:
            from_key = filter(lambda from_keys: from_keys.name == name, from_keys)
            #print from_key
            new_key = copy_public_key('to', from_key[0])
            # new_flavor.set_keys(from_flavor[0].get_keys())
            # print "New flavor created: "
            # print new_flavor


# cannot assign user since this novaclient doesn't support microversions. Microversions supported since Liberty.
def copy_public_key(destination, key):
    nova = get_nova(destination)
    new_key = nova.keypairs.create(key.name, public_key=key.public_key)
    print "Public key", new_key.name, "created."
    return new_key


def power_off_vms(destination, id_file):
    ids = utils.read_ids_from_file(id_file)
    nova = get_nova(destination)
    for uuid in ids:
        try:
            server = nova.servers.get(uuid)
            if server.status == 'ACTIVE':
                print "Shutting down server with UUID:", uuid
                server.stop()
            else:
                print "Server with UUID:", uuid, "is not running. It must be in ACTIVE status for this action."
        except nova_exc.NotFound:
            print "4 Server with UUID", uuid, "not found"


def power_on_vms(destination, id_file):
    ids = utils.read_ids_from_file(id_file)
    nova = get_nova(destination)
    for uuid in ids:
        try:
            server = nova.servers.get(uuid)
            if server.status == 'SHUTOFF':
                print "Powering on server with UUID:", uuid
                server.start()
            else:
                print "Server with UUID:", uuid, "is running. It must be in SHUTOFF status for this action."
        except nova_exc.NotFound:
            print "14 Server with UUID", uuid, "not found"


def check_vm_are_on(destination, id_file):
    ids = utils.read_ids_from_file(id_file)
    # nova = get_nova(destination)
    ready = True
    for uuid in ids:
        try:
            server = get_vm_by_original_id('to', uuid)
            # server = nova.servers.get(uuid)
            if server.status != 'ACTIVE':
                print "Server", server.name, "is not ACTIVE."
                ready = False
        except Exception, e:
                print "Server with UUID", uuid, "not found when trying to check that it is powered on"
    return ready


def check_vm_are_off(destination, id_file):
    ids = utils.read_ids_from_file(id_file)
    nova = get_nova(destination)
    ready = True
    for uuid in ids:
        try:
            server = nova.servers.get(uuid)
            if server.status != 'SHUTOFF':
                print "Server", server.name, "is not shut off."
                print "All servers in the migration ID file must be turned off for image creation to start."
                ready = False
        except nova_exc.NotFound:
            print "15 Server with UUID", uuid, "not found"
    return ready


def create_image_from_vm(destination, id_file):
    ids = utils.read_ids_from_file(id_file)
    nova = get_nova(destination)
    for uuid in ids:
        try:
            server = nova.servers.get(uuid)
            if server.status != 'SHUTOFF':
                print "Server", server.name, "is not shut off."
                print "All servers in the migration ID file must be turned off for image creation to start."
                return
        except nova_exc.NotFound:
            print "6 Server with UUID", uuid, "not found"
    for uuid in ids:
        try:
            server = nova.servers.get(uuid)
            if server.status == 'SHUTOFF':
                print "Making image from server with UUID:", uuid
                new_name = "migration_vm_image_" + server.id
                metadata = {}
                metadata.update({'original_vm_id':server.id})
                metadata.update({'original_vm_name':server.name})
                print new_name
                server.create_image(new_name, metadata)
            else:
                print "7 Server with UUID:", uuid, " is not shutoff. It must be in SHUTOFF status for this action."

            #cannot force volume attach: https://review.openstack.org/#/c/176174/

            # if server.__dict__['os-extended-volumes:volumes_attached']:
            #     print "Creating image from volume attached to the VM, volume id:"
            #     volumes = server.__dict__['os-extended-volumes:volumes_attached']
            #     for vol in volumes:
            #         print vol['id']
            #         # cinder_common.
            #         cinder_common.upload_volume_to_image_by_volume_id(destination, vol['id'])
        except nova_exc.NotFound:
            print "8 Server with UUID", uuid, "not found"


def get_volume_id_list_for_vm_ids(destination, id_file):
    ids = utils.read_ids_from_file(id_file)
    nova = get_nova(destination)
    volume_ids = []
    for uuid in ids:
        try:
            server = nova.servers.get(uuid)
            if len(server.__dict__['os-extended-volumes:volumes_attached']) > 0:
                volumes = server.__dict__['os-extended-volumes:volumes_attached']
                for vol in volumes:
                    # print vol['id']
                    volume_ids.append(vol['id'])
        except nova_exc.NotFound:
            print "9 Server with UUID", uuid, "not found"
    return volume_ids


def print_keys(destination):
    keys = get_keypairs(destination)
    for key in keys:
        print key.name


def get_volumes_for_vm(destination, vm_uuid):
    nova = get_nova(destination)
    volume_objects = []
    try:
        server = nova.servers.get(vm_uuid)
        if len(server.__dict__['os-extended-volumes:volumes_attached']) > 0:
            volumes = server.__dict__['os-extended-volumes:volumes_attached']
            for vol in volumes:
                vl = cinder_common.get_volume_by_id("from", vol['id'])
                volume_objects.append(vl)

    except nova_exc.NotFound:
        print "10 Server ", vm_uuid, "not found"
    return volume_objects


def get_vms_with_multiple_volumes(destination):
    servers = []
    vms = get_vm_list(destination)
    for vm in vms:
        if len(vm.__dict__['os-extended-volumes:volumes_attached']) > 1:
            servers.append(vm)
    return servers


def print_vm_list_with_multiple_volumes(destination):
    vms = get_vms_with_multiple_volumes(destination)

    print "VMs with multiple volumes:"
    for vm in vms:
        print vm.id, " ", vm.name, " attached volumes:"
        volumes = vm.__dict__['os-extended-volumes:volumes_attached']
        for vol in volumes:
            volume = cinder_common.get_volume_by_id(destination, vol['id'])
            vol_name = None
            if hasattr(volume, 'display_name'):
                vol_name = volume.display_name
            if hasattr(volume, 'name'):
                vol_name = volume.name
            print '{:8}'.format(" "), '{:16}'.format(volume.id), '{:12}'.format(volume.attachments[0]['device']), vol_name


def get_vms_without_volumes(destination):
    servers = []
    vms = get_vm_list(destination)
    for vm in vms:
        if len(vm.__dict__['os-extended-volumes:volumes_attached']) == 0:
            servers.append(vm)
    return servers


def get_vms_without_boot_volumes(destination):
    servers = []
    vms = get_vm_list(destination)
    for vm in vms:
        vm_has_boot = False
        if len(vm.__dict__['os-extended-volumes:volumes_attached']) == 0:
            servers.append(vm)
        elif len(vm.__dict__['os-extended-volumes:volumes_attached']) > 0:
            volumes = vm.__dict__['os-extended-volumes:volumes_attached']
            for vol in volumes:
                boot = cinder_common.is_bootable_volume(destination, vol['id'])
                if boot is True:
                    vm_has_boot = True
                    break
            if vm_has_boot is False:
                servers.append(vm)

    return servers


def get_vms_with_boot_volumes(destination):
    servers = []
    vms = get_vm_list(destination)
    for vm in vms:
        if len(vm.__dict__['os-extended-volumes:volumes_attached']) > 0:
            volumes = vm.__dict__['os-extended-volumes:volumes_attached']
            for vol in volumes:
                boot = cinder_common.is_bootable_volume(destination, vol['id'])
                if boot is True:
                    servers.append(vm)
    return servers


# Find VMs with cinder volumes attached.
# Create snapshot of those volumes
# Create glance images of all volumes related to a VM
def prepare_migrate_vms_from_image_snapshot(id_file):
    ids = utils.read_ids_from_file(id_file)
    ready = check_vm_are_off("from", id_file)
    if ready:
        for vm_uuid in ids:
            volumes = get_volumes_for_vm("from", vm_uuid)
            for v in volumes:
                cinder_common.create_volume_snapshot("from", v, vm_uuid)
    else:
        print "Please make sure that all migration VMs are powered off."


# Find VMs with cinder volumes attached.
# Copy NFS Volumes on the backend
def prepare_migrate_vms_make_volume_copies(id_file):
    ids = utils.read_ids_from_file(id_file)
    ready = check_vm_are_off("from", id_file)
    if ready:
        for vm_uuid in ids:
            volumes = get_volumes_for_vm("from", vm_uuid)
            for v in volumes:
                if v.volume_type == 'SolidFire':
                    cinder_common.copy_solidfire_volume(v.id)
                else:
                    cinder_common.copy_nfs_volume(v.id)
    else:
        print "Please make sure that all migration VMs are powered off."


def make_volumes_from_snapshots(destination, id_file):
    vms = utils.read_ids_from_file(id_file)
    for vm in vms:
        volumes = get_volumes_for_vm("from", vm)
        for vol in volumes:
            snap = cinder_common.get_snapshot_by_volume_id(destination, vol.id)
            new_volume = cinder_common.make_volume_from_snapshot(destination, vol.id, snap)


def make_images_of_volumes_based_on_vms(destination, id_file):
    vms = utils.read_ids_from_file(id_file)
    for vm in vms:
        volumes = cinder_common.get_volume_list_by_vm_id(destination, vm)
        for vol in volumes:
            name = vol.metadata['original_volume_id']
            print "original volume name "  + name + ", snapshot volume id: " + vol.id
            cinder_common.upload_volume_to_image_by_volume_name(destination, vol, name)


def download_images_of_volumes_based_on_vms(destination, path, id_file):
    volumes = get_volume_id_list_for_vm_ids("from", id_file)
    glance_common.download_images_by_volume_uuid(destination, path, volumes)


def create_volumes_from_images_based_on_vms(id_file):
    volumes = get_volume_id_list_for_vm_ids("from", id_file)
    cinder_common.create_volumes_from_images_by_vm_id(volumes)


def manage_volumes_based_on_vms(id_file, ssd_host=None, hdd_host=None):
    vms = utils.read_ids_from_file(id_file)
    for vm in vms:
        volumes = cinder_common.get_volume_list_by_vm_id('from', vm)
        for volume in volumes:
            cinder_common.manage_volume_from_id('to', ssd_host, hdd_host, volume)


def manage_volume_copies_based_on_vms(id_file):
    vms = utils.read_ids_from_file(id_file)
    nova = get_nova('from')
    for vm_uuid in vms:
        vm = nova.servers.get(vm_uuid)
        if len(vm.__dict__['os-extended-volumes:volumes_attached']) > 0:
            print "Verifying Volumes for VM ID: " + vm.id
            from_vols = vm.__dict__['os-extended-volumes:volumes_attached']
            from_volumes = cinder_common.get_volumes_from_vm_attachment_list("from", from_vols)
            for volume in from_volumes:
                cinder_common.manage_copy_volume_from_id('to', volume)
        else:
            print "No attached volumes for VM " + vm_uuid


def retype_volumes_based_on_vms(id_file, type):
    vms = utils.read_ids_from_file(id_file)
    for vm in vms:
        volumes = cinder_common.get_volume_list_by_vm_id('to', vm)
        for volume in volumes:
            cinder_common.change_volume_type("to", volume, type)


def print_interfaces_for_vms(destination, id_file):
    if destination == 'from':
        servers = get_from_vm_list_by_ids(id_file)
    else:
        servers = get_to_vm_list_by_original_ids(id_file)
    nova = get_nova(destination)
    # print 'VM Name VM ID Port ID Port State Mac Fixed IP'
    print '{:16}'.format("VM Name"), '{:38}'.format("VM ID"), '{:38}'.format("Port ID"), '{:10}'.format("Port State"), \
        '{:18}'.format("Mac"), '{:16}'.format("Fixed IP")

    for server in servers:
        interfaces = nova.servers.interface_list(server)
        for interface in interfaces:
            print '{:16}'.format(server.name), '{:38}'.format(server.id), '{:38}'.format(interface.port_id), \
                '{:10}'.format(interface.port_state), '{:18}'.format(interface.mac_addr),
            for ip in interface.fixed_ips:
                print '{:16}'.format(ip['ip_address'])


def print_hypervisors(destination):
    nova = get_nova(destination)
    hyps = nova.hypervisors.list()
    for hyp in hyps:
        print hyp.hypervisor_hostname


def check_hypervisor_list(hyp_file):
    hyps_pairs = utils.read_ids_with_hyps_file(hyp_file)
    nova = get_nova('to')
    hyps = nova.hypervisors.list()
    new_hyp_set = set(map(lambda d: d['hyp'], hyps_pairs))
    system_hyp_set = set(map(lambda d: d.hypervisor_hostname, hyps))
    allgood = True
    for new_hyp in new_hyp_set:
        if new_hyp not in system_hyp_set:
            print "Hypervisor: " + new_hyp + " is NOT in available hypervisor list"
            allgood = False
    return allgood


# search to see if server was part of a server group on the "from" side.
# if server was part of a server group, return server group's name.
def find_server_group_by_old_uuid(old_uuid):
    # hint format:
    # {"group": "14f9838a-5b32-400f-92bf-7a494af708c8"}
    # must send id, doesn't take names.
    from_nova = get_nova("from")
    from_groups = from_nova.server_groups.list()
    for from_group in from_groups:
        for member in from_group.members:
            if member == old_uuid:
                print "Server ", old_uuid, "was part of", from_group.name, "server group."
                to_nova = get_nova("to")
                to_groups = to_nova.server_groups.list()
                for to_group in to_groups:
                    if to_group.name == from_group.name:
                        # return group
                        return {"group": to_group.id}
    return None


def print_server_groups(destination):
    nova = get_nova(destination)
    groups = nova.server_groups.list()
    for group in groups:
        print group.name, group.policies[0], group.members


# This will be need to be done per project, server_group_list doesn't return tenant info as part of ServerGroup object
# Will not create server groups with duplicate names
def copy_server_groups():
    from_nova = get_nova('from')
    to_nova = get_nova('to')
    from_groups = from_nova.server_groups.list()
    to_groups = to_nova.server_groups.list()
    new_to_group_name_set = set(map(lambda d: d.name, to_groups))

    for from_group in from_groups:
        if from_group.name not in new_to_group_name_set:
            new_group = to_nova.server_groups.create(name=from_group.name, policies=from_group.policies)
            print "Created new server group", new_group.name, new_group.policies[0]


def main():
    # get_security_groups('to')
    #create_security_group('to', 'foo')
    # compare_and_create_security_groups()
    # print get_vm_list('from')
    # print get_flavor_list('to')
    # compare_and_create_flavors()
    # get_quotas('from')
    #compare_and_update_quotas()
    #create_vm()
    #compare_and_create_vms()
    # compare_and_report_quotas()
    #get_keypairs('from')
    #compare_and_create_keypairs()
    #print_vm_list_ids('from')
    #read_ids_from_file("./id_file")
    #power_off_vms('from', "./id_file")
    # create_image_from_vm('from', "./id_file")
    # migrate_vms_from_image("./id_file")
    # print_security_groups('from')
    # get_flavor_by_id('from', 'a97d80f0-e309-436e-95cc-bb2a02139225')
    # vms = get_vm_list('from')
    # print vms
    # print_keys("to")
    # prepare_migrate_vms_from_image_snapshot("./id_file")
    # make_images_of_volumes_based_on_vms("from", "./id_file")
    # boot_from_volume_vms_from_image_with_network_mapping( './id_file', 'demo-net')
    # make_images_of_volumes_based_on_vms("from", './id_file')
    # make_volumes_from_snapshots("from", './id_file')
    # manage_volumes_based_on_vms('./id_file', 'egle-pike-dns-1@lvm#LVM_iSCSI')
    # power_on_vms('from', './id_file')
    # update_default_group_rules()
    # compare_and_create_security_groups()
    # print get_vms_without_volumes('from')
    # print get_vms_without_boot_volumes('from')
    # attach_volumes('./id_file')
    # update_all_group_rules()
    # boot_from_volume_vms_with_network_mapping('./id_file', 'demo-net')
    # get_interfaces_for_vm_ids('from', './id_file')
    # print_interfaces_for_vms('from', './id_file')
    # utils.get_macs_from_libvirt("path")
    # create_migration_security_group('from')
    # print_vm_list_with_multiple_volumes('to')
    # print_hypervisors("to")
    # check_hypervisor_list('pairs')
    # print_server_groups('from')
    copy_server_groups()

if __name__ == "__main__":
        main()
