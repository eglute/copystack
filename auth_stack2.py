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

import contextlib
import datetime
import errno
import json
import logging
import os
import re
import sys
import traceback

from log import logging
from keystoneauth1.identity import v3
from keystoneauth1.identity import v2
from keystoneauth1 import session
from keystoneclient.v3 import client
from keystoneclient.v2_0 import client as client_v2
from novaclient import client as nova_client
from neutronclient.neutron import client as neutron_client
from glanceclient import Client as glance_client
from cinderclient.client import Client as cinder_client
# from cinderclient import exceptions as c_exc

from neutronclient.common import exceptions as n_exc
from novaclient.client import exceptions as nova_exc
from glanceclient import exc as g_exc
from keystoneclient.openstack.common.apiclient import exceptions as k_exc

import requests.packages.urllib3

OPENRC_FROM = './from_auth'
OPENRC_TO = './to_auth'




class AuthStack(object):

    def __init__(self):

        logger = logging.getLogger('copystack')
        logger = logging.getLogger('copystack.auth_stack.AuthStack')
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)

        from_auth = self.get_auth_details('from')
        to_auth = self.get_auth_details('to')

        self.from_auth_url = from_auth['OS_AUTH_URL']
        self.from_auth_ip = from_auth['OS_AUTH_IP']
        self.from_username = from_auth['OS_USERNAME']
        self.from_password = from_auth['OS_PASSWORD']
        self.from_tenant_name = from_auth['OS_TENANT_NAME']
        self.from_cert = from_auth['OS_CACERT']
        self.from_user_domain_id = from_auth['USER_DOMAIN_ID']
        self.from_project_domain_id = from_auth['PROJECT_DOMAIN_ID']
        self.from_cinder_version = from_auth['CINDER_VERSION']
        self.from_keystone_version = from_auth['KEYSTONE_VERSION']
        self.from_nova_version = from_auth['NOVA_VERSION']
        self.solid_fire_ip = from_auth['SOLID_FIRE_IP']
        self.solid_fire_user = from_auth['SOLID_FIRE_USER']
        self.solid_fire_password = from_auth['SOLID_FIRE_PASSWORD']
        self.solid_fire_host = from_auth['SOLID_FIRE_HOST']
        self.nfs_host = from_auth['NFS_HOST']
        self.nfs_dir = from_auth['NFS_DIR']
        self.nfs_ip = from_auth['NFS_IP']
        self.nfs_libvirt_location = from_auth['NFS_LIBVIRT_LOCATION']
        self.from_nfs_glance_location = from_auth['NFS_GLANCE_LOCATION']
        self.nfs_cinder_location = from_auth['NFS_CINDER_LOCATION']


        self.from_nova_port = from_auth['NOVA_PORT']
        self.from_cinder_port = from_auth['CINDER_PORT']
        # self.from_keystone_port = from_auth['KEYSTONE_PORT']
        self.from_neutron_port = from_auth['NEUTRON_PORT']
        self.from_glance_port = from_auth['GLANCE_PORT']
        self.from_domain_id = from_auth['DOMAIN_ID']

        self.to_auth_url = to_auth['OS_AUTH_URL']
        self.to_auth_ip = to_auth['OS_AUTH_IP']
        self.to_username = to_auth['OS_USERNAME']
        self.to_password = to_auth['OS_PASSWORD']
        self.to_tenant_name = to_auth['OS_TENANT_NAME']
        self.to_cert = to_auth['OS_CACERT']
        self.to_user_domain_id = to_auth['USER_DOMAIN_ID']
        self.to_project_domain_id = to_auth['PROJECT_DOMAIN_ID']
        self.to_cinder_version = to_auth['CINDER_VERSION']
        self.to_keystone_version = to_auth['KEYSTONE_VERSION']
        self.to_nova_version = to_auth['NOVA_VERSION']

        self.to_nova_port = to_auth['NOVA_PORT']
        self.to_cinder_port = to_auth['CINDER_PORT']
        # self.to_keystone_port = to_auth['KEYSTONE_PORT']
        self.to_neutron_port = to_auth['NEUTRON_PORT']
        self.to_glance_port = to_auth['GLANCE_PORT']
        self.to_domain_id = to_auth['DOMAIN_ID']
        self.to_nfs_glance_location = to_auth['NFS_GLANCE_LOCATION']

        #to disable warnings on certs missing subjectAltName
        #https://github.com/shazow/urllib3/issues/497#issuecomment-66942891
        requests.packages.urllib3.disable_warnings()

    def get_from_auth_ref(self):
        if self.from_keystone_version == '2':
            keystone = client_v2.Client(cacert=self.from_cert, username=self.from_username, password=self.from_password,
                                tenant_name=self.from_tenant_name, auth_url=self.from_auth_url)
            # keystone.management_url = self.from_auth_url
            # keystone.auth_url = self.from_auth_url
            # print keystone.auth_ref
            # print keystone
        else:
            auth = v3.Password(auth_url=self.from_auth_url, username=self.from_username, password=self.from_password,
                               project_name=self.from_tenant_name, user_domain_id=self.from_user_domain_id,
                               project_domain_id=self.from_project_domain_id)
            sess = session.Session(auth=auth,
                                   verify=self.from_cert)

            keystone = client.Client(session=sess, endpoint_override=self.from_auth_url)

        return keystone

    def get_to_auth_ref(self):
        auth = v3.Password(auth_url=self.to_auth_url, username=self.to_username, password=self.to_password,
                            project_name=self.to_tenant_name, user_domain_id=self.to_user_domain_id,
                            project_domain_id=self.to_project_domain_id)
        sess = session.Session(auth=auth, verify=self.to_cert)

        keystone = client.Client(session=sess, endpoint_override=self.to_auth_url)
        return keystone

    def get_from_keystone_client(self):
        return self.get_from_auth_ref()

    def get_to_keystone_client(self):
        return self.get_to_auth_ref()

    def get_keystone_client(self, destination):
        if destination == 'to':
            return self.get_to_keystone_client()
        else:
            return self.get_from_keystone_client()

    def get_from_nova_client(self):
        if self.from_nova_version == '2':
            auth_ref = self.get_from_auth_ref().auth_ref
            auth_token = auth_ref['token']['id']
            tenant_id = auth_ref['token']['tenant']['id']

            bypass_url = '{ip}:{port}/v2/{tenant_id}' \
                         .format(ip=self.from_auth_ip, port=self.from_nova_port, tenant_id=tenant_id)

            nova = nova_client.Client('2', auth_token=auth_token, bypass_url=bypass_url, cacert=self.from_cert)
        else:
            auth_ref = self.get_from_auth_ref()

            # todo: check this works for before newton. might have to change it to tenant_id
            project_id = auth_ref.session.get_project_id()
            bypass_url = '{ip}:{port}/v2.1/{tenant_id}' \
                .format(ip=self.from_auth_ip, port=self.from_nova_port, tenant_id=project_id)

            nova = nova_client.Client('2.1', session=auth_ref.session, endpoint_override=bypass_url)
        return nova

    def get_to_nova_client(self):
        auth_ref = self.get_to_auth_ref()

        # todo: check this works for before newton. might have to change it to tenant_id
        project_id = auth_ref.session.get_project_id()
        bypass_url = '{ip}:{port}/v2.1/{tenant_id}' \
            .format(ip=self.to_auth_ip, port=self.to_nova_port, tenant_id=project_id)

        nova = nova_client.Client('2.1', session=auth_ref.session, endpoint_override=bypass_url)
        return nova

    def get_nova_client(self, destination):
        if destination == 'to':
            return self.get_to_nova_client()
        else:
            return self.get_from_nova_client()

    def get_from_neutron_client(self):
        auth_ref = self.get_from_auth_ref()
        endpoint_url = '{ip}:{port}'.format(ip=self.from_auth_ip, port=self.from_neutron_port)
        neutron = neutron_client.Client('2.0', session=auth_ref.session, endpoint_override=endpoint_url)
        return neutron

    def get_to_neutron_client(self):
        auth_ref = self.get_to_auth_ref()
        endpoint_url = '{ip}:{port}'.format(ip=self.to_auth_ip, port=self.to_neutron_port)
        neutron = neutron_client.Client('2.0', session=auth_ref.session, endpoint_override=endpoint_url)
        return neutron

    def get_neutron_client(self, destination):
        if destination == 'to':
            return self.get_to_neutron_client()
        else:
            return self.get_from_neutron_client()

    def get_from_glance_client(self):

        auth_ref = self.get_from_auth_ref()
        endpoint_url = '{ip}:{port}'.format(ip=self.from_auth_ip, port=self.from_glance_port)
        glance = glance_client('2', session=auth_ref.session, endpoint=endpoint_url)
        return glance

    def get_to_glance_client(self):

        auth_ref = self.get_to_auth_ref()
        endpoint_url = '{ip}:{port}'.format(ip=self.to_auth_ip, port=self.to_glance_port,)
        glance = glance_client('2', endpoint=endpoint_url, session=auth_ref.session)
        return glance

    def get_glance_client(self, destination):
        if destination == 'to':
            return self.get_to_glance_client()
        else:
            return self.get_from_glance_client()

    def get_from_cinder_client(self):
        if self.from_keystone_version == '2':
            return self.get_from_cinder_client_keystone2()
        else:
            return self.get_from_cinder_client_keystone3()

    # this is really more about which keystone version is running... if keystone 2, use this call
    # if keystone 3, the other
    def get_from_cinder_client_keystone2(self):
        auth_ref = self.get_from_auth_ref().auth_ref
        # auth_ref = self.get_from_auth_ref()
        token = auth_ref['token']['id']
        tenant_id = auth_ref['token']['tenant']['id']
        endpoint_url = ('{ip}:{port}/v1/{tenant}'.format
                        (ip=self.from_auth_ip, port=self.from_cinder_port, tenant=tenant_id))

        print endpoint_url
        cinder = cinder_client('1', self.from_username, token,
                               project_id=self.from_tenant_name,
                               auth_url=self.from_auth_url, cacert=self.from_cert)
        cinder.client.auth_token = token
        cinder.client.management_url = endpoint_url

        return cinder

    def get_from_cinder_client_keystone3(self):
        auth_ref = self.get_from_auth_ref()
        project_id = auth_ref.session.get_project_id()
        endpoint_url = ('{ip}:{port}/v{version}/{project_id}'.format
                        (ip=self.from_auth_ip, port=self.from_cinder_port, version=self.from_cinder_version, project_id=project_id))

        cinder = cinder_client(self.from_cinder_version, session=auth_ref.session, bypass_url=endpoint_url)
        cinder.client.management_url = endpoint_url

        return cinder

    def get_to_cinder_client(self):

        auth_ref = self.get_to_auth_ref()
        project_id = auth_ref.session.get_project_id()
        endpoint_url = ('{ip}:{port}/v2/{project_id}'.format
                       (ip=self.to_auth_ip, port=self.to_cinder_port, project_id=project_id))

        cinder = cinder_client('2', session=auth_ref.session, bypass_url=endpoint_url)
        cinder.client.management_url = endpoint_url
        return cinder

    def get_cinder_client(self, destination):
        if destination == 'to':
            return self.get_to_cinder_client()
        else:
            return self.get_from_cinder_client()

    def get_auth_details(self, destination):
        AUTH_DETAILS = {'OS_USERNAME': None,
                    'OS_PASSWORD': None,
                    'OS_TENANT_NAME': None,
                    'OS_AUTH_URL': None,
                    'OS_AUTH_IP': None,
                    'OS_CACERT': None,
                    'USER_DOMAIN_ID': None,
                    'PROJECT_DOMAIN_ID': None,
                    'CINDER_VERSION': None,
                    'KEYSTONE_VERSION': None,
                    'NOVA_VERSION': None,
                    'NOVA_PORT': None,
                    'CINDER_PORT': None,
                    'GLANCE_PORT': None,
                    'NEUTRON_PORT': None,
                    'DOMAIN_ID': None,
                    'SOLID_FIRE_IP': None,
                    'SOLID_FIRE_USER': None,
                    'SOLID_FIRE_PASSWORD': None,
                    'SOLID_FIRE_HOST': None,
                    'NFS_HOST': None,
                    'NFS_DIR' : None,
                    'NFS_IP' : None,
                    'NFS_LIBVIRT_LOCATION': None,
                    'NFS_GLANCE_LOCATION': None,
                    'NFS_CINDER_LOCATION': None
                        }

        auth_details = AUTH_DETAILS
        pattern = re.compile(
            '^(?:export\s)?(?P<key>\w+)(?:\s+)?=(?:\s+)?(?P<value>.*)$'
        )

        try:
            if destination == 'to':
                openrc_file = OPENRC_TO
            else:
                openrc_file = OPENRC_FROM

            with open(openrc_file) as openrc:
                for line in openrc:
                    match = pattern.match(line)
                    if match is None:
                        continue
                    k = match.group('key')
                    v = match.group('value')
                    if k in auth_details and auth_details[k] is None:
                        auth_details[k] = v
        except IOError as e:
            if e.errno != errno.ENOENT:
                print str(e)
            # no openrc file, so we try the environment
            for key in auth_details.keys():
                auth_details[key] = os.environ.get(key)

        for key in auth_details.keys():
            if auth_details[key] is None:
                print '%s not set' % key

        return auth_details