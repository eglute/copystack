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

    if opts.fromusers:
        print "\n--------------- From Users: ------------------------"
        keystone_common.print_user_names('from')
    if opts.tousers:
        print "\n--------------- To Users: ------------------------"
        keystone_common.print_user_names('to')
    if opts.fromprojects:
        keystone_common.print_projects('from')
    if opts.toprojects:
        keystone_common.print_projects('to')

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-f", "--fromusers", action='store_true', dest='fromusers', help='Print FROM users')
    parser.add_option("-t", "--tousers", action='store_true', dest='tousers', help='Print TO users')
    parser.add_option("-p", "--fromprojects", action='store_true', dest='fromprojects', help='Print FROM projects (or tenants)')
    parser.add_option("-r", "--toprojects", action='store_true', dest='toprojects', help='Print TO projects (or tenants)')



    (opts, args) = parser.parse_args()
    main(opts, args)
