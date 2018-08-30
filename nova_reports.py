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

    if opts.scf:
        print "\n--------------- From Security Groups: ------------------------"
        nova_common.print_security_groups('from')
    if opts.Scf:
        print "\n--------------- To Security Groups: ------------------------"
        nova_common.print_security_groups('to')
    if opts.ff:
        print "\n--------------- From Flavors: ------------------------"
        nova_common.print_flavor_list('from')
    if opts.Ff:
        print "\n--------------- To Flavors: ------------------------"
        nova_common.print_flavor_list('to')
    if opts.vf:
        print "\n--------------- From VMs: ------------------------"
        vms = nova_common.print_vm_list_ids('from')
    if opts.vF:
        print "\n--------------- To VMs: ------------------------"
        vms = nova_common.print_vm_list_ids('to')


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-s", "--scf", action='store_true', dest='scf', help='Print FROM security groups')
    parser.add_option("-S", "--Scf", action='store_true', dest='Scf', help='Print TO security groups')
    parser.add_option("-f", "--ff", action='store_true', dest='ff', help='Print FROM flavors')
    parser.add_option("-F", "--Ff", action='store_true', dest='Ff', help='Print TO flavors')
    parser.add_option("-v", "--vf", action='store_true', dest='vf', help='Print FROM vms')
    parser.add_option("-V", "--vF", action='store_true', dest='vF', help='Print TO vms')




    (opts, args) = parser.parse_args()
    main(opts, args)
