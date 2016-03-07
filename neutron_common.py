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

import keystone_common
from auth_stack import AuthStack


def get_neutron(destination):
    auth = AuthStack()
    client = auth.get_neutron_client(destination)
    return client


def get_network_list(destination):
    neutron = get_neutron(destination)
    networks = neutron.list_networks()['networks']
    #print networks
    return networks


def get_network_by_name(destination, name):
    networks = get_network_list(destination)
    from_network = filter(lambda networks: networks['name'] == name, networks)
    return from_network[0]


def get_subnets(destination, network_id):
    neutron = get_neutron(destination)
    subnets = neutron.list_subnets(network_id=network_id)['subnets']
    if len(subnets) > 0:
        return subnets
    return None

# neutron security-group-list
def get_neutron_security_group_list(destination):
    neutron = get_neutron(destination)
    groups = neutron.list_security_groups()
    #print groups
    return groups


# takes a network object which and replicated to the indicated destination
def network_create_net(destination, network):
    neutron = get_neutron(destination)

    # need a "to" tenant id.
    tenant_info = keystone_common.find_opposite_tenant_id(network['tenant_id'])
    new_network = {'network': {'name': network['name'],
                            'tenant_id': tenant_info['to_id'],
                            'admin_state_up': network['admin_state_up'],
                            'provider:network_type': network['provider:network_type'],
                            #'provider:segmentation_id': network['provider:segmentation_id'], #todo: check on this
                            'router:external': network['router:external'],
                            'shared': network['shared']}}

    physical = network['provider:physical_network']
    if physical is not None:
        new_network['network'].update({'provider:physical_network': physical})

    new_net = neutron.create_network(body=new_network)
    return new_net



def compare_and_create_networks():
    from_networks = get_network_list('from')
    to_networks = get_network_list('to')
    from_names = map(lambda from_networks: from_networks['name'], from_networks)
    to_names = map(lambda to_networks: to_networks['name'], to_networks)
    for name in from_names:
        if name not in to_names:
            from_network = filter(lambda from_networks: from_networks['name'] == name, from_networks)
            # print from_network
            new_network = network_create_net('to', from_network[0])
            print "New network created: "
            print new_network
            create_subnets(from_network[0]['id'], new_network['network']['id'], new_network['network']['tenant_id'])


def create_subnets(from_network_id, to_network_id, to_tenant_id):
    from_subnets = get_subnets('from', from_network_id)
    if from_subnets is not None:
        neutron = get_neutron('to')
        for from_subnet in from_subnets:
            to_subnet = {'subnets': [{'cidr': from_subnet['cidr'],
                                       'name': from_subnet['name'],
                                        'enable_dhcp': from_subnet['enable_dhcp'],
                                        'tenant_id': to_tenant_id,
                                       # 'allocation_pools': from_subnet['allocation_pools'], #todo: check test this, should work
                                        'host_routes': from_subnet['host_routes'],
                                       'ip_version': from_subnet['ip_version'],
                                       'network_id': to_network_id,
                                       'dns_nameservers': from_subnet['dns_nameservers']}]}
                                       #'gateway_ip': from_subnet['gateway_ip']}]} #todo: test this with valid values, should work.

            subnet = neutron.create_subnet(body=to_subnet)
            print 'created subnet: '
            print subnet


def main():
    # check(args)
    #get_network_list('from')
    # get_neutron_security_group_list(args)
    # network_create_net(args)
    compare_and_create_networks()

    #print get_subnet('from', '8cb27f87-406f-4fcd-99c1-98da2238fd90')

if __name__ == "__main__":
        main()
