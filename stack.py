#!/usr/bin/env python

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

import json
import argparse
import optparse
import keystone_common
import neutron_common
import nova_common
import glance_common
import cinder_common
from auth_stack2 import AuthStack


def main(opts, args):
    auth = AuthStack()
    print "From:", auth.from_auth_ip, " Username:", auth.from_username, " Project:", auth.from_tenant_name
    print "To:  ", auth.to_auth_ip, " Username:", auth.to_username, " Project:", auth.to_tenant_name

    if opts.report:
        try:
            keystone_common.print_projects('from')
        except Exception, e:
            print "To print project info, switch to admin user"
        try:
            keystone_common.print_projects('to')
        except Exception, e:
            print "To print project info, switch to admin user"
        print "\n--------------- From Users: ---------------------"
        try:
            keystone_common.print_user_names('from')
        except Exception, e:
            print "To print user info, switch to admin user"
        print "\n--------------- To Users: ---------------------"
        try:
            keystone_common.print_user_names('to')
        except Exception, e:
            print "To print user info, switch to admin user"
        print "\n--------------- From Public Keys: ---------------------"
        try:
            nova_common.print_keys('from')
        except Exception, e:
            print "To print user info, switch to admin user"
        print "\n--------------- To Public Keys: ---------------------"
        try:
            nova_common.print_keys('to')
        except Exception, e:
            print "To print public keys, switch to admin user"
        # print "\n--------------- From Networks (with subnets): ---------------------"
        # neutron_common.print_network_list('from')
        # print "\n--------------- To Networks (with subnets): ------------------------"
        # neutron_common.print_network_list('to')
        # print "\n--------------- From Routers: ---------------------"
        # neutron_common.print_routers('from')
        # print "\n--------------- To Routers: ---------------------"
        # neutron_common.print_routers('to')
        print "\n--------------- From Security Groups: ------------------------"
        nova_common.print_security_groups('from')
        print "\n--------------- To Security Groups: ------------------------"
        nova_common.print_security_groups('to')
        print "\n--------------- From Images: ------------------------"
        glance_common.print_images('from')
        print "\n--------------- To Images: ------------------------"
        to_images = glance_common.get_images('to')
        glance_common.print_images('to')
        print "\n--------------- From Flavors: ------------------------"
        nova_common.print_flavor_list('from')
        print "\n--------------- To Flavors: ------------------------"
        nova_common.print_flavor_list('to')
        print "\n--------------- From VMs: ------------------------"
        vms = nova_common.print_vm_list_ids('from')
        print "\n--------------- To VMs: ------------------------"
        vms = nova_common.print_vm_list_ids('to')
        print "\n--------------- From Volumes: ------------------------"
        volumes = cinder_common.print_volumes('from')
        print "\n--------------- To Volumes: ------------------------"
        volumes = cinder_common.print_volumes('to')
    if opts.copynets:
        neutron_common.compare_and_create_networks()
    if opts.routers:
        neutron_common.compare_and_create_routers()
    if opts.copysec:
        nova_common.compare_and_create_security_groups()
    if opts.download:
        if len(args) == 2:
            print args[0]
            print args[1]
            ready = glance_common.download_images('from', path=args[0], uuid_file=args[1])
        else:
            print "Please provide download directory and file with image UUIDs to be downloaded, " \
                  "for example, ./downloads/ ./id_file"
    if opts.upload:
        if len(args) == 2:
            print args[0]
            print args[1]
            glance_common.create_images(path=args[0], uuid_file=args[1])
        else:
            print "Please provide download directory and file with image UUIDs to be uploaded, " \
                  "for example, ./downloads/ ./id_file"
    if opts.flavors:
        nova_common.compare_and_create_flavors()
    #todo: fix this
    if opts.singlevolumeimagecreate:
        if args:
            # print args[0]
            cinder_common.upload_single_volumes_to_image('from', uuid_file=args[0])
        else:
            print "Please provide file with volume UUIDs, for example, ./id_volume_file"
    if opts.quota:
        nova_common.compare_and_report_quotas()
    if opts.projects:
        print keystone_common.print_projects('from')
        print keystone_common.print_projects('to')
    if opts.createprojects:
        keystone_common.compare_and_create_projects()
    if opts.publickeys:
        nova_common.compare_and_create_keypairs()
    if opts.users:
        if args:
            keystone_common.compare_and_create_users_by_project(password = args[0])
        else:
            keystone_common.compare_and_create_users_by_project()
    if opts.shutdown:
        if args:
            # print args[0]
            nova_common.power_off_vms('from', id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be shutdown, for example, ./id_file"
    """
    if opts.createimages:
        if args:
            # print args[0]
            nova_common.create_image_from_vm('from', id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be shutdown, for example, ./id_file"
    
    if opts.downloadbyvmid:
        if len(args) == 2:
            print args[0]
            print args[1]
            ready = glance_common.download_images_by_vm_uuid('from', path=args[0], uuid_file=args[1])
            # if ready:
                #TODO: update volume part
                # volumes = nova_common.get_volume_id_list_for_vm_ids('from', id_file=args[1])
                # glance_common.download_images_by_volume_uuid('from', path=args[0], volumes=volumes)
        else:
            print "Please provide download directory and file with VM UUIDs to be downloaded, " \
                  "for example, ./downloads/ ./id_file"
    if opts.uploadbyvmid:
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

    if opts.migratevmscustomnet:
        if not args:
            print "Please provide args, ./id_file demo-net"
        elif len(args) == 2:
            print args[0]
            print args[1]
            nova_common.migrate_vms_from_image_with_network_mapping(id_file=args[0], custom_network=args[1])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    """
    if opts.bootvmsfromvolumescustomnet:
        if not args:
            print "Please provide args, ./id_file demo-net"
        elif len(args) >= 2:
            print args[0]
            print args[1]
            key = "default"
            if len(args) == 3:
                key = args[2]

            nova_common.boot_from_volume_vms_from_image_with_network_mapping(id_file=args[0], custom_network=args[1], key=key)
        else:
            print "Please provide file with VM UUIDs to be migrated, network to attach them to, and optional key, " \
                  "for example, ./id_file demo-net public-key"
    if opts.securitygroups:
        if args:
            print args[0]
            nova_common.attach_security_groups(id_file=args[0])
        else:
            print "Please provide file with VM UUIDs being migrated, for example, ./id_file"
    # if opts.createvolumes:
    #     if args:
    #         cinder_common.create_volume_from_image_by_vm_ids(id_file=args[0])
    #     else:
    #         print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    if opts.singlevolumeimagedownload:
        if len(args) == 2:
            cinder_common.download_single_volumes('from', path=args[0], id_file=args[1])
        else:
            print "Please provide image directory and file with volume ids, for example, ./downloads/ ./id_volume_file"
    if opts.singlevolumeimageupload:
        if len(args) == 2:
            cinder_common.upload_single_volume_images_to_clouds(path=args[0], id_file=args[1])
        else:
            print "Please provide image directory and file with volume ids for example, ./downloads/ ./id_volume_file"
    if opts.singlevolumecreate:
        if args:
            cinder_common.create_single_volumes_from_images(id_file=args[0])
        else:
            print "Please provide file with volume ids, for example, ./id_volume_file"
    if opts.addmissinginterfaces:
        neutron_common.compare_and_create_ports()
    if opts.reportvms:
        if args:
            if len(args) == 1:
                print "\n--------------- " + args[0] + " VMs: ------------------------"
                dest = args[0].strip().lower()
                vms = nova_common.print_vm_list_ids(args[0])
        else:
            print "\n--------------- From VMs: ------------------------"
            vms = nova_common.print_vm_list_ids('from')
            print "\n--------------- To VMs: ------------------------"
            vms = nova_common.print_vm_list_ids('to')
    if opts.createsnapshotvm:
        if args:
            print args[0]
            nova_common.prepare_migrate_vms_from_image_snapshot(id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    if opts.createsvolumefromsnapshot:
        if args:
            print args[0]
            nova_common.make_volumes_from_snapshots("from", id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    if opts.createsimagesfromvolumesnapshots:
        if args:
            print args[0]
            nova_common.make_images_of_volumes_based_on_vms("from", id_file=args[0])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    if opts.downloadbyvmidsnapshot:
        if len(args) == 2:
            print args[0]
            nova_common.download_images_of_volumes_based_on_vms("from", path=args[0], id_file=args[1])
        else:
            print "Please provide image directory and file with VM ids, for example, ./downloads/ ./id_file"
    if opts.uploadimagebyvmidsnapshot:
        if len(args) == 2:
            print args[0]
            glance_common.upload_volume_images_by_vm_uuid(path=args[0], id_file=args[1])
        else:
            print "Please provide image directory and file with VM ids, for example, ./downloads/ ./id_file"
    if opts.volumefromimage:
        if len(args) == 1:
            print args[0]
            nova_common.create_volumes_from_images_based_on_vms(id_file=args[0])
        else:
            print "Please provide file with VM ids, for example, ./id_file"
    if opts.adddvolumestovms:
        if len(args) == 1:
            print args[0]
            nova_common.attach_volumes(id_file=args[0])
        else:
            print "Please provide file with VM ids, for example, ./id_file"


if __name__ == "__main__":

        parser = optparse.OptionParser()
        parser.add_option("-t", "--projects", action='store_true', dest='projects',
                          help='Run this command as Admin. Print to and from projects. Project names must match before '
                               'running the rest of copystack')
        parser.add_option("-x", "--createprojects", action='store_true', dest='createprojects',
                          help='Run this command as Admin. Create projects from->to.'
                               'Project names must match before running the rest of copystack')
        parser.add_option("-u", "--users", action='store_true', dest='users',
                          help='Run this command as Admin. Create users from->to. Password is optional parameter. '
                               'If password is not included, users created without a password.')
        parser.add_option("-q", "--quota", action='store_true', dest='quota',
                          help='Run this command as Admin. Print differences in individual quotas for each project')
        parser.add_option("-f", "--flavors", action='store_true', dest='flavors',
                          help='Run this command as Admin. Copy flavors from -> to')
        parser.add_option("-c", "--copynets", action="store_true", dest='copynets',
                          help='Run this command as Admin. Copy networks and subnets from->to')
        parser.add_option("-w", "--routers", action="store_true", dest='routers',
                          help='Run this command as Admin. Copy routers from->to')
        parser.add_option("-W", "--addmissinginterfaces", action="store_true", dest='addmissinginterfaces',
                          help='Run this command as Admin. Add missing interfaces between routers and networks and '
                               'additional ports. '
                               'It will skip duplicates, but will print an exception that it did so. If ports created'
                               'in error, delete them from OpenStack command line with "neutron port-delete" command.')
        parser.add_option("-s", "--copysec", action="store_true", dest='copysec',
                          help='Copy security groups from -> to')
        parser.add_option("-p", "--publickeys", action='store_true', dest='publickeys',
                          help='Copy public keys from -> to')
        parser.add_option("-d", "--download", action="store_true", dest='download',
                          help='Download all non-migration images to a specified path, for example, ./downloads/.'
                          'for each UUID provided in a file, for example, ./id_file. '
                          'First argument directory path, second path to a file. '
                          ' Images with names that start with "migration_vm_image_" or "migration_volume_image_" '
                               'will not be moved. All others will be.')
        parser.add_option("-l", "--upload", action="store_true", dest='upload',
                          help='Recreate all non-migration images in a new environment. Provide a path, '
                               'for example, ./downloads/ where images from "-d" where stored. '
                               'Will not check for duplicate image names, since duplicate names are allowed.'
                          ' Images with names that start with "migration_vm_image_" or "migration_volume_image_" '
                               'will not be moved. All others will be.')

        parser.add_option("-r", "--report", action='store_true', dest='report', help='Print Summary of Things')
        parser.add_option("-0", "--shutdown", action="store_true", dest='shutdown',
                          help='Shutdown VMs for each UUID provided in a file, for example, ./id_file')
        ####### VMs from volume snapshots
        parser.add_option("-1", "--createsnapshotvm", action="store_true", dest='createsnapshotvm',
                          help='Create snapshots from VMs Cinder volumes for each UUID provided in a file, '
                               'for example, ./id_file. ')
        parser.add_option("-2", "--createsvolumefromsnapshot", action="store_true", dest='createsvolumefromsnapshot',
                          help='Create volumes from snapshots based on associated VM for each VM UUID provided in a file, '
                               'for example, ./id_file. ')
        parser.add_option("-3", "--createsimagesfromvolumesnapshots", action="store_true",
                          dest='createsimagesfromvolumesnapshots',
                          help='Create images from volumes based on snapshots based on associated VM for each VM UUID provided in a file, '
                               'for example, ./id_file. ')
        parser.add_option("-4", "--downloadbyvmidsnapshot", action="store_true", dest='downloadbyvmidsnapshot',
                          help='First argument directory path, second path to a file. '
                               'Download all images by VM UUID to a specified path, for example, ./downloads/ '
                               'for each UUID provided in a file, for example, ./id_file.')
        parser.add_option("-5", "--uploadimagebyvmidsnapshot", action="store_true", dest='uploadimagebyvmidsnapshot',
                          help='First argument directory path, second path to a file. '
                               'Upload all images by VM UUID from a specified path, for example, ./downloads/ '
                               'for each UUID provided in a file, for example, ./id_file. ')
        parser.add_option("-6", "--volumefromimage", action="store_true", dest='volumefromimage',
                          help='First argument path to a file with original VM IDs. '
                               'Upload all images by VM UUID from a specified path, for example, ./downloads/ '
                               'for each UUID provided in a file, for example, ./id_file. ')
        parser.add_option("-7", "--bootvmsfromvolumescustomnet", action="store_true",
                          dest='bootvmsfromvolumescustomnet',
                          help='Boot migrated VMs from volumes for each VM UUID provided in a file, for example, ./id_file. '
                               'on a custom network. Floating IPs will not be created. Provide network name or ID,'
                               'for example, "demo-net and optional public key name "key-name" '
                               ' Sample: -7 ./id_file demo-net key-name')
        parser.add_option("-8", "--adddvolumestovms", action="store_true", dest='adddvolumestovms',
                          help='Attach additional volumes to migrated VMs for each UUID provided in the original '
                               'migration file, for example, ./id_file.')

        # standalone vms without volumes attached. commenting out for cleaner --help
        """ 
        parser.add_option("-i", "--createimages", action="store_true", dest='createimages',
                          help='Create images from VMs for each UUID provided in a file, for example, ./id_file. '
                               'Volumes attached to VMs will also be their images created.')
        parser.add_option("-o", "--downloadbyvmid", action="store_true", dest='downloadbyvmid',
                          help='First argument directory path, second path to a file. '
                               'Download all images by VM UUID to a specified path, for example, ./downloads/ '
                               'for each UUID provided in a file, for example, ./id_file. '
                               'Volumes associated with the VMs will not be downloaded.')
        parser.add_option("-k", "--uploadbyvmid", action="store_true", dest='uploadbyvmid',
                          help='First argument directory path, second path to a file. '
                               'Upload all images by VM UUID from a specified path, for example, ./downloads/ '
                               'for each UUID provided in a file, for example, ./id_file. '
                               'Volumes associated with the VMs will not be uploaded.')
        parser.add_option("-g", "--migratevms", action="store_true", dest='migratevms',
                          help='Create migrated VMs each UUID provided in a file, for example, ./id_file. ')
        parser.add_option("-G", "--migratevmscustomnet", action="store_true", dest='migratevmscustomnet',
                          help='Create migrated VMs each UUID provided in a file, for example, ./id_file. '
                               'on a custom network. Floating IPs will not be created. Provide network name or ID,'
                               'for example, "demo-net. '
                               ' Sample: -G ./id_file demo-net')
        """

        parser.add_option("-9", "--securitygroups", action="store_true", dest='securitygroups',
                          help='Attach security groups to migrated VMs for each UUID provided in the original '
                               'migration file, for example, ./id_file. ')
        # parser.add_option("-z", "--createvmvolumes", action="store_true", dest='createvolumes',
        #                   help='Create and attach volumes for VMs that were migrated from each UUID provided in a file,'
        #                        ' for example, ./id_file. ')
        parser.add_option("-v", "--singlevolumeimagecreate", action='store_true', dest='singlevolumeimagecreate',
                          help='Create images of unattached volumes for each UUID provided in the ./id_volume_file')
        parser.add_option("-V", "--singlevolumeimagedownload", action='store_true', dest='singlevolumeimagedownload',
                          help='Download images of unattached volumes as specified in volume ID file'
                               'to a specified path, for example, ./downloads/ ./id_volume_file')
        parser.add_option("-y", "--singlevolumeimageupload", action='store_true', dest='singlevolumeimageupload',
                          help='Upload images of unattached volumes from '
                               'a specified path as specified in volume ID file, for example, '
                               './downloads/ ./id_volume_file')
        parser.add_option("-Y", "--singlevolumecreate", action='store_true', dest='singlevolumecreate',
                          help='Create un-attached volumes from images as specified in volume ID file, '
                               'for example, ./id_volume_file')
        parser.add_option("-R", "--reportvms", action='store_true', dest='reportvms',
                          help='Print only VM report. Specify "from" or "to". Not specifying will print '
                               'for both environments.')



        (opts, args) = parser.parse_args()
        main(opts, args)
