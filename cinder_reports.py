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
    if opts.Report:
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
    if opts.Manage:
        if args:
            print "\n--------------- To Manageable Volumes: ------------------------"
            cinder_common.print_manageable_volumes('to', host=args[0])
        else:
            print "Please provide host name, similar to sample-aio-liberty-2@lvm#LVM_iSCSI"
    if opts.manage:
        if args:
            print "\n--------------- From Volume Pools: ------------------------"
            cinder_common.print_manageable_volumes('from', host=args[0])
        else:
            print "Please provide host name, similar to sample-aio-liberty-2@lvm#LVM_iSCSI"


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-r", "--report", action='store_true', dest='report', help='Print FROM volumes with details')
    parser.add_option("-R", "--Report", action='store_true', dest='Report', help='Print TO volumes with details')
    parser.add_option("-t", "--types", action='store_true', dest='types', help='Print available volume types')
    parser.add_option("-b", "--backups", action='store_true', dest='backups', help='Print volume backups')
    parser.add_option("-p", "--pools", action='store_true', dest='pools', help='Print volume pools')
    parser.add_option("-m", "--manage", action='store_true', dest='manage', help='Print FROM manageable volumes. '
                                        'Please provide host name, similar to sample-aio-liberty-2@lvm#LVM_iSCSI')
    parser.add_option("-M", "--Manage", action='store_true', dest='Manage', help='Print TO manageable volumes. '
                                        'Please provide host name, similar to sample-aio-liberty-2@lvm#LVM_iSCSI')

    (opts, args) = parser.parse_args()
    main(opts, args)
