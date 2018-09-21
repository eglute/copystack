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

from auth_stack2 import AuthStack
import keystoneclient.v2_0.users
from log import logging
from keystoneauth1 import exceptions as keystone_exceptions
import utils


logger = logging.getLogger('copystack.keystone_common')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


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


def get_from_project_list():
    auth = AuthStack()
    keystone = get_keystone('from')
    if auth.from_keystone_version == '2':
        projects = keystone.tenants.list()
    else:
        projects = keystone.projects.list(domain=auth.from_domain_id)
    #print projects
    return projects


def get_from_tenant_names():
    tenants = get_from_tenant_list()
    names = map(lambda tenants: tenants.name, tenants)
    names = sorted(names)
    return names


def get_from_project_names():
    projects = get_from_project_list()
    names = map(lambda projects: projects.name, projects)
    names = sorted(names)
    return names


def get_to_tenant_names():
    tenants = get_to_tenant_list()
    names = map(lambda tenants: tenants.name, tenants)
    names = sorted(names)
    return names

def get_to_project_names():
    projects = get_to_project_list()
    names = map(lambda projects: projects.name, projects)
    names = sorted(names)
    return names


def get_to_tenant_list():
    keystone = get_keystone('to')
    tenants = keystone.tenants.list()
    #print tenants
    return tenants


def get_to_project_list():
    auth = AuthStack()
    keystone = get_keystone('to')
    if auth.to_keystone_version == '2':
        projects = keystone.tenants.list()
    else:
        projects = keystone.projects.list(domain=auth.to_domain_id)
    #print tenants
    return projects


def print_projects(destination):
    auth = AuthStack()
    project = "Project"
    dest = "To"
    if destination == 'to':
        projects = get_to_project_list()
    else:
        projects = get_from_project_list()
        dest = "From"
        if auth.from_keystone_version == '2':
            project = "Tenant"
    projects.sort(key=lambda x: x.name)
    newlist = sorted(projects, key=lambda x: x.name)
    print "\n--------------- ",dest, project ," ------------------------"
    print project, "ID:                         Name:                  Description:"
    for project in newlist:
        print project.id, " ", '{:20}'.format(project.name), " ", project.description, " "


def print_tenants(destination):
    if destination == 'to':
        tenants = get_to_tenant_list()
    else:
        tenants = get_from_tenant_list()
    tenants.sort(key=lambda x: x.name)
    newlist = sorted(tenants, key=lambda x: x.name)
    print "Project ID:                         Name:                  Description:"
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


def get_from_to_name_project_ids():
    from_projects = get_from_project_list()
    to_projects = get_to_project_list()

    project_ids = list()
    for to_project in to_projects:
        from_project = filter(lambda from_projects: from_projects.name == to_project.name, from_projects)
        tenant = {'from_id': from_project[0].id, 'to_id': to_project.id, 'name': from_project[0].name}
        project_ids.append(tenant)

    return project_ids

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


def find_opposite_project_id(project_id):
    from_projects = get_from_project_list()
    to_projects = get_to_project_list()

    from_project = filter(lambda from_project: from_project.id == project_id, from_projects)
    if from_project:
        to_project = filter(lambda to_tenants: to_tenants.name == from_project[0].name, to_projects)
        if to_project:
            return {'from_id': from_project[0].id, 'name': from_project[0].name, 'to_id': to_project[0].id}

    to_project = filter(lambda to_tenants: to_tenants.id == project_id, to_projects)
    if to_project:
        from_project = filter(lambda from_tenants: from_tenants.name == to_project[0].name, from_projects)
        return {'from_id': from_project[0].id, 'name': to_project[0].name, 'to_id': to_project[0].id}

    # if didn't find anything, return a lot of nones.
    return {'from_id': 'None', 'name': 'None', 'to_id': 'None'}


def build_project_from_to_id_list():
    from_projects = get_from_project_list()
    to_projects = get_to_project_list()
    opposites = []
    for from_project in from_projects:
        to_project = filter(lambda to_tenants: to_tenants.name == from_project.name, to_projects)
        if to_project:
            oppo = {'from_id': from_project.id, 'name': from_project.name, 'to_id': to_project[0].id}
            opposites.append(oppo)

    return opposites


def compare_and_create_tenants():
    from_tenants = get_from_tenant_list()
    to_tenants = get_to_tenant_list()

    from_names = map(lambda from_tenants: from_tenants.name, from_tenants)
    to_names = map(lambda to_tenants: to_tenants.name, to_tenants)

    for name in from_names:
        if name not in to_names:
            from_tenant = filter(lambda from_tenants: from_tenants.name == name, from_tenants)
            new_tenant = create_tenant('to', from_tenant[0])


def compare_and_create_projects():
    print "Compare and create projects between two environments"
    from_tenants = get_from_project_list()
    to_tenants = get_to_project_list()

    from_names = map(lambda from_tenants: from_tenants.name, from_tenants)
    to_names = map(lambda to_tenants: to_tenants.name, to_tenants)

    for name in from_names:
        if name not in to_names:
            from_tenant = filter(lambda from_tenants: from_tenants.name == name, from_tenants)
            new_tenant = create_project('to', from_tenant[0])


def create_tenant(destination, tenant):
    keystone = get_keystone(destination)
    new_tenant = keystone.tenants.create(tenant_name=tenant.name, description=tenant.description, enabled=tenant.enabled)
    print "Created tenant", new_tenant.name
    return new_tenant


def create_project(destination, tenant):
    keystone = get_keystone(destination)
    auth = AuthStack()
    new_tenant = keystone.projects.create(tenant.name, auth.to_project_domain_id, description=tenant.description, enabled=tenant.enabled)
    print "Created project", new_tenant.name
    return new_tenant


def get_users(destination):
    keystone = get_keystone(destination)
    users = keystone.users.list()
    #print users
    return users


def get_users_based_on_domain(destination):
    auth = AuthStack()
    keystone = get_keystone(destination)
    version = '3'
    if auth.from_keystone_version == '2':
        version = '2'
    domain = 'default'
    if destination == 'from':
        domain = auth.from_domain_id
    else:
        domain = auth.to_domain_id
    if version == '2':
        users = keystone.users.list()
    else:
        users = keystone.users.list(domain=domain)
    #print users
    return users


def get_users_based_on_project(destination, name):
    keystone = get_keystone(destination)
    auth = AuthStack()
    version = '3'
    domain_id = 'default'
    if destination == 'from':
        domain_id = auth.from_domain_id
        if auth.from_keystone_version == '2':
            version = '2'
    if destination == 'to':
        domain_id = auth.to_domain_id
        if auth.to_keystone_version == '2':
            version = '2'
    if version == '2':
        projects = keystone.tenants.list()
    else:
        # projects = keystone.projects.list(domain=domain_id, name=name)
        projects = keystone.projects.list(name=name)
    # print projects
    users = []
    if version == '2':
        users = get_users(destination)
    else:
        for project in projects:
            # roles = keystone.role_assignments.list(project=project.id)
            roles = keystone.role_assignments.list(project=project.id)
            for role in roles:
                # print role.user['id']
                user = keystone.users.get(role.user['id'])
                if user not in users:
                    users.append(user)
    return users


def print_users_per_project(destination):
    if destination == "from":
        projects = get_from_project_list()
    else:
        projects = get_to_project_list()
    for project in projects:
        users = get_users_based_on_project('from', project.name)
        print "Users in Project: " + project.name
        for user in users:
            print "     " + user.name


def get_users_from_name_list(destination, user_name_file):
    names = utils.read_ids_from_file(user_name_file)
    users = []
    for name in names:
        user = get_user_by_name(destination, name)
        users.append(user)
    return users


# Build a matrix of users/projects/roles. Takes a long time to build but speeds up adding users to proper tenants.
def build_matrix(user_name_file=None):
    keystone = get_keystone("from")
    auth = AuthStack()
    matrix = list()
    projects = list()
    project_list = build_project_from_to_id_list()
    role_list = build_role_from_to_list()
    if auth.from_keystone_version == '2':
        if user_name_file:
            users = get_users_from_name_list('from', user_name_file)
        else:
            users = get_users('from')
        # print users
        for user in users:
            # print user
            get_user_roles('from', matrix, user, project_list, role_list)
        # matrix.append(mat)
    else:
        asl = keystone.role_assignments.list()
        project = ''
        print "Building user project role matrix between the two environments. This will take a bit."
        for a in asl:
            project = ''
            if hasattr(a, 'scope'):
                if a.scope.has_key('project'):
                    pro = a.scope['project']['id']
                    p = filter(lambda to_vms: to_vms['from_id'] == pro, projects)
                    if p:
                        project = p[0]
                    if not project:
                        project = find_opposite_project_id(a.scope['project']['id'])
                        if not project:
                            print "WARNING: Project not found" +  a.scope['project']['id']
                        else:
                            projects.append(project)
                    if project:
                        role = find_opposite_role(a.role['id'])
                        mat = {'from_role_id:': a.role['id'], 'role_name':role['name'], 'from_project_id': a.scope['project']['id'], 'from_user_id': a.user['id'],
                               'to_project_id': project['to_id'], 'to_role_id': role['to_id'], 'project_name': project['name']}
                        print mat
                        matrix.append(mat)
    return matrix


def find_in_list_by_id(list_of_things, id):
    for thing in list_of_things:
        if thing['from_id'] == id:
            return thing


def get_user_roles(destination, matrix, user, project_list, role_list):

    # user = get_user_by_name(destination, name)
    keystone = get_keystone(destination)
    tenants = get_from_tenant_list()

    for tenant in tenants:
        try:
            # print user, tenant.id
            roles = keystone.users.list_roles(user=user, tenant=tenant.id)
            # project = find_opposite_project_id(tenant.id)
            project = find_in_list_by_id(project_list, tenant.id)
            # return {'from_id': from_project[0].id, 'name': to_project[0].name, 'to_id': to_project[0].id}
            for rol in roles:
                # print user.name, tenant.name, rol.name
                # role = find_opposite_role(rol.id)
                role = find_in_list_by_id(role_list, rol.id)
                if role['to_id'] == 'None':
                    continue
                else:
                    #  role:  return {'from_id': 'None', 'name': 'None', 'to_id': 'None'}
                    mat = {'from_role_id:': role['from_id'], 'role_name': role['name'],
                           'from_project_id': tenant.id, 'from_user_id': user.id,
                           'to_project_id': project['to_id'], 'to_role_id': role['to_id'], 'project_name': tenant.name}
                    print mat
                    matrix.append(mat)
        except keystone_exceptions.http.NotFound as e:
            #print e
            #ok if not found, not every user is in every project
            continue

        # print roles
    return matrix


def print_users_per_domain(destination):
    users = get_users_based_on_domain(destination)
    for user in users:
        print user.name


def compare_and_create_users():
    from_users = get_users('from')
    to_users = get_users('to')
    from_matrix = build_matrix()

    from_names = map(lambda from_users: from_users.name, from_users)
    to_names = map(lambda to_users: to_users.name, to_users)

    for name in from_names:
        if name not in to_names:
            from_user = filter(lambda from_users: from_users.name == name, from_users)
            new_user = create_user('to', from_user[0], from_matrix)


def compare_and_create_users_by_project(password=None):
    auth = AuthStack()
    from_matrix = build_matrix()
    from_users = get_users_based_on_project('from', auth.from_tenant_name)
    to_users = get_users_based_on_project('to', auth.to_tenant_name)
    from_names = map(lambda from_users: from_users.name, from_users)
    to_names = map(lambda to_users: to_users.name, to_users)
    for name in from_names:
        if name not in to_names:
            from_user = filter(lambda from_users: from_users.name == name, from_users)
            new_user = create_user('to', from_user[0], password, from_matrix)


def compare_and_create_users_by_domain(password=None, user_name_file=None):
    auth = AuthStack()
    if user_name_file:
        from_users = get_users_from_name_list('from', user_name_file)
    else:
        from_users = get_users_based_on_domain('from')
    to_users = get_users_based_on_domain('to')
    from_names = map(lambda from_users: from_users.name, from_users)
    to_names = map(lambda to_users: to_users.name, to_users)
    from_matrix = build_matrix(user_name_file=user_name_file)
    for name in from_names:
        if name not in to_names:
            from_user = filter(lambda from_users: from_users.name == name, from_users)
            new_user = create_user('to', from_user[0], password, from_matrix)
        elif name in to_names:
            print "user already exists, update roles"
            from_user = filter(lambda from_users: from_users.name == name, from_users)
            to_user = filter(lambda to_users: to_users.name == name, to_users)
            update_roles(from_user[0], to_user[0], from_matrix)


# at this point don't have the tenant info for the user, so not attaching tenant info.
def create_user(destination, user, password, from_matrix):
    auth = AuthStack()
    keystone = get_keystone(destination)
    # u_id = None
    # if hasattr(user, 'default_project_id'):
    #     u_id = user.default_project_id
    # else:
    #     #todo: not all v3 have defaults, so need to check for v2/v3 and then might not have project associated
    #     if auth.from_keystone_version == '2':
    #         u_id = user.tenantId
    try:
        if hasattr(user, 'email'):
            new_user = keystone.users.create(name=user.name, password=password, email=user.email,
                                             enabled=user.enabled)
        else:
            new_user = keystone.users.create(name=user.name, password=password, enabled=user.enabled)
        if password:
            print "Created new user:", new_user.name, ". This user has default password set. Change password manually."
        else:
            print "Created new user:", new_user.name, ". This user has no password. Set password manually."

        update_roles(user, new_user, from_matrix)
        return new_user
    except keystone_exceptions.http.Conflict:
        print "WARNING: Duplicate user creation attempted, skipping user:", user.name


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
    auth = AuthStack()
    version = '3'
    if destination == "from":
        if auth.from_keystone_version == '2':
            version = '2'
    if destination == 'to':
        if auth.to_keystone_version == '2':
            version = '2'
    if version == '2':
        user = keystone.users.get(user_id)
        tenant = keystone.tenants.get(tenant_id)
        roles = keystone.roles.roles_for_user(user, tenant=tenant)
    else:
        roles = keystone.roles.list(user_id, project=tenant_id)
    return roles


def update_roles(old_user, new_user, from_matrix):
    try:
        keystone = get_keystone('to')
        for matrix in from_matrix:
            if matrix['from_user_id'] == old_user.id:
                keystone.roles.grant(project=matrix['to_project_id'], user=new_user.id, role=matrix['to_role_id'])
                print "Role added: ", matrix['role_name'], " to user:", new_user.name, " in project: ", matrix['project_name']
    except Exception, e:
        print "Exception when updating roles for the user " + new_user.name
        print e


def get_roles(destination):
    keystone = get_keystone(destination)
    roles = keystone.roles.list()
    return roles


def find_opposite_role(role_id):
    from_roles = get_roles('from')
    to_roles = get_roles('to')

    from_role = filter(lambda from_roles: from_roles.id == role_id, from_roles)
    if from_role:
        if from_role[0].name == '_identity_internal_role_':
            return {'from_id': 'None', 'name': 'None', 'to_id': 'None'}
        if from_role[0].name == 'member':
            to_role = filter(lambda to_roles: to_roles.name == '_member_', to_roles)
        else:
            to_role = filter(lambda to_roles: to_roles.name == from_role[0].name, to_roles)
        if to_role:
            return {'from_id': from_role[0].id, 'name': to_role[0].name, 'to_id': to_role[0].id}
        else:
            print "to_role named", from_role[0].name, "not found"
            return {'from_id': 'None', 'name': 'None', 'to_id': 'None'}

    to_role = filter(lambda to_roles: to_roles.id == role_id, to_roles)
    if to_role:
        from_role = filter(lambda from_roles: from_roles.name == to_role[0].name, from_roles)
        return {'from_id': from_role[0].id, 'name': to_role[0].name, 'to_id': to_role[0].id}

    # if didn't find anything, return a lot of nones.
    return {'from_id': 'None', 'name': 'None', 'to_id': 'None'}


def build_role_from_to_list():
    from_roles = get_roles('from')
    to_roles = get_roles('to')
    roles = []
    for from_role in from_roles:
        if from_role.name == '_identity_internal_role_':
            rol = {'from_id': from_role.id, 'name': '_identity_internal_role_', 'to_id': 'None'}
            roles.append(rol)
        if from_role.name == 'member':
            to_role = filter(lambda to_roles: to_roles.name == '_member_', to_roles)
        else:
            to_role = filter(lambda to_roles: to_roles.name == from_role.name, to_roles)
        if to_role:
            rol = {'from_id': from_role.id, 'name': to_role[0].name, 'to_id': to_role[0].id}
            roles.append(rol)
    return roles


def print_user_names(destination):
    auth = AuthStack()
    us = get_users_based_on_project(destination, auth.from_tenant_name)
    users = sorted(us, key=lambda x: x.name)
    version = '3'
    if destination == "from":
        if auth.from_keystone_version == '2':
            version = '2'
    if destination == 'to':
        if auth.to_keystone_version == '2':
            version = '2'
    if version == '2':
        print "Name:                     Tenant ID:"
        for u in users:
            if hasattr(u, 'tenantId'):
                print '{:25}'.format(u.name), u.tenantId
            else:
                print u.name
    else:
        print "Name:                     Domain:                             Default Project ID:"
        for u in users:
            if hasattr(u, 'default_project_id'):
                print '{:25}'.format(u.name), '{:35}'.format(u.domain_id), u.default_project_id
            else:
                print '{:25}'.format(u.name), u.domain_id


def get_user_by_name(destination, name):
    keystone = get_keystone(destination)
    users = keystone.users.list()
    for user in users:
        if user.name == name:
            return user


def get_user_by_id(destination, id):
    keystone = get_keystone(destination)
    user = keystone.users.get(id)
    print user
    return user

def get_from_tenant_by_name(name):
    keystone = get_keystone('from')
    tenants = get_from_tenant_list()
    auth = AuthStack()
    for tenant in tenants:
        if tenant.name == name:
            return tenant


def print_roles(destination):
    roles = get_roles(destination)
    print "       Roles: ID,  name"
    for role in roles:
        print role.id, "   ", role.name


def main():
    #compare_and_create_tenants()
    #get_from_to_name_tenant_ids()
    #print find_opposite_tenant_id('e99e58c687ec4a608f4323d22a29c08e')
    # print get_from_tenant_list()
    # projects = get_from_tenant_list()
    # print projects
    #get_keystone('to')
    #get_from_tenant_list()
    #get_to_tenant_list()
    #get_from_tenant_names()
    # print get_users('from')
    # print get_users('to')
    # compare_and_create_users()
    # print get_from_to_name_user_ids()
    # print_tenants('to')
    # print get_to_project_list(name="demo")
    # print list_roles("from", '08d53ca0a9304f28ad299a9a63dc4b68', 'a370cc1a5e4e409c80f41d50c3fa0ee5')
    # print get_roles_for_tenant('from', 'a370cc1a5e4e409c80f41d50c3fa0ee5')
    # projects = get_from_project_list()
    # create_project('to', projects[0])
    # print projects

    # print_user_names('from')
    # tenants = get_from_tenant_list()
    # print tenants
    #get_keystone("from")
    # print_projects("to")
    # print get_users_based_on_project("from", "admin")
    # print get_from_project_list()
    # compare_and_create_users_by_project()
    # print_users_per_project("from")
    # print get_users_based_on_domain('from')
    # compare_and_create_users_by_domain()
    # get_matrix()
    # compare_and_create_users_by_domain("password")
    # build_matrix()
    # get_user_roles('from', 'myuser')
    print_roles('to')

if __name__ == "__main__":
        main()
