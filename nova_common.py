#!/usr/bin/env python

# Copyright 2014, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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


def create_security_rules(destination, from_group, to_group, new_groups):
    nova = get_nova(destination)

    if from_group.rules:
        for rule in from_group.rules:
            if 'ip_range' in rule:
                if 'cidr' in rule['ip_range']:
                    cidras = rule['ip_range']['cidr']
                    rule = nova.security_group_rules.create(to_group.id, ip_protocol = rule['ip_protocol'],
                                                    from_port = rule['from_port'], to_port=rule['to_port'], cidr=cidras)#,
                                                    # group_id = to_group.id)
                else:
                    group_id = find_new_group_id_by_group_name(new_groups, rule['group']['name'])
                    rule = nova.security_group_rules.create(to_group.id, ip_protocol=rule['ip_protocol'],
                                                            from_port=rule['from_port'], to_port=rule['to_port'],
                                                            group_id=group_id)
                    print rule


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
    for s in servers:
        server = nova.servers.get(s.id)
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
def create_vm(from_vm, image='default'):
    nova = get_nova('to')

    flavor = get_flavor_by_id('to', from_vm.flavor['id'])
    if flavor is None:
        print "Error: Cannot continue for this VM without proper flavor"
        return None
    if image == 'default':
        image = glance_common.get_image_by_original_id('to', from_vm.image['id'])
    networks = from_vm.networks

    nics = []
    for network, nets in networks.iteritems():
        for ip in nets:
            port = neutron_common.find_port_by_ip('to', ip)
            # nic = {'net-id': net['id'], 'v4-fixed-ip': ip}
            if port:
                if not port['device_owner'].startswith('network:floatingip'):
                    nic = {'port-id': port['id']}
                    nics.append(nic)

    #include original image info as metadata:
    img = glance_common.get_image('from', from_vm.image['id'])
    metadata = from_vm.metadata
    metadata.update({'original_vm_id':from_vm.id})
    metadata.update({'original_image_id': img.id})
    metadata.update({'original_image_name': img.name})
    #attaching security groups during server creation does not seem to work, so moved to a separate task
    server = nova.servers.create(name=from_vm.name, image=image, flavor=flavor.id, nics=nics,
                                 meta=metadata, key_name=from_vm.key_name)

    print "Server created:", from_vm.name


def create_vm_with_network_mapping(from_vm, image='default', network_name='none'):
    nova = get_nova('to')

    flavor = get_flavor_by_id('to', from_vm.flavor['id'])
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

def attach_security_groups(id_file):
    ready = check_vm_are_on('to', id_file)
    if ready:
        ids = utils.read_ids_from_file(id_file)
        nova = get_nova('from')
        for uuid in ids:
            try:
                old_server = nova.servers.get(uuid)
                new_server = get_vm_by_original_id('to', uuid)
                groups = old_server.security_groups
                print "Attaching security groups to:", new_server.name
                for g in groups:
                    print "Group:", g['name']
                    new_server.add_security_group(g['name'])
            except Exception, e:
                print str(e)
    else:
        print "All VMs must be powered on for this action to proceed"


def migrate_vms_from_image(id_file):
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
                        if dup.metadata['original_vm_id'] == server.id:
                            print "Duplicate VM on TO side already found, skipping VM:", server.name, server.id
                            duplicate = True
                    if duplicate is False:
                        create_vm(server, image=image)
                else:
                    print "Did not find image in 'to' environment with name:", new_name
            else:
                print "1 Server with UUID:", uuid, " is not shutoff. It must be in SHUTOFF status for this action."
        except nova_exc.NotFound:
            print "2 Server with UUID", uuid, "not found"


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
                print "3 Server with UUID:", uuid, "is not running. It must be in ACTIVE status for this action."
        except nova_exc.NotFound:
            print "4 Server with UUID", uuid, "not found"


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
        except nova_exc.NotFound:
            print "5 Server with UUID", uuid, "not found"
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
                    print vol['id']
                    volume_ids.append(vol['id'])
        except nova_exc.NotFound:
            print "9 Server with UUID", uuid, "not found"
    return volume_ids


def print_keys(destination):
    keys = get_keypairs(destination)
    for key in keys:
        print key.name


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

#    vms = get_vm_list('from')
#    print vms
    print_keys("from")
if __name__ == "__main__":
        main()
