#!/usr/bin/env python

import json
import argparse
import keystone_common
import neutron_common
import nova_common
import glance_common
import cinder_common
from auth_stack2 import AuthStack


# auth = AuthStack()
# parser = argparse.ArgumentParser(description='Welcome to Copystack, your OpenStack migration helper')
# print "From:", auth.from_auth_ip, " Username:", auth.from_username, " Project:", auth.from_tenant_name
# print "To:  ", auth.to_auth_ip, " Username:", auth.to_username, " Project:", auth.to_tenant_name


def add_cinder_command_options(subparsers):
    cinder_parser = subparsers.add_parser('cinder', help='Run cinder reports.')

    cinder_parser.add_argument("-r", "--report", action='store_true', dest='report', help='Print FROM volumes with details')
    cinder_parser.add_argument("-R", "--Report", action='store_true', dest='Report', help='Print TO volumes with details')
    cinder_parser.add_argument("-t", "--types", action='store_true', dest='types', help='Print available volume types')
    cinder_parser.add_argument("-b", "--backups", action='store_true', dest='backups', help='Print volume backups')
    cinder_parser.add_argument("-p", "--pools", action='store_true', dest='pools', help='Print volume pools')
    cinder_parser.add_argument("-m", "--manage", nargs=1, metavar='host name', dest='manage', help='Print FROM manageable volumes. '
                                                                                 'Please provide host name, similar to sample-aio-liberty-2@lvm#LVM_iSCSI')
    cinder_parser.add_argument("-M", "--Manage", nargs=1, metavar='host name', dest='Manage', help='Print TO manageable volumes. '
                                                                                 'Please provide host name, similar to sample-aio-liberty-2@lvm#LVM_iSCSI')


def cinder_actions(args):
    if args.report:
        print "\n--------------- From Volumes: ------------------------"
        volumes = cinder_common.print_detail_volumes('from')
    if args.Report:
        print "\n--------------- To Volumes: ------------------------"
        volumes = cinder_common.print_detail_volumes('to')
    if args.types:
        print "\n--------------- From Volume Types: ------------------------"
        cinder_common.print_volume_types('from')
        print "\n--------------- To Volume Types: ------------------------"
        cinder_common.print_volume_types('to')
    if args.backups:
        print "\n--------------- From Volume Backups: ------------------------"
        cinder_common.print_volume_backups('from')
        print "\n--------------- To Volume Backups: ------------------------"
        cinder_common.print_volume_backups('to')
    if args.pools:
        print "\n--------------- From Volume Pools: ------------------------"
        cinder_common.print_cinder_pools('from')
        print "\n--------------- To Volume Pools: ------------------------"
        cinder_common.print_cinder_pools('to')
    if args.Manage:
        if len(args.Manage) == 1:
            print "\n--------------- To Manageable Volumes: ------------------------"
            cinder_common.print_manageable_volumes('to', host=args.Manage[0])
        else:
            print "Please provide host name, similar to sample-aio-liberty-2@lvm#LVM_iSCSI"
    if args.manage:
        if args:
            print "\n--------------- From Volume Pools: ------------------------"
            if len(args.manage) == 1:
                print args.manage[0]
            cinder_common.print_manageable_volumes('from', host=args.manage[0])
        else:
            print "Please provide host name, similar to sample-aio-liberty-2@lvm#LVM_iSCSI"


def add_keystone_command_options(subparsers):
    keystone_parser = subparsers.add_parser('keystone', help='Run keystone reports.')

    keystone_parser.add_argument("-f", "--fromusers", action='store_true', dest='fromusers', help='Print FROM users')
    keystone_parser.add_argument("-t", "--tousers", action='store_true', dest='tousers', help='Print TO users')
    keystone_parser.add_argument("-p", "--fromprojects", action='store_true', dest='fromprojects',
                      help='Print FROM projects (or tenants)')
    keystone_parser.add_argument("-r", "--toprojects", action='store_true', dest='toprojects',
                      help='Print TO projects (or tenants)')


def keystone_actions(args):
    if args.fromusers:
        print "\n--------------- From Users: ------------------------"
        keystone_common.print_user_names('from')
    if args.tousers:
        print "\n--------------- To Users: ------------------------"
        keystone_common.print_user_names('to')
    if args.fromprojects:
        keystone_common.print_projects('from')
    if args.toprojects:
        keystone_common.print_projects('to')


def add_nova_command_options(subparsers):
    nova_parser = subparsers.add_parser('nova', help='Run nova reports')
    nova_parser.add_argument("-s", "--from_sec", action='store_true', dest='from_sec', help='Print FROM security groups')
    nova_parser.add_argument("-S", "--to_sec", action='store_true', dest='to_sec', help='Print TO security groups')
    nova_parser.add_argument("-f", "--from_flavor", action='store_true', dest='from_flavor', help='Print FROM flavors')
    nova_parser.add_argument("-F", "--to_flavor", action='store_true', dest='to_flavor', help='Print TO flavors')
    nova_parser.add_argument("-v", "--from_vms", action='store_true', dest='from_vms', help='Print FROM vms')
    nova_parser.add_argument("-V", "--to_vms", action='store_true', dest='to_vms', help='Print TO vms')


def nova_actions(args):
    if args.from_sec:
        print "\n--------------- From Security Groups: ------------------------"
        nova_common.print_security_groups('from')
    if args.to_sec:
        print "\n--------------- To Security Groups: ------------------------"
        nova_common.print_security_groups('to')
    if args.from_flavor:
        print "\n--------------- From Flavors: ------------------------"
        nova_common.print_flavor_list('from')
    if args.to_flavor:
        print "\n--------------- To Flavors: ------------------------"
        nova_common.print_flavor_list('to')
    if args.from_vms:
        print "\n--------------- From VMs: ------------------------"
        vms = nova_common.print_vm_list_ids('from')
    if args.to_vms:
        print "\n--------------- To VMs: ------------------------"
        vms = nova_common.print_vm_list_ids('to')


def add_neutron_command_options(subparsers):
    neutron_parser = subparsers.add_parser('neutron', help='Run neutron reports')
    neutron_parser.add_argument("-n", "--nets", action='store_true', dest='nets', help='Print FROM networks')
    neutron_parser.add_argument("-N", "--Nets", action='store_true', dest='Nets', help='Print TO networks')
    neutron_parser.add_argument("-r", "--routers", action='store_true', dest='routers', help='Print FROM routers')
    neutron_parser.add_argument("-R", "--Routers", action='store_true', dest='Routers', help='Print TO routers')


def neutron_actions(args):
    if args.nets:
        print "\n--------------- From Networks (with subnets): ---------------------"
        neutron_common.print_network_list('from')
    if args.Nets:
        print "\n--------------- To Networks (with subnets): ------------------------"
        neutron_common.print_network_list('to')
    if args.routers:
        print "\n--------------- From Routers: ---------------------"
        neutron_common.print_routers('from')
    if args.Routers:
        print "\n--------------- To Routers: ---------------------"
        neutron_common.print_routers('to')


def add_migrate_command_options(subparsers):
    migrate_parser = subparsers.add_parser('migrate', help='Migration actions')
    migrate_parser.add_argument("-0", "--shutdown", dest='shutdown', nargs=1, metavar='UUID_file',
                      help='Shutdown VMs for each UUID provided in a file, for example, ./id_file')
    migrate_parser.add_argument("-1", "--createsnapshotvm", dest='createsnapshotvm', nargs=1, metavar='UUID_file',
                      help='Create snapshots from VMs Cinder volumes for each UUID provided in a file, '
                           'for example, ./id_file. ')
    migrate_parser.add_argument("-2", "--createsvolumefromsnapshot", dest='createsvolumefromsnapshot', nargs=1, metavar='UUID_file',
                      help='Create volumes from snapshots based on associated VM for each VM UUID provided in a file, '
                           'for example, ./id_file. ')
    migrate_parser.add_argument("-3", "--createsimagesfromvolumesnapshots", nargs=1, metavar='UUID_file',
                      dest='createsimagesfromvolumesnapshots',
                      help='Create images from volumes based on snapshots based on associated VM for each VM UUID provided in a file, '
                           'for example, ./id_file. ')
    migrate_parser.add_argument("-4", "--downloadbyvmidsnapshot", dest='downloadbyvmidsnapshot',
                      nargs=2, metavar=('path', 'UUID_file'),
                      help='First argument directory path, second path to a file. '
                           'Download all images by VM UUID to a specified path, for example, ./downloads/ '
                           'for each UUID provided in a file, for example, ./id_file.')
    migrate_parser.add_argument("-5", "--uploadimagebyvmidsnapshot",  dest='uploadimagebyvmidsnapshot',
                      nargs=2, metavar=('path', 'UUID_file'),
                      help='First argument directory path, second path to a file. '
                           'Upload all images by VM UUID from a specified path, for example, ./downloads/ '
                           'for each UUID provided in a file, for example, ./id_file. ')
    migrate_parser.add_argument("-6", "--volumefromimage", dest='volumefromimage',
                      nargs=2, metavar=('path', 'UUID_file'),
                      help='First argument path to a file with original VM IDs. '
                           'Upload all images by VM UUID from a specified path, for example, ./downloads/ '
                           'for each UUID provided in a file, for example, ./id_file. ')
    migrate_parser.add_argument("-7", "--bootvmsfromvolumescustomnet",
                      nargs=3, metavar=('UUID_file', 'network', 'public_key'),
                      dest='bootvmsfromvolumescustomnet',
                      help='Boot migrated VMs from volumes for each VM UUID provided in a file, for example, ./id_file. '
                           'on a custom network. Floating IPs will not be created. Provide network name or ID,'
                           'for example, "demo-net and optional public key name "key-name" '
                           ' Sample: -7 ./id_file demo-net key-name')
    migrate_parser.add_argument("-8", "--adddvolumestovms",  dest='adddvolumestovms',
                      nargs=1, metavar='UUID_file',
                      help='Attach additional volumes to migrated VMs for each UUID provided in the original '
                           'migration file, for example, ./id_file.')


def migrate_actions(args):
    if args.shutdown:
        if len(args.shutdown) == 1:
            nova_common.power_off_vms('from', id_file=args.shutdown[0])
        else:
            print "Please provide file with VM UUIDs to be shutdown, for example, ./id_file"
    if args.createsnapshotvm:
        if args.createsnapshotvm:
            nova_common.prepare_migrate_vms_from_image_snapshot(id_file=args.createsnapshotvm[0])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    if args.createsvolumefromsnapshot:
        if len(args.createsvolumefromsnapshot) == 1:
            nova_common.make_volumes_from_snapshots("from", id_file=args.createsvolumefromsnapshot[0])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    if args.createsimagesfromvolumesnapshots:
        if len(args.createsimagesfromvolumesnapshots) == 1:
            nova_common.make_images_of_volumes_based_on_vms("from", id_file=args.createsimagesfromvolumesnapshots[0])
        else:
            print "Please provide file with VM UUIDs to be migrated, for example, ./id_file"
    if args.downloadbyvmidsnapshot:
        if len(args.downloadbyvmidsnapshot) == 2:
            nova_common.download_images_of_volumes_based_on_vms("from", path=args.downloadbyvmidsnapshot[0], id_file=args.downloadbyvmidsnapshot[1])
        else:
            print "Please provide image directory and file with VM ids, for example, ./downloads/ ./id_file"
    if args.uploadimagebyvmidsnapshot:
        if len(args.uploadimagebyvmidsnapshot) == 2:
            glance_common.upload_volume_images_by_vm_uuid(path=args.uploadimagebyvmidsnapshot[0], id_file=args.uploadimagebyvmidsnapshot[1])
        else:
            print "Please provide image directory and file with VM ids, for example, ./downloads/ ./id_file"
    if args.volumefromimage:
        if len(args.volumefromimage) == 1:
            nova_common.create_volumes_from_images_based_on_vms(id_file=args.volumefromimage[0])
        else:
            print "Please provide file with VM ids, for example, ./id_file"
    if args.adddvolumestovms:
        if len(args.adddvolumestovms) == 1:
            nova_common.attach_volumes(id_file=args.adddvolumestovms[0])
        else:
            print "Please provide file with VM ids, for example, ./id_file"


def main():
    auth = AuthStack()
    print "From:", auth.from_auth_ip, " Username:", auth.from_username, " Project:", auth.from_tenant_name
    print "To:  ", auth.to_auth_ip, " Username:", auth.to_username, " Project:", auth.to_tenant_name

    parser = argparse.ArgumentParser(description="Welcome to Copystack, your OpenStack migration helper!")
    subparsers = parser.add_subparsers(help='Program mode', dest='mode')
    subparsers.add_parser('cinder')
    subparsers.add_parser('keystone')
    subparsers.add_parser('nova')
    subparsers.add_parser('migrate')

    add_cinder_command_options(subparsers)
    add_keystone_command_options(subparsers)
    add_nova_command_options(subparsers)
    add_neutron_command_options(subparsers)
    add_migrate_command_options(subparsers)

    args = parser.parse_args()
    # print args
    if args.mode == 'cinder':
        cinder_actions(args)
    elif args.mode == 'keystone':
        keystone_actions(args)
    elif args.mode == 'nova':
        nova_actions(args)
    elif args.mode == 'neutron':
        neutron_actions(args)
    elif args.mode == 'migrate':
        migrate_actions(args)
    else:
        parser.print_usage()


if __name__== "__main__":
  main()

