#!/usr/bin/env python

import json
import argparse
import optparse
import keystone_common
import neutron_common
import nova_common
import glance_common
import cinder_common
from auth_stack import AuthStack


def main(opts, args):
    auth = AuthStack()
    print "From:", auth.from_auth_ip
    print "To:", auth.to_auth_ip
    if opts.report:
        from_tenants = keystone_common.get_from_tenant_list()
        print "=============== From Tenants: ======================"
        print from_tenants
        to_tenants = keystone_common.get_to_tenant_list()
        print "=============== To Tenants: ========================"
        print to_tenants
        from_to_tenant = keystone_common.get_from_to_name_tenant_ids()
        print "================ Tenant ID mappings: ==============="
        print json.dumps(from_to_tenant, indent=4)

        from_networks = neutron_common.get_network_list('from')
        print "=============== From Networks: ======================"
        print from_networks
        print "=============== To Networks: ========================"
        to_networks = neutron_common.get_network_list('to')
        print to_networks
        print "===============From Security Groups: ========================"
        from_sec = nova_common.get_security_groups('from')
        print from_sec
        print "===============To Security Groups: ========================"
        print nova_common.get_security_groups('to')
    if opts.copynets:
        neutron_common.compare_and_create_networks()
    if opts.copysec:
        nova_common.compare_and_create_security_groups()
    if opts.download:
        if args:
            print args[0]
            glance_common.download_images('from', path=args[0])
        else:
            print "Please provide download directory, for example, ./downloads/"
    if opts.upload:
        if args:
            print args[0]
            glance_common.create_images(path=args[0])
        else:
            print "Please provide image directory, for example, ./downloads/"
    if opts.flavors:
        nova_common.compare_and_create_flavors()
    if opts.volumes:
        cinder_common.compare_and_create_volumes()
    if opts.nova:
        nova_common.compare_and_create_vms()
    if opts.quota:
        nova_common.compare_and_report_quotas()
    if opts.tenants:
        print keystone_common.get_from_tenant_names()
        print keystone_common.get_to_tenant_names()

if __name__ == "__main__":

        parser = optparse.OptionParser()
        parser.add_option("-t", "--tenants", action='store_true', dest='tenants',
                          help='Print to and from tenants. Tenant names must match before running the rest of copystack')
        parser.add_option("-q", "--quota", action='store_true', dest='quota',
                          help='Differences in individual quotas for each tenant')
        parser.add_option("-c", "--copynets", action="store_true", dest='copynets',
                          help='Copy networks and subnets from->to')
        parser.add_option("-s", "--copysec", action="store_true", dest='copysec',
                          help='Copy security groups from -> to')
        parser.add_option("-d", "--download", action="store_true", dest='download',
                          help='Download all images to a specified path, for example, ./downloads/')
        parser.add_option("-u", "--upload", action="store_true", dest='upload',
                          help='Recreate all images in a new environment. Provide a path, for example, ./downloads/ '
                               'where images from "-d" where stored. '
                               'Will not check for duplicate image names, since duplicate names are allowed.')
        parser.add_option("-f", "--flavors", action='store_true', dest='flavors', help='Copy flavors from -> to')
        parser.add_option("-n", "--nova", action='store_true', dest='nova', help='Recreate VMs from -> to')
        parser.add_option("-v", "--volumes", action='store_true', dest='volumes', help='Recreate volumes from -> to')
        parser.add_option("-r", "--report", action='store_true', dest='report', help='Print Summary of Things')

        (opts, args) = parser.parse_args()
        main(opts, args)