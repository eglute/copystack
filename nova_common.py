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
                                                from_port = rule['from_port'], to_port=rule['to_port'], cidr=cidras,
                                                 group_id = to_group.id)
        print rule



def main():
    # get_security_groups('to')
    #create_security_group('to', 'foo')
    compare_and_create_security_groups()

if __name__ == "__main__":
        main()
