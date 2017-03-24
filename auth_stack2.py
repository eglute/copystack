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
from keystoneauth1 import session
from keystoneclient.v3 import client
from novaclient import client as nova_client
from neutronclient.neutron import client as neutron_client
from glanceclient import Client as glance_client
from cinderclient.client import Client as cinder_client
from cinderclient import exceptions as c_exc
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

        self.to_auth_url = to_auth['OS_AUTH_URL']
        self.to_auth_ip = to_auth['OS_AUTH_IP']
        self.to_username = to_auth['OS_USERNAME']
        self.to_password = to_auth['OS_PASSWORD']
        self.to_tenant_name = to_auth['OS_TENANT_NAME']
        self.to_cert = to_auth['OS_CACERT']
        self.to_user_domain_id = to_auth['USER_DOMAIN_ID']
        self.to_project_domain_id = to_auth['PROJECT_DOMAIN_ID']

        #to disable warnings on certs missing subjectAltName
        #https://github.com/shazow/urllib3/issues/497#issuecomment-66942891
        requests.packages.urllib3.disable_warnings()

    def get_from_auth_ref(self):
        # keystone = client.Client(username=self.from_username, password=self.from_password,
        #                     tenant_name=self.from_tenant_name, auth_url=self.from_auth_url)
        # return keystone.auth_ref

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

        # auth_ref = self.get_from_auth_ref()
        # keystone = client.Client(auth_ref=auth_ref, endpoint=self.from_auth_url)
        #
        # return keystone
        return self.get_from_auth_ref()

    def get_to_keystone_client(self):
        return self.get_to_auth_ref()

    def get_keystone_client(self, destination):
        if destination == 'to':
            return self.get_to_keystone_client()
        else:
            return self.get_from_keystone_client()

    def get_from_nova_client(self):

        auth_ref = self.get_from_auth_ref()

        #todo: check this works for before newton. might have to change it to tenant_id
        project_id = auth_ref.session.get_project_id()
        bypass_url = '{ip}:8774/v2.1/{tenant_id}' \
            .format(ip=self.from_auth_ip, tenant_id=project_id)

        nova = nova_client.Client('2.1', session=auth_ref.session, endpoint_override=bypass_url)
        return nova

    def get_to_nova_client(self):
        auth_ref = self.get_to_auth_ref()

        # todo: check this works for before newton. might have to change it to tenant_id
        project_id = auth_ref.session.get_project_id()
        bypass_url = '{ip}:8774/v2.1/{tenant_id}' \
            .format(ip=self.to_auth_ip, tenant_id=project_id)

        nova = nova_client.Client('2.1', session=auth_ref.session, endpoint_override=bypass_url)
        return nova

    def get_nova_client(self, destination):
        if destination == 'to':
            return self.get_to_nova_client()
        else:
            return self.get_from_nova_client()

    def get_from_neutron_client(self):
        auth_ref = self.get_from_auth_ref()
        endpoint_url = '{ip}:9696'.format(ip=self.from_auth_ip)
        neutron = neutron_client.Client('2.0', session=auth_ref.session, endpoint_override=endpoint_url)
        return neutron

    def get_to_neutron_client(self):
        auth_ref = self.get_to_auth_ref()
        endpoint_url = '{ip}:9696'.format(ip=self.to_auth_ip)
        neutron = neutron_client.Client('2.0', session=auth_ref.session, endpoint_override=endpoint_url)
        return neutron

    def get_neutron_client(self, destination):
        if destination == 'to':
            return self.get_to_neutron_client()
        else:
            return self.get_from_neutron_client()

    def get_from_glance_client(self):

        auth_ref = self.get_from_auth_ref()
        endpoint_url = '{ip}:9292/v1'.format(ip=self.from_auth_ip)
        glance = glance_client('1', endpoint=endpoint_url, session=auth_ref.session)
        return glance

    def get_to_glance_client(self):

        auth_ref = self.get_to_auth_ref()
        endpoint_url = '{ip}:9292/v1'.format(ip=self.to_auth_ip)
        glance = glance_client('1', endpoint=endpoint_url, session=auth_ref.session)
        return glance

    def get_glance_client(self, destination):
        if destination == 'to':
            return self.get_to_glance_client()
        else:
            return self.get_from_glance_client()

    def get_from_cinder_client(self):
        auth_ref = self.get_from_auth_ref()
        project_id = auth_ref.session.get_project_id()
        print project_id
        endpoint_url = ('{ip}:8776/v1/{project_id}'.format
                       (ip=self.from_auth_ip, project_id=project_id))

        cinder = cinder_client('1', session=auth_ref.session)
        cinder.client.management_url = endpoint_url

        return cinder

    def get_to_cinder_client(self):

        auth_ref = self.get_to_auth_ref()
        project_id = auth_ref.session.get_project_id()
        endpoint_url = ('{ip}:8776/v1/{project_id}'.format
                       (ip=self.to_auth_ip, project_id=project_id))

        cinder = cinder_client('1', session=auth_ref.session)
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
                    'PROJECT_DOMAIN_ID': None }

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
