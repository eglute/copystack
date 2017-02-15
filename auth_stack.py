import os_client_config

class AuthStack(object):

    def get_client(self, client, destination):
        return os_client_config.make_client(client, cloud=destination)

    def get_keystone_client(self, destination):
        return self.get_client('identity', destination)

    def get_nova_client(self, destination):
        return self.get_client('compute', destination)

    def get_neutron_client(self, destination):
        return self.get_client('network', destination)

    def get_glance_client(self, destination):
        return self.get_client('image', destination)

    def get_cinder_client(self, destination):
        return self.get_client('volume', destination)
