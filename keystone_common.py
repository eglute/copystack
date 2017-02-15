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
import keystoneclient.v2_0.users

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


def print_tenants(destination):
    if destination == 'to':
        tenants = get_to_tenant_list()
    else:
        tenants = get_from_tenant_list()
    tenants.sort(key=lambda x: x.name)
    newlist = sorted(tenants, key=lambda x: x.name)
    print "Tenant ID:                         Name:                  Description:"
    for tenant in newlist:
        print tenant.id, " ", '{:20}'.format(tenant.name), " ", tenant.description, " "


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
    keystone = get_keystone(destination)
    new_tenant = keystone.tenants.create(tenant_name=tenant.name, description=tenant.description, enabled=tenant.enabled)
    print "Created tenant", new_tenant.name
    return new_tenant


def get_users(destination):
    keystone = get_keystone(destination)
    users = keystone.users.list()
    #print users
    return users


def compare_and_create_users():
    from_users = get_users('from')
    to_users = get_users('to')

    from_names = map(lambda from_users: from_users.name, from_users)
    to_names = map(lambda to_users: to_users.name, to_users)

    for name in from_names:
        if name not in to_names:
            from_user = filter(lambda from_users: from_users.name == name, from_users)
            new_user = create_user('to', from_user[0])


# at this point don't have the tenant info for the user, so not attaching tenant info.
# #todo: lookup tenant and add on creation
def create_user(destination, user):
    keystone = get_keystone(destination)
    tenant = find_opposite_tenant_id(user.tenantId)
    if hasattr(user, 'email'):
        new_user = keystone.users.create(user.name, tenant_id=tenant['to_id'], email=user.email, enabled=user.enabled)
    else:
        new_user = keystone.users.create(user.name, tenant_id=tenant['to_id'], enabled=user.enabled)

    print "Created new user:", new_user.name, ". This user has no password. Set password manually."
    update_roles(user, new_user, tenant)

    return new_user


# let's assume the users are as they should be or compare_and_create_users() was already called here.
def get_from_to_name_user_ids():
    from_users = get_users('from')
    to_users = get_users('to')

    users_ids = list()
    for to_user in to_users:
        from_user = filter(lambda from_tenants: from_tenants.name == to_user.name, from_users)
        user = {'from_id': from_user[0].id, 'to_id': to_user.id, 'name': from_user[0].name}
        users_ids.append(user)

    return users_ids


# finds opposite user ID based on matching user names.
# returns the following format:
# {'to_id': u'e99e58c687ec4a608f4323d22a29c08e', 'name': u'foobar1', 'from_id': u'eaeb181cbdaa429483960f3c7a5c95fe'}
def find_opposite_user_id(user_id):
    from_users = get_users('from')
    to_users = get_users('to')

    from_user = filter(lambda from_users: from_users.id == user_id, from_users)
    if from_user:
        to_user = filter(lambda to_users: to_users.name == from_user[0].name, to_users)
        return {'from_id': from_user[0].id, 'name': from_user[0].name, 'to_id': to_user[0].id}

    to_user = filter(lambda to_tenants: to_tenants.id == user_id, to_users)
    if to_user:
        from_user = filter(lambda from_users: from_users.name == to_user[0].name, from_users)
        return {'from_id': from_user[0].id, 'name': to_user[0].name, 'to_id': to_user[0].id}

    # if didn't find anything, return a lot of nones.
    return {'from_id': 'None', 'name': 'None', 'to_id': 'None'}


def list_roles(destination, user_id, tenant_id):
    keystone = get_keystone(destination)

    roles = keystone.users.list_roles(user_id, tenant=tenant_id)
    return roles


def update_roles(old_user, new_user, tenant):
    keystone = get_keystone('to')
    to_tenants = keystone.tenants.list()
    to_tenant = filter(lambda to_tenants: to_tenants.id == tenant['to_id'], to_tenants)
    from_roles = list_roles('from', old_user.id, tenant['from_id'])
    to_roles = get_roles('to')

    for role in from_roles:
        rol = filter(lambda to_roles: to_roles.name == role.name, to_roles)
        try:
            keystone.roles.add_user_role(new_user, role=rol[0], tenant=to_tenant[0])
            print "Role added:", rol[0].name, " to user:", new_user.name
        except Exception, e:
            print "No new roles added for user:", new_user.name



def get_roles(destination):
    keystone = get_keystone(destination)
    roles = keystone.roles.list()
    return roles


def find_opposite_role(role_id):
    from_roles = get_roles('from')
    to_roles = get_roles('to')

    from_role = filter(lambda from_roles: from_roles.id == role_id, from_roles)
    if from_role:
        to_role = filter(lambda to_roles: to_roles.name == from_role[0].name, to_roles)
        return {'from_id': from_role[0].id, 'name': from_role[0].name, 'to_id': to_role[0].id}

    to_role = filter(lambda to_roles: to_roles.id == role_id, to_roles)
    if to_role:
        from_role = filter(lambda from_roles: from_roles.name == to_role[0].name, from_roles)
        return {'from_id': from_role[0].id, 'name': to_role[0].name, 'to_id': to_role[0].id}

    # if didn't find anything, return a lot of nones.
    return {'from_id': 'None', 'name': 'None', 'to_id': 'None'}

def main():
    #compare_and_create_tenants()
    #get_from_to_name_tenant_ids()
    #print find_opposite_tenant_id('e99e58c687ec4a608f4323d22a29c08e')
    # print get_from_tenant_list()
    #get_to_tenant_list()
    #get_keystone('to')
    #get_from_tenant_list()
    #get_to_tenant_list()
    #get_from_tenant_names()
    # print get_users('from')
    # get_users('to')
    # compare_and_create_users()
    # print get_from_to_name_user_ids()
    # print_tenants('from')
    # print list_roles("from", '08d53ca0a9304f28ad299a9a63dc4b68', 'a370cc1a5e4e409c80f41d50c3fa0ee5')
    print get_roles_for_tenant('from', 'a370cc1a5e4e409c80f41d50c3fa0ee5')
if __name__ == "__main__":
        main()
