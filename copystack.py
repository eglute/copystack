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

        print "===============From VMs: ========================"
        vms = nova_common.print_vm_list_ids('from')
        print "===============To VMs: ========================"
        vms = nova_common.print_vm_list_ids('to')
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
    if opts.createtenants:
        keystone_common.compare_and_create_tenants()
    if opts.publickeys:
        nova_common.compare_and_create_keypairs()
    if opts.users:
        keystone_common.compare_and_create_users()
    if opts.shutdown:
        if args:
            print args[0]
            nova_common.power_off_vms('from', id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be shutdown, for example, ./id_file"
    if opts.createimages:
        if args:
            print args[0]
            nova_common.create_image_from_vm('from', id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be shutdown, for example, ./id_file"
    if opts.downloadbyid:
        if len(args) == 2:
            print args[0]
            print args[1]
            glance_common.download_images_by_vm_uuid('from', path=args[0], uuid_file=args[1])
            volumes = nova_common.get_volume_id_list_for_vm_ids('from', id_file=args[1])
            glance_common.download_images_by_volume_uuid('from', path=args[0], volumes=volumes)
        else:
            print "Please provide download directory and file with VM UUIDs to be downloaded, " \
                  "for example, ./downloads/ ./id_file"
    if opts.uploadbyid:
        if len(args) == 2:
            print args[0]
            print args[1]
            glance_common.upload_images_by_vm_uuid(path=args[0], uuid_file=args[1])
        else:
            print "Please provide download directory and file with VM UUIDs to be uploaded, " \
                  "for example, ./downloads/ ./id_file"

    if opts.migratevms:
        if args:
            print args[0]
            nova_common.migrate_vms_from_image(id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    if opts.createvolumes:
        if args:
            print args[0]
            cinder_common.create_volume_from_image_by_vm_ids(id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"

if __name__ == "__main__":

        parser = optparse.OptionParser()
        parser.add_option("-t", "--tenants", action='store_true', dest='tenants',
                          help='Print to and from tenants. Tenant names must match before running the rest of copystack')
        parser.add_option("-x", "--createtenants", action='store_true', dest='createtenants',
                          help='Create tenants from->to. Tenant names must match before running the rest of copystack')
        parser.add_option("-u", "--users", action='store_true', dest='users',
                          help='Create users from->to. Users created without passwords')
        parser.add_option("-p", "--publickeys", action='store_true', dest='publickeys',
                          help='Copy public keys from -> to')
        parser.add_option("-q", "--quota", action='store_true', dest='quota',
                          help='Differences in individual quotas for each tenant')
        parser.add_option("-c", "--copynets", action="store_true", dest='copynets',
                          help='Copy networks and subnets from->to')
        parser.add_option("-s", "--copysec", action="store_true", dest='copysec',
                          help='Copy security groups from -> to')
        parser.add_option("-d", "--download", action="store_true", dest='download',
                          help='Download all images to a specified path, for example, ./downloads/')
        parser.add_option("-l", "--upload", action="store_true", dest='upload',
                          help='Recreate all images in a new environment. Provide a path, for example, ./downloads/ '
                               'where images from "-d" where stored. '
                               'Will not check for duplicate image names, since duplicate names are allowed.')
        parser.add_option("-f", "--flavors", action='store_true', dest='flavors', help='Copy flavors from -> to')
        parser.add_option("-n", "--nova", action='store_true', dest='nova',
                          help='Recreate VMs from -> to. '
                               'No user data is set on creation, will create as logged in user.')
        parser.add_option("-v", "--volumes", action='store_true', dest='volumes', help='Recreate volumes from -> to')
        parser.add_option("-r", "--report", action='store_true', dest='report', help='Print Summary of Things')
        parser.add_option("-m", "--shutdown", action="store_true", dest='shutdown',
                          help='Shutdown VMs for each UUID provided in a file, for example, ./id_file')
        parser.add_option("-i", "--createimages", action="store_true", dest='createimages',
                          help='Create images from VMs for each UUID provided in a file, for example, ./id_file. '
                               'Volumes attached to VMs will also be their images created.')
        parser.add_option("-o", "--downloadbyid", action="store_true", dest='downloadbyid',
                          help='First argument directory path, second path to a file. '
                               'Download all images to a specified path, for example, ./downloads/ '
                               'for each UUID provided in a file, for example, ./id_file. '
                               'Volumes associated with the VMs will also be downloaded.')
        parser.add_option("-k", "--uploadbyid", action="store_true", dest='uploadbyid',
                          help='First argument directory path, second path to a file. '
                               'Upload all images from a specified path, for example, ./downloads/ '
                               'for each UUID provided in a file, for example, ./id_file. '
                               'Volumes associated with the VMs will also be uploaded.')
        parser.add_option("-g", "--migratevms", action="store_true", dest='migratevms',
                          help='Create migrated VMs each UUID provided in a file, for example, ./id_file. ')
        parser.add_option("-z", "--createvolumes", action="store_true", dest='createvolumes',
                          help='Create and attach volumes for VMs that were migrated from each UUID provided in a file,'
                               ' for example, ./id_file. ')

        (opts, args) = parser.parse_args()
        main(opts, args)