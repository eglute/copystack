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

    if opts.report:
        print "\n--------------- From Volumes: ------------------------"
        volumes = cinder_common.print_detail_volumes('from')
        print "\n--------------- To Volumes: ------------------------"
        volumes = cinder_common.print_detail_volumes('to')
    if opts.types:
        print "\n--------------- From Volume Types: ------------------------"
        cinder_common.print_volume_types('from')
        print "\n--------------- To Volume Types: ------------------------"
        cinder_common.print_volume_types('to')
    if opts.backups:
        print "\n--------------- From Volume Backups: ------------------------"
        cinder_common.print_volume_backups('from')
        print "\n--------------- To Volume Backups: ------------------------"
        cinder_common.print_volume_backups('to')
    if opts.pools:
        print "\n--------------- From Volume Pools: ------------------------"
        cinder_common.print_cinder_pools('from')
        print "\n--------------- To Volume Pools: ------------------------"
        cinder_common.print_cinder_pools('to')


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-r", "--report", action='store_true', dest='report', help='Print volumes with details')
    parser.add_option("-t", "--types", action='store_true', dest='types', help='Print available volume types')
    parser.add_option("-b", "--backups", action='store_true', dest='backups', help='Print volume backups')
    parser.add_option("-p", "--pools", action='store_true', dest='pools', help='Print volume pools')


    (opts, args) = parser.parse_args()
    main(opts, args)
