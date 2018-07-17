#!/usr/bin/env python

import json
import argparse
import optparse
import keystone_common
import neutron_common
import nova_common
import glance_common
import cinder_common
from auth_stack2 import AuthStack


def main(opts, args):
    auth = AuthStack()
    print "From:", auth.from_auth_ip, " Username:", auth.from_username, " Project:", auth.from_tenant_name
    print "To:  ", auth.to_auth_ip, " Username:", auth.to_username, " Project:", auth.to_tenant_name

    if opts.nets:
        print "\n--------------- From Networks (with subnets): ---------------------"
        neutron_common.print_network_list('from')
    if opts.Nets:
        print "\n--------------- To Networks (with subnets): ------------------------"
        neutron_common.print_network_list('to')
    if opts.routers:
        print "\n--------------- From Routers: ---------------------"
        neutron_common.print_routers('from')
    if opts.Routers:
        print "\n--------------- To Routers: ---------------------"
        neutron_common.print_routers('to')

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-n", "--nets", action='store_true', dest='nets', help='Print FROM networks')
    parser.add_option("-N", "--Nets", action='store_true', dest='Nets', help='Print TO networks')
    parser.add_option("-r", "--routers", action='store_true', dest='routers', help='Print FROM routers')
    parser.add_option("-R", "--Routers", action='store_true', dest='Routers', help='Print TO routers')

    (opts, args) = parser.parse_args()
    main(opts, args)
