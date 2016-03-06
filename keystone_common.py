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

from auth_stack import AuthStack

# Useful CLI commands:
# view tenant details:
# keystone tenant-get foobar1
# get tenant list:
# keystone tenant-list
# create tenant:
# keystone tenant-create --name foobar --description "foobar tenant"


def get_keystone(destination):

    auth = AuthStack()
    client = auth.get_keystone_client(destination)
    return client


def get_from_tenant_list():
    keystone = get_keystone('from')
    tenants = keystone.tenants.list()
    #print tenants
    return tenants


def get_from_tenant_names():
    tenants = get_from_tenant_list()
    names = map(lambda tenants: tenants.name, tenants)
    names = sorted(names)
    return names


def get_to_tenant_names():
    tenants = get_to_tenant_list()
    names = map(lambda tenants: tenants.name, tenants)
    names = sorted(names)
    return names


def get_to_tenant_list():
    keystone = get_keystone('to')
    tenants = keystone.tenants.list()
    #print tenants
    return tenants


# let's assume the tenants are as they should be or compare_and_create_tenants() was already called here.
def get_from_to_name_tenant_ids():
    from_tenants = get_from_tenant_list()
    to_tenants = get_to_tenant_list()

    tenant_ids = list()
    for to_tenant in to_tenants:
        from_tenant = filter(lambda from_tenants: from_tenants.name == to_tenant.name, from_tenants)
        tenant = {'from_id': from_tenant[0].id, 'to_id': to_tenant.id, 'name': from_tenant[0].name}
        tenant_ids.append(tenant)

    return tenant_ids


# finds opposite tenant ID based on matching tenant names.
# returns the following format:
# {'to_id': u'e99e58c687ec4a608f4323d22a29c08e', 'name': u'foobar1', 'from_id': u'eaeb181cbdaa429483960f3c7a5c95fe'}
def find_opposite_tenant_id(tenant_id):
    from_tenants = get_from_tenant_list()
    to_tenants = get_to_tenant_list()

    from_tenant = filter(lambda from_tenants: from_tenants.id == tenant_id, from_tenants)
    if from_tenant:
        to_tenant = filter(lambda to_tenants: to_tenants.name == from_tenant[0].name, to_tenants)
        return {'from_id': from_tenant[0].id, 'name': from_tenant[0].name, 'to_id': to_tenant[0].id}

    to_tenant = filter(lambda to_tenants: to_tenants.id == tenant_id, to_tenants)
    if to_tenant:
        from_tenant = filter(lambda from_tenants: from_tenants.name == to_tenant[0].name, from_tenants)
        return {'from_id': from_tenant[0].id, 'name': to_tenant[0].name, 'to_id': to_tenant[0].id}

    # if didn't find anything, return a lot of nones.
    return {'from_id': 'None', 'name': 'None', 'to_id': 'None'}


def compare_and_create_tenants():
    from_tenants = get_from_tenant_list()
    to_tenants = get_to_tenant_list()

    from_names = map(lambda from_tenants: from_tenants.name, from_tenants)
    to_names = map(lambda to_tenants: to_tenants.name, to_tenants)

    for name in from_names:
        if name not in to_names:
            from_tenant = filter(lambda from_tenants: from_tenants.name == name, from_tenants)
            new_tenant = create_tenant('to', from_tenant[0])


def create_tenant(destination, tenant):
    keystone = get_keystone('to')
    new_tenant = keystone.tenants.create(tenant_name=tenant.name, description=tenant.description, enabled=tenant.enabled)
    return new_tenant

def main():
    #compare_and_create_tenants()
    #get_from_to_name_tenant_ids()
    #print find_opposite_tenant_id('e99e58c687ec4a608f4323d22a29c08e')
    # print get_from_tenant_list()
    #get_to_tenant_list()
    #get_keystone('to')
    #get_from_tenant_list()
    #get_to_tenant_list()
    get_from_tenant_names()

if __name__ == "__main__":
        main()