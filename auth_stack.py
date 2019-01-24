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

from keystoneclient.v2_0 import client as client
from novaclient import client as nova_client
from neutronclient.neutron import client as neutron_client
from glanceclient import Client as glance_client
from cinderclient.client import Client as cinder_client
from cinderclient import exceptions as c_exc
from neutronclient.common import exceptions as n_exc
from novaclient.client import exceptions as nova_exc
from glanceclient import exc as g_exc
from keystoneclient.openstack.common.apiclient import exceptions as k_exc

OPENRC_FROM = './from_auth'
OPENRC_TO = './to_auth'

class AuthStack(object):

    def __init__(self):

        from_auth = self.get_auth_details('from')
        to_auth = self.get_auth_details('to')

        self.from_auth_url = from_auth['OS_AUTH_URL']
        self.from_auth_ip = from_auth['OS_AUTH_IP']
        self.from_username = from_auth['OS_USERNAME']
        self.from_password = from_auth['OS_PASSWORD']
        self.from_tenant_name = from_auth['OS_TENANT_NAME']

        self.to_auth_url = to_auth['OS_AUTH_URL']
        self.to_auth_ip = to_auth['OS_AUTH_IP']
        self.to_username = to_auth['OS_USERNAME']
        self.to_password = to_auth['OS_PASSWORD']
        self.to_tenant_name = to_auth['OS_TENANT_NAME']

    def get_from_auth_ref(self):
        keystone = client.Client(username=self.from_username, password=self.from_password,
                            tenant_name=self.from_tenant_name, auth_url=self.from_auth_url)
        return keystone.auth_ref

    def get_to_auth_ref(self):
        keystone = client.Client(username=self.to_username, password=self.to_password,
                            tenant_name=self.to_tenant_name, auth_url=self.to_auth_url)
        return keystone.auth_ref

    def get_from_keystone_client(self):

        auth_ref = self.get_from_auth_ref()
        keystone = client.Client(auth_ref=auth_ref, endpoint=self.from_auth_url)
        return keystone

    def get_to_keystone_client(self):

        auth_ref = self.get_to_auth_ref()
        keystone = client.Client(auth_ref=auth_ref, endpoint=self.to_auth_url)

        return keystone

    def get_keystone_client(self, destination):
        if destination == 'to':
            return self.get_to_keystone_client()
        else:
            return self.get_from_keystone_client()

    def get_from_nova_client(self):
        # nova = nova_client.Client('2', self.from_username, self.from_password,
        #                     self.from_tenant_name, self.from_auth_url)

        auth_ref = self.get_from_auth_ref()
        auth_token = auth_ref['token']['id']
        tenant_id = auth_ref['token']['tenant']['id']

        bypass_url = 'http://{ip}:8774/v2.1/{tenant_id}' \
                     .format(ip=self.from_auth_ip, tenant_id=tenant_id)

        nova = nova_client.Client('2.1', auth_token=auth_token, bypass_url=bypass_url)
        return nova

    def get_to_nova_client(self):
        # nova = nova_client.Client('2', self.to_username, self.to_password,
        #                     self.to_tenant_name, self.to_auth_url)

        auth_ref = self.get_to_auth_ref()
        auth_token = auth_ref['token']['id']
        tenant_id = auth_ref['token']['tenant']['id']

        bypass_url = 'http://{ip}:8774/v2/{tenant_id}' \
                     .format(ip=self.to_auth_ip, tenant_id=tenant_id)

        nova = nova_client.Client('2', auth_token=auth_token, bypass_url=bypass_url)
        return nova

    def get_nova_client(self, destination):
        if destination == 'to':
            return self.get_to_nova_client()
        else:
            return self.get_from_nova_client()

    def get_from_neutron_client(self):
        auth_ref = self.get_from_auth_ref()
        token = auth_ref['token']['id']
        endpoint_url = 'http://{ip}:9696'.format(ip=self.from_auth_ip)
        neutron = neutron_client.Client('2.0', token=token, endpoint_url=endpoint_url)
        return neutron

    def get_to_neutron_client(self):
        auth_ref = self.get_to_auth_ref()
        token = auth_ref['token']['id']
        endpoint_url = 'http://{ip}:9696'.format(ip=self.to_auth_ip)
        neutron = neutron_client.Client('2.0', token=token, endpoint_url=endpoint_url)
        return neutron

    def get_neutron_client(self, destination):
        if destination == 'to':
            return self.get_to_neutron_client()
        else:
            return self.get_from_neutron_client()

    def get_from_glance_client(self):

        auth_ref = self.get_from_auth_ref()
        token = auth_ref['token']['id']
        endpoint_url = 'http://{ip}:9292/v1'.format(ip=self.from_auth_ip)
        glance = glance_client('1', endpoint=endpoint_url, token=token)
        return glance

    def get_to_glance_client(self):

        auth_ref = self.get_to_auth_ref()
        token = auth_ref['token']['id']
        endpoint_url = 'http://{ip}:9292/v1'.format(ip=self.to_auth_ip)
        glance = glance_client('1', endpoint=endpoint_url, token=token)
        return glance

    def get_glance_client(self, destination):
        if destination == 'to':
            return self.get_to_glance_client()
        else:
            return self.get_from_glance_client()

    def get_from_cinder_client(self):
        auth_ref = self.get_from_auth_ref()
        token = auth_ref['token']['id']

        tenant_id = auth_ref['token']['tenant']['id']
        endpoint_url = ('http://{ip}:8776/v1/{tenant}'.format
                       (ip=self.from_auth_ip, tenant=tenant_id))

        cinder = cinder_client('1', self.from_username, token,
                               project_id=self.from_tenant_name,
                               auth_url=self.from_auth_url)
        cinder.client.auth_token = token
        cinder.client.management_url = endpoint_url

        return cinder

    def get_to_cinder_client(self):

        auth_ref = self.get_to_auth_ref()
        token = auth_ref['token']['id']

        tenant_id = auth_ref['token']['tenant']['id']
        endpoint_url = ('http://{ip}:8776/v1/{tenant}'.format
                       (ip=self.to_auth_ip, tenant=tenant_id))

        cinder = cinder_client('1', self.to_username, token,
                               project_id=self.to_tenant_name,
                               auth_url=self.to_auth_url)
        cinder.client.auth_token = token
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
                    'OS_AUTH_IP': None}

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
