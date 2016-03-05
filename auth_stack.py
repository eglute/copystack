from keystoneclient.v2_0 import client as client
from novaclient import client as nova_client
from neutronclient.v2_0 import client as neutron_client

class AuthStack(object):

    def __init__(self):
        """Inits the client manager.
        :param auth_url: String keystone auth url
        :param username: String openstack username
        :param password: String openstack password
        :param project_id: String project_id - Tenant uuid
        """
        # self.from_nova = None
        # self.from_glance = None
        # self.from_cinder = None


        self.from_auth_url = 'http://166.78.121.160:35357/v2.0'
        self.from_auth_ip = '166.78.121.160'
        self.from_username = 'admin'
        self.from_password = 'DEVSTACK_PASSWORD'
        self.from_tenant_name = 'demo'

        # self.from_auth_url = 'http://172.16.56.128:35357/v2.0/'
        # self.from_auth_ip = '172.16.56.128'
        # self.from_username = 'myadmin'
        # self.from_password = 'mypassword'
        # self.from_tenant_name = 'MyProject'

        # self.to_nova = None
        # self.to_glance = None
        # self.to_cinder = None
        self.to_auth_url = 'http://166.78.250.56:35357/v2.0'
        self.to_auth_ip = '166.78.250.56'
        self.to_username = 'admin'
        self.to_password = 'DEVSTACK_PASSWORD'
        self.to_tenant_name = 'demo'


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

        bypass_url = 'http://{ip}:8774/v2/{tenant_id}' \
                     .format(ip=self.from_auth_ip, tenant_id=tenant_id)

        nova = nova_client.Client('2', auth_token=auth_token, bypass_url=bypass_url)
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
        neutron = neutron_client.Client(username=self.from_username, password=self.from_password,
                            tenant_name=self.from_tenant_name, auth_url=self.from_auth_url)
        return neutron

    def get_to_neutron_client(self):
        neutron = neutron_client.Client(username=self.to_username, password=self.to_password,
                            tenant_name=self.to_tenant_name, auth_url=self.to_auth_url)
        return neutron

    def get_neutron_client(self, destination):
        if destination == 'to':
            return self.get_to_neutron_client()
        else:
            return self.get_from_neutron_client()


