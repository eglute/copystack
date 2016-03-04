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
from maas_common import (get_auth_ref, get_nova_client, status_err, status_ok,
                         DESTINATION_TO_IP, DESTINATION_FROM_IP)


def check(args):
    auth_ref = get_auth_ref()
    auth_token = auth_ref['token']['id']
    tenant_id = auth_ref['token']['tenant']['id']

    COMPUTE_ENDPOINT = 'http://{hostname}:8774/v2/{tenant_id}' \
                       .format(hostname=args.hostname, tenant_id=tenant_id)
    try:
        nova = get_nova_client(auth_token=auth_token,
                               bypass_url=COMPUTE_ENDPOINT)
        groups = nova.security_groups.list()

        print groups
    # not gathering api status metric here so catch any exception
    except Exception as e:
        status_err(str(e))


def get_nova(destination):
        #TODO: fix this part...
    if destination == 'to':
        IDENTITY_IP = DESTINATION_TO_IP
    else:
        IDENTITY_IP = DESTINATION_FROM_IP
    auth_ref = get_auth_ref(destination)
    auth_token = auth_ref['token']['id']
    tenant_id = auth_ref['token']['tenant']['id']

    COMPUTE_ENDPOINT = 'http://{ip}:8774/v2/{tenant_id}' \
                    .format(ip=IDENTITY_IP, tenant_id=tenant_id)

    try:
       nova = get_nova_client(destination, auth_token=auth_token,bypass_url=COMPUTE_ENDPOINT)

    except Exception as e:
        #status_err(str(e))
        print "boo exception"
        print e
    return nova


def get_security_groups(destination):
    nova = get_nova(destination)
    groups = nova.security_groups.list()
   # print groups

    return groups


def compare_and_create_security_groups():
    from_groups = get_security_groups('from')
    to_groups = get_security_groups('to')
    #print from_groups
    #print to_groups

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
    return to_group


#todo: fix this
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
    servers = nova.servers.list()
    for s in servers:
        server = nova.servers.get(s.id)
        #print server
        #print s
        #print s.networks
        #print s.addresses
        #for key in s.addresses:
        #   print key
    return servers


def compare_and_create_vms():
    from_vms = get_vm_list('from')
    to_vms = get_vm_list('to')
    from_names = map(lambda from_vms: from_vms.name, from_vms)
    to_names = map(lambda to_vms: to_vms.name, to_vms)
    for name in from_names:
        if name not in to_names:
            from_vm_list = filter(lambda from_vms: from_vms.name == name, from_vms)
            for from_vm in from_vm_list:
                #print from_vm

                create_vm(from_vm)
            #new_flavor = create_flavor('to', from_flavor[0])
            #new_flavor.set_keys(from_flavor[0].get_keys())
            #print "New flavor created: "
            #print new_flavor

# todo: add try catch for when multiple security groups are present.
# client lets add groups by name only...
def create_vm(from_vm):
    nova = get_nova('to')

    flavor = get_flavor_by_id('to', from_vm.flavor['id'])
    image = glance_common.get_image_by_original_id('to', from_vm.image['id'])
    networks = from_vm.networks

    nics = []
    for network, ips in networks.iteritems():
        net = neutron_common.get_network_by_name('to', network)
        #print ip[0]
        for ip in ips:
            nic = {'net-id': net['id'], 'v4-fixed-ip': ip}
            nics.append(nic)

    groups = from_vm.security_groups
    #out of luck for duplicate group names...
    group_names_map = map(lambda groups: groups['name'], groups)
    group_names = set(group_names_map)
    print group_names

    server = nova.servers.create(name=from_vm.name, image=image, flavor=flavor.id, nics=nics,
                                 meta=from_vm.metadata, security_groups=group_names)
    print server
    return server


def get_flavor_by_id(destination, flavor_id):
    nova = get_nova(destination)
    fl = nova.flavors.get(flavor=flavor_id)
    return fl


# nova flavor-list --all for checking all flavors for admin, private and public
def get_flavor_list(destination):
    nova = get_nova(destination)

    # There is no api flag for "--all", so need to make separate calls...
    flavors_public = nova.flavors.list(detailed=True, is_public=False)
    flavors_private = nova.flavors.list(detailed=True, is_public=True)
    flavors = flavors_private + flavors_public
    print flavors
    return flavors


def compare_and_create_flavors():
    from_flavors = get_flavor_list('from')
    to_flavors = get_flavor_list('to')
    from_names = map(lambda from_flavors: from_flavors.name, from_flavors)
    to_names = map(lambda to_flavors: to_flavors.name, to_flavors)
    for name in from_names:
        if name not in to_names:
            from_flavor = filter(lambda from_flavors: from_flavors.name == name, from_flavors)
            print from_flavor
            new_flavor = create_flavor('to', from_flavor[0])
            new_flavor.set_keys(from_flavor[0].get_keys())
            print "New flavor created: "
            print new_flavor


def create_flavor(destination, flavor):
    nova = get_nova(destination)
    new_flavor = nova.flavors.create(name=flavor.name,
                                     ram=flavor.ram,
                                     vcpus=flavor.vcpus,
                                     disk=flavor.disk,
                                     flavorid=flavor.id,
                                     ephemeral=flavor.ephemeral,
                                     swap=flavor.swap,
                                     rxtx_factor=flavor.rxtx_factor,
                                     is_public=flavor.is_public)
    return new_flavor


def get_quotas(destination, tenant):
    nova = get_nova(destination)
    quotas = nova.quotas.defaults(tenant)
    #print quotas
    return quotas


def compare_and_report_quotas():
    from_tenants = keystone_common.get_from_tenant_list()
    print "Differences in individual quotas for each tenant:"
    for from_tenant in from_tenants:

        from_quotas = get_quotas('from', from_tenant.id)
        to_tenant = keystone_common.find_opposite_tenant_id(from_tenant.id)
        to_quotas = get_quotas('to', to_tenant['to_id'])
        print "\nFrom tenant id:", from_tenant.id, "To tenant id:", to_tenant['to_id']
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
    from_tenants = keystone_common.get_from_tenant_list()
    for from_tenant in from_tenants:
        print "from tenant id "
        print from_tenant.id
        from_quotas = get_quotas('from', from_tenant.id)
        to_tenant = keystone_common.find_opposite_tenant_id(from_tenant.id)
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


def main():
    # get_security_groups('to')
    #create_security_group('to', 'foo')
    #compare_and_create_security_groups()
    #get_vm_list('from')
    #get_flavor_list('from')
    #compare_and_create_flavors()
    #get_quotas('from')
    #compare_and_update_quotas()
    #create_vm()
    compare_and_create_vms()
    #compare_and_report_quotas()

if __name__ == "__main__":
        main()
