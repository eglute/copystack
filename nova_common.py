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
from maas_common import (get_auth_ref, get_nova_client, status_err, status_ok,
                         metric_bool, print_output)


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
        IDENTITY_IP = '172.16.56.129'
    else:
        IDENTITY_IP = '172.16.56.128'
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
    
    from_names = map(lambda from_groups: from_groups.name, from_groups)
    to_names = map(lambda to_groups: to_groups.name, to_groups)
    for name in from_names:
        if name not in to_names:
            from_group = filter(lambda from_groups: from_groups.name == name, from_groups)
            create_security_group('to', from_group[0])

def create_security_group(destination, sec_group):
    print sec_group.rules
    nova = get_nova(destination)
    sec = nova.security_groups.create(name=sec_group.name, description=sec_group.description)
    print sec
    create_security_rules(destination, sec_group, sec)
    print sec.rules
    return sec

#todo: fix this
def create_security_rules(destination, from_group, to_group):
    nova = get_nova(destination)

    for rule in from_group.rules:

        cidras = None

        if 'ip_range' in rule:
            if 'cidr' in rule['ip_range']:
                cidras = rule['ip_range']['cidr']
        else:
            cidras = "None"
        print "cidras"
        print cidras

        rule = nova.security_group_rules.create(to_group.id, ip_protocol = rule['ip_protocol'],
                                                from_port = rule['from_port'], to_port=rule['to_port'], cidr=cidras)#,
                                                # group_id = to_group.id)
        print rule


def get_vm_list(destination):
    nova = get_nova(destination)
    servers = nova.servers.list()
    for s in servers:
        print s
    return servers


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
    compare_and_update_quotas()



if __name__ == "__main__":
        main()
