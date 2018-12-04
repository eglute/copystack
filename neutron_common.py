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
from auth_stack2 import AuthStack


def get_neutron(destination):
    auth = AuthStack()
    client = auth.get_neutron_client(destination)
    return client


def get_network_list(destination):
    neutron = get_neutron(destination)
    networks = neutron.list_networks()['networks']
    #print networks
    return networks


def print_network_list(destination):
    networks = get_network_list(destination)
    networks.sort(key=lambda x: x['name'])
    newlist = sorted(networks, key=lambda x: x['name'])
    for net in newlist:
        print net['name']
        print net
        subnets = get_subnets(destination, net['id'])
        if subnets:
            for sub in subnets:
                print "    ", '{:20}'.format(sub['name']), " ", sub['cidr']


def get_network_by_name(destination, name):
    networks = get_network_list(destination)
    from_network = filter(lambda networks: networks['name'] == name, networks)
    return from_network[0]


def get_subnet_by_name(destination, network_id, name):
    subnets = get_subnets(destination, network_id)
    from_subnet = filter(lambda subnets: subnets['name'] == name, subnets)
    return from_subnet[0]


def get_network_by_id(destination, net_id):
    networks = get_network_list(destination)
    from_network = filter(lambda networks: networks['id'] == net_id, networks)
    return from_network[0]


def get_subnet_by_id(destination, net_id, subnet_id):
    subnets = get_subnets(destination, net_id)
    from_subnet = filter(lambda subnets: subnets['id'] == subnet_id, subnets)
    return from_subnet[0]


def get_subnets(destination, network_id):
    neutron = get_neutron(destination)
    subnets = neutron.list_subnets(network_id=network_id)['subnets']
    # print subnets
    if len(subnets) > 0:
        return subnets
    return None


def show_subnet(destination, subnet_id):
    neutron = get_neutron(destination)
    subnet = neutron.show_subnet(subnet_id)
    # print subnet
    return subnet


def get_ports(destination):
    neutron = get_neutron(destination)
    ports = neutron.list_ports()['ports']
    # print ports
    return ports


# takes a network object which and replicated to the indicated destination
def network_create_net(destination, network):
    neutron = get_neutron(destination)

    # need a "to" tenant id.
    tenant_info = keystone_common.find_opposite_project_id(network['tenant_id'])
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
                                        'allocation_pools': from_subnet['allocation_pools'], #todo: check test this, should work
                                        'host_routes': from_subnet['host_routes'],
                                       'ip_version': from_subnet['ip_version'],
                                       'network_id': to_network_id,
                                       'dns_nameservers': from_subnet['dns_nameservers'], #}]}
                                       'gateway_ip': from_subnet['gateway_ip']}]} #todo: test this with valid values, should work.

            subnet = neutron.create_subnet(body=to_subnet)
            print 'created subnet: '
            print subnet


def get_routers(destination):
    neutron = get_neutron(destination)
    routers = neutron.list_routers()['routers']
    # print routers
    return routers


def print_routers(destination):
    routers = get_routers(destination)

    routers.sort(key=lambda x: x['name'])
    newlist = sorted(routers, key=lambda x: x['name'])
    print "Name:                  Status:      Project ID"
    for router in newlist:
        print '{:20}'.format(router['name']), " ", '{:10}'.format(router['status']), " ", router['tenant_id']


def get_router(destination, router):
    neutron = get_neutron(destination)
    router = neutron.show_router(router)['router']
    # print router
    return router


def compare_and_create_routers():
    from_routers = get_routers('from')
    to_routers = get_routers('to')
    from_names = map(lambda from_routers: from_routers['name'], from_routers)
    to_names = map(lambda to_routers: to_routers['name'], to_routers)
    for name in from_names:
        if name not in to_names:
            from_router = filter(lambda from_routers: from_routers['name'] == name, from_routers)
            # print from_router
            create_router('to', from_router[0])
            # new_network = network_create_net('to', from_router[0])
            # print "New network created: "
            # print new_network
            # create_subnets(from_router[0]['id'], new_network['network']['id'], new_network['network']['tenant_id'])


def create_router(destination, router):
    neutron = get_neutron(destination)

#todo: fix ['external_gateway_info']['external_fixed_ips'][0] to have multiples, rather than single
    #though i dont think routers can have two external gateway IPs...
    matching_network = find_corresponding_network_name_by_id(router['external_gateway_info']['network_id'])
    matching_subnet = find_corresponding_subnet_name_by_id(router['external_gateway_info']['network_id'],
                                                           matching_network['id'],
                                                           router['external_gateway_info']['external_fixed_ips'][0]['subnet_id'])
    matching_tenant = keystone_common.find_opposite_project_id(router['tenant_id'])
    body = {'router': {
                'name': router['name'],
                'tenant_id': matching_tenant['to_id']
            }}
    new_router = neutron.create_router(body=body)
    print "New Router created:", new_router

    add_router_gateway(destination, new_router['router'], router, matching_network, matching_subnet)
    return new_router


# the all in one command for creating router and setting this info was not working, was creating port that was down.
# equivalent of 'neutron router-gateway-set egle-router public'
def add_router_gateway(destination, router, old_router, matching_network, matching_subnet):
    body = { 'network_id': matching_network['id'],
             'enable_snat': old_router['external_gateway_info']['enable_snat'],
                        'external_fixed_ips': [{
                            'subnet_id': matching_subnet['id'],
                            'ip_address': old_router['external_gateway_info']['external_fixed_ips'][0]['ip_address']
                        }]}
    neutron = get_neutron(destination)
    updated_router = neutron.add_gateway_router(router['id'], body)
    # print updated_router
    return updated_router


def find_corresponding_network_name_by_id(net_id):
    from_network = get_network_by_id('from', net_id)
    to_network = get_network_by_name('to', from_network['name'])
    # print to_network
    return to_network


def find_corresponding_subnet_name_by_id(from_net_id, to_net_id, subnet_id):
    from_subnet = get_subnet_by_id('from', from_net_id, subnet_id)
    to_subnet = get_subnet_by_name('to', to_net_id, from_subnet['name'])
    # print to_subnet
    return to_subnet


def find_corresponding_router_name_by_id(router_id):
    from_router = get_router('from', router_id)
    to_router = get_router_by_name('to', from_router['name'])
    # print to_router
    return to_router


def get_router_by_name(destination, name):
    routers = get_routers(destination)
    from_routers = filter(lambda routers: routers['name'] == name, routers)
    if from_routers:
        return from_routers[0]
    else:
        return None


def print_ports(destination):
    ports = get_ports(destination)
    for port in ports:
        print port['id'], port['mac_address'], port['fixed_ips'], port['allowed_address_pairs']


def print_common_ips():
    from_ports = get_ports('from')
    to_ports = get_ports('to')
    from_names = map(lambda from_ports: from_ports['fixed_ips'][0]['ip_address'], from_ports)
    to_names = map(lambda to_ports: to_ports['fixed_ips'][0]['ip_address'], to_ports)
    for name in from_names:
        if name in to_names:
            from_po = filter(lambda from_ports: from_ports['fixed_ips'][0]['ip_address'] == name, from_ports)
            for from_port in from_po:
                print '{:20}'.format(name), from_port['device_owner']


def print_diff_ips():
    from_ports = get_ports('from')
    to_ports = get_ports('to')
    from_names = map(lambda from_ports: from_ports['fixed_ips'][0]['ip_address'], from_ports)
    to_names = map(lambda to_ports: to_ports['fixed_ips'][0]['ip_address'], to_ports)
    for name in from_names:
        if name not in to_names:
            from_po = filter(lambda from_ports: from_ports['fixed_ips'][0]['ip_address'] == name, from_ports)
            for from_port in from_po:
                print '{:20}'.format(name), from_port['device_owner']


def print_diff_macs():
    from_ports = get_ports('from')
    to_ports = get_ports('to')
    from_names = map(lambda from_ports: from_ports['mac_address'], from_ports)
    to_names = map(lambda to_ports: to_ports['mac_address'], to_ports)
    for name in from_names:
        if name not in to_names:
            from_po = filter(lambda from_ports: from_ports['mac_address'] == name, from_ports)
            for from_port in from_po:
                print '{:20}'.format(from_port['mac_address']), '{:20}'.format(from_port['fixed_ips'][0]['ip_address']), from_port['device_owner']


def print_same_macs():
    from_ports = get_ports('from')
    to_ports = get_ports('to')
    from_names = map(lambda from_ports: from_ports['mac_address'], from_ports)
    to_names = map(lambda to_ports: to_ports['mac_address'], to_ports)
    for name in from_names:
        if name in to_names:
            from_po = filter(lambda from_ports: from_ports['mac_address'] == name, from_ports)
            for from_port in from_po:
                print '{:20}'.format(from_port['mac_address']), '{:20}'.format(from_port['fixed_ips'][0]['ip_address']), from_port['device_owner']


def compare_and_create_ports():
    from_ports = get_ports('from')
    to_ports = get_ports('to')
    #the magic of mixing ids and names. Ports that are newly created through copystack will have the old id as the name.
    # from_names = map(lambda from_ports: from_ports['id'], from_ports)
    from_names = map(lambda from_ports: from_ports['fixed_ips'][0]['ip_address'], from_ports)
    # to_names = map(lambda to_ports: to_ports['name'], to_ports)
    to_names = map(lambda to_ports: to_ports['fixed_ips'][0]['ip_address'], to_ports)
    for name in from_names:
        if name not in to_names:
            from_port = filter(lambda from_ports: from_ports['fixed_ips'][0]['ip_address'] == name, from_ports)
            # if (from_port[0]['device_owner'].startswith('network:router_gateway') or
            if from_port[0]['device_owner'].startswith('network:router_interface'):
            # cannot simply just add a new port for some reason, need to do this for ports to come up in active status
                try:
                    new_thing = add_interface_router('to', from_port[0])
                except Exception, e:
                    print "Somthing bad happened when trying to add a router interface. Check that routers match on source and destination"
                    print str(e)
            fixed_ip = filter(lambda to_ports: to_ports['fixed_ips'][0]['ip_address'] == from_port[0]['fixed_ips'][0]['ip_address'], to_ports)
            if fixed_ip:
                print "Port with fixed ip", fixed_ip[0]['fixed_ips'][0]['ip_address'], "already exists, skipping it."
            else:
                if (from_port[0]['device_owner'].startswith('compute:nova') or
                    from_port[0]['device_owner'].startswith('network:floatingip') or
                    from_port[0]['device_owner'].startswith('compute:None')):
                        create_ip_ports('to', from_port[0])


    associate_all_ips()


# attach internal network to a router, by creating new interface
# equivalent of 'neutron router-interface-add'
def add_interface_router(destination, port):
    neutron = get_neutron(destination)
    old_router = get_router('from', port['device_id'])
    old_network = get_network_by_id('from', port['network_id'])
    new_router = find_corresponding_router_name_by_id(old_router['id'])
    new_network = find_corresponding_network_name_by_id(old_network['id'])
    old_subnet_id = port['fixed_ips'][0]['subnet_id']
    # print old_subnet_id
    new_subnet = find_corresponding_subnet_name_by_id(old_network['id'], new_network['id'], old_subnet_id) #todo: change to list of things
    body = {'subnet_id': new_subnet['id'],
            'fixed_ips': [{
                'ip_address': port['fixed_ips'][0]['ip_address'] #todo: fix this
            }]}
    try:
        updated_router = neutron.add_interface_router(new_router['id'], body)
        print "Router updated with new interfaces:", updated_router
        return updated_router
    except Exception, e:
        if str(e).startswith("Bad router request: Router already has a port on subnet"):
            print "Router ", new_router['name'], "already has all interfaces"
        else:
            print "Exception occured while adding interface to router", str(e)


# create ports for floating ips as well as any other ports that get individual ips on subnets that are then attached to
# vm instances. Equivalent of 'neutron port-create egle-net --fixed-ip ip_address=11.11.11.3'
def create_ip_ports(destination, port):
    neutron = get_neutron(destination)
    try:
        corspd_network = find_corresponding_network_name_by_id(port['network_id'])
    except Exception, e:
        print "Couldn't find a matching network, please check that source and destination networks match."
        return
    if port['device_owner'].startswith('network:floatingip'):
        fip = find_float_by_floatip('from', port['fixed_ips'][0]['ip_address'])
        corspd_tenant = keystone_common.find_opposite_project_id(fip['tenant_id'])
    else:
        corspd_tenant = keystone_common.find_opposite_project_id(port['tenant_id'])

    # print "old port tenant", port['tenant_id']
    # print "corresponding tenant in port creation", corspd_tenant
    print port
    try:
        if port['device_owner'].startswith('network:floatingip'):
            print "---------"
            body = {
                    "floatingip": {
                        "floating_network_id": corspd_network['id'],
                        "floating_ip_address": port['fixed_ips'][0]['ip_address'],
                        "tenant_id": corspd_tenant['to_id'],
                        # "mac_address": port['mac_address']

                    }
            }
            new_port = neutron.create_floatingip(body=body)
            print "Floating IP port created:", new_port
        else:
            body = {'port': {
                'network_id': corspd_network['id'],
                "tenant_id": corspd_tenant['to_id'],
                "mac_address": port['mac_address'],
                'fixed_ips':[{
                    'ip_address': port['fixed_ips'][0]['ip_address']
                    }],
                "admin_state_up": 'true'
                }
            }
            new_port = neutron.create_port(body=body)
            print "Port created:", new_port
        return new_port
    except Exception, e:
        print "Exception occured while creating port", str(e)


def find_port_by_ip(destination, ip):
    ports = get_ports(destination)
    port_ip = filter(lambda ports: ports['fixed_ips'][0]['ip_address'] == ip, ports)
    if port_ip:
        return port_ip[0]
    else:
        return None


def find_float_by_floatip(destination, ip):
    ports = get_floatingip_list(destination)
    port_ip = filter(lambda ports: ports['floating_ip_address'] == ip, ports)
    if port_ip:
        return port_ip[0]
    else:
        return None


# neutron security-group-list
def get_neutron_security_group_list(destination):
    neutron = get_neutron(destination)
    groups = neutron.list_security_groups()['security_groups']
    # print groups
    return groups


def get_floatingip_list(destination):
    neutron = get_neutron(destination)
    floats = neutron.list_floatingips()['floatingips']
    return floats


def associate_all_ips():
    from_floats = get_floatingip_list('from')
    to_floats = get_floatingip_list('to')

    from_fips = map(lambda from_floats: from_floats['fixed_ip_address'], from_floats)
    to_fips = map(lambda to_floats: to_floats['fixed_ip_address'], to_floats)

    for fip in from_fips:
        if fip not in to_fips:
            from_fip = filter(lambda from_floats: from_floats['fixed_ip_address'] == fip, from_floats)
            to_fixed_port = find_port_by_ip('to', from_fip[0]['fixed_ip_address'])
            to_float_port = find_float_by_floatip('to', from_fip[0]['floating_ip_address'])
            if to_float_port:
                associate_floating_ip_to_fixed_port('to', to_float_port['id'], to_fixed_port['id'])
    # for from_float in from_floats:
    #     if from_float['fixed_ip_address']:
    #         to_fixed_port = find_port_by_ip('to', from_float['fixed_ip_address'])
    #         to_float_port = find_float_by_floatip('to', from_float['floating_ip_address'])
    #         associate_floating_ip_to_fixed_port('to', to_float_port['id'], to_fixed_port['id'])


def associate_floating_ip_to_fixed_port(destination, to_float_port_id, to_fixed_port_id):
    neutron = get_neutron(destination)
    body = {"floatingip":
                {"port_id": to_fixed_port_id} #fixed ip port ID.
            }
    #floating ip port, body
    neutron.update_floatingip(to_float_port_id, body=body)
    print "Updated floating to fixed IP association, port: ", to_float_port_id, " to ", to_fixed_port_id


def main():
    # check(args)
    # get_network_list('from')
    # network_create_net(args)
    # compare_and_create_networks()
    # print get_routers('from')
    # print_routers('from')
    # print get_routers('to')
    # compare_and_create_routers()
    #print get_subnet('from', '8cb27f87-406f-4fcd-99c1-98da2238fd90')
    # show_subnet('from', '5a4a876d-f22d-48c8-874a-a3385576b717')
    # get_subnets('from', '0dfd0dee-7253-40c3-8157-45d9b2ffe07c')
    # get_subnets('to', '5618c10d-f055-4244-b439-56df4e23334a')
    # get_router('from', '8cd5e812-9300-4c41-b913-db8e221d883c')
    # print get_ports('from')
    # create_port()
    # compare_and_create_ports()
    # find_port_by_ip('to', '11.11.11.3')
    # print get_neutron_security_group_list('from')
    # print get_neutron_security_group_list('to')
    # print get_floatingip_list('from')
    # associate_floating_ip_to_fixed_port('to')
    # print find_float_by_floatip('from', '172.29.248.10')
    # associate_all_ips()
    # print_network_list('to')
    # print_diff_macs()
    print_ports("from")

if __name__ == "__main__":
        main()
