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

import glance_common
import keystone_common
import nova_common
import solidfire_common
import utils
import re
from auth_stack2 import AuthStack

import time


def get_cinder(destination):

    auth = AuthStack()
    client = auth.get_cinder_client(destination)
    return client


def get_volume_list(destination):
    cinder = get_cinder(destination)
    volumes = cinder.volumes.list()
    # print volumes
    return volumes


def get_volume_list_by_vm_id(destination, vm_uuid):
    cinder = get_cinder(destination)
    volumes = cinder.volumes.list(search_opts={'metadata': {'original_vm_id': vm_uuid}})
    return volumes


def get_volume_by_id(destination, uuid):
    cinder = get_cinder(destination)
    volume = cinder.volumes.get(uuid)
    return volume


# volumes that are not attached to any VMs
def get_single_volumes(destination):
    volumes = get_volume_list(destination)
    singles = []
    for vol in volumes:
        if not vol.attachments:
            singles.append(vol)
    return singles


def get_volumes_from_vm_attachment_list(destination, attachments):
    volumes = []
    for att in attachments:
        vol = get_volume_by_id(destination, att['id'])
        volumes.append(vol)
    return volumes


def update_boot_status(destination, volumes):
    cinder = get_cinder(destination)
    for vol in volumes:
        bootable = False
        if vol.metadata['clone_boot_status'] == 'true':
            bootable = True
        cinder.volumes.set_bootable(vol, bootable)


def verify_to_vm_volumes(uuid, from_volumes):
    to_volumes = get_volume_list_by_vm_id("to", uuid)
    from_uuid = map(lambda from_volumes: from_volumes.id, from_volumes)
    to_original_uuid = map(lambda to_volumes: to_volumes.metadata['original_volume_id'], to_volumes)
    from_uuid.sort()
    to_original_uuid.sort()
    if from_uuid == to_original_uuid:
        print "Volume lists match!"
        update_boot_status("to", to_volumes)
        return to_volumes
    else:
        print "Volume lists dont match!"
        print "From volume IDs: "
        print from_uuid
        print "To volume IDs:"
        print to_original_uuid
        return []


def find_bootable_volume(to_volumes):
    for vol in to_volumes:
        og_device = vol.metadata['original_device']
        # root_disk_pattern = '/dev/.*da'
        #some volumes disk is only 'vda'
        root_disk_pattern = '.*da'
        first_vol_found = re.search(root_disk_pattern, og_device)
        print "vol.bootable", vol.bootable
        if vol.bootable == 'true' and first_vol_found:
            return vol
    print "No boot volume found."
    return None


def is_bootable_volume(destination, volume_id):
    vol = get_volume_by_id(destination, volume_id)
    if vol.bootable == 'true':
        return True
    return False


def compare_and_create_volumes():
    from_volumes = get_volume_list('from')
    to_volumes = get_volume_list('to')
    from_names = map(lambda from_volumes: from_volumes.name, from_volumes)
    to_names = map(lambda to_volumes: to_volumes.name, to_volumes)
    for volume in from_volumes:
        if volume.name not in to_names:
            create_volume('to', volume)
            #print volume.name
    #print from_names
    #print to_names


def create_volume_snapshot(destination, volume, original_vm_id="none"):
    cinder = get_cinder(destination)

    orig_name = ''
    if hasattr(volume, 'name'):
        orig_name = volume.name
    if hasattr(volume, 'display_name'):
        orig_name = volume.display_name

    name = "volume_snap_" + volume.id
    meta = {'original_vm_id': original_vm_id, 'original_volume_id': volume.id,
            'original_volume_name': orig_name,
            'bootable': volume.bootable}

    # Cinder version 1 has different parameter names from 2 and up.
    version = float(cinder.version)
    if version >= 2.0:
        snap = cinder.volume_snapshots.create(volume_id=volume.id, force=True, name=name,
                                              description="Migration snapshot", metadata=meta)
        print "Volume snapshot created: " + snap.name
    else:
        snap = cinder.volume_snapshots.create(volume_id=volume.id, force=True, display_name=name,
                                              display_description="Migration snapshot")
        cinder.volume_snapshots.set_metadata(snap, meta)
        print "Volume snapshot created: " + snap.display_name

    return snap


def create_volume(destination, volume):
    cinder = get_cinder(destination)
    from_tenant = volume.__dict__['os-vol-tenant-attr:tenant_id']
    tenant = keystone_common.find_opposite_tenant_id(from_tenant)

    if volume.volume_type == 'None':
        myvol = cinder.volumes.create(size=volume.size,
                                      snapshot_id=volume.snapshot_id,
                                      name=volume.name,
                                      description=volume.description,
                                      #volume_type=volume.volume_type,
                                      #user_id=volume.user_id, todo:fixthis
                                      project_id=tenant,
                                      availability_zone=volume.availability_zone,
                                      metadata=volume.metadata,
                                      #imageRef=volume.imageRef,
                                      source_volid=volume.source_volid
                                      )
    else:
        myvol = cinder.volumes.create(size=volume.size,
                                      snapshot_id=volume.snapshot_id,
                                      name=volume.name,
                                      description=volume.description,
                                      volume_type=volume.volume_type,
                                      #user_id=volume.user_id, todo:fixthis
                                      project_id=tenant,
                                      availability_zone=volume.availability_zone,
                                      metadata=volume.metadata,
                                      #imageRef=volume.imageRef,
                                      source_volid=volume.source_volid
                                      )
    print "Volume", myvol.name, "created"
    if volume.attachments:
        for att in volume.attachments:
            print att
            print att['server_id']
            device = att['device']
            print device

            vm = nova_common.get_vm_by_original_id('to', att['server_id'])
            if vm:
                #myvol.attach(vm.id, device)
                # Followed this advice: http://www.florentflament.com/blog/openstack-volume-in-use-although-vm-doesnt-exist.html
                nova = nova_common.get_nova(destination)
                nova.volumes.create_server_volume(vm.id, myvol.id, device)
                print "Volume", myvol.name, "attached to VM", vm.name
            else:
                print "Original Volume", volume.name, "was attached to a VM with ID", att['server_id'], \
                    "but this VM was not found in the current VM list"
    return myvol


def create_volume_from_image(destination, volume, single=False):
    cinder = get_cinder(destination)
    try:
        from_tenant = volume.__dict__['os-vol-tenant-attr:tenant_id']
        tenant = keystone_common.find_opposite_tenant_id(from_tenant)
    except Exception, e:
        tenant = None
    # user = keystone_common.find_opposite_user_id(volume.user_id)
    if single:
        image_name = "single_migration_volume_image_" + volume.id
    else:
        image_name = "migration_volume_image_" + volume.id
    image = glance_common.get_image_by_name('to', image_name)
    if image:
        meta = volume.metadata
        meta.update({'original_volume_id': volume.id})
        meta.update({'original_boot_status': volume.bootable})
        if volume.attachments:
            for att in volume.attachments:
                meta.update({'original_vm_id': att['server_id']})
                meta.update({'original_vm_device': att['device']})

        version = float(cinder.version)
        if version >= 2.0:
            if volume.volume_type == 'None':
                myvol = cinder.volumes.create(size=volume.size,
                                              snapshot_id=volume.snapshot_id,
                                              name=volume.name,
                                              description=volume.description,
                                              #volume_type=volume.volume_type,
                                              # user_id=user, #todo:fixthis
                                              project_id=tenant,
                                              metadata=meta,
                                              imageRef=image.id,
                                              source_volid=volume.source_volid
                                              )
            else:
                myvol = cinder.volumes.create(size=volume.size,
                                              snapshot_id=volume.snapshot_id,
                                              name=volume.name,
                                              description=volume.description,
                                              volume_type=volume.volume_type,
                                              project_id=tenant,
                                              metadata=meta,
                                              imageRef=image.id,
                                              source_volid=volume.source_volid
                                              )
        # Handle cinder v1:
        else:
            if volume.volume_type == 'None':
                myvol = cinder.volumes.create(size=volume.size,
                                              snapshot_id=volume.snapshot_id,
                                              display_name=volume.display_name,
                                              display_description=volume.display_description,
                                              #volume_type=volume.volume_type,
                                              # user_id=user, #todo:fixthis
                                              project_id=tenant,
                                              metadata=meta,
                                              imageRef=image.id,
                                              source_volid=volume.source_volid
                                              )
            else:
                myvol = cinder.volumes.create(size=volume.size,
                                              snapshot_id=volume.snapshot_id,
                                              display_name=volume.display_name,
                                              display_description=volume.display_description,
                                              volume_type=volume.volume_type,
                                              project_id=tenant,
                                              metadata=meta,
                                              imageRef=image.id,
                                              source_volid=volume.source_volid
                                              )
        bootable = False
        if volume.bootable == 'true':
            bootable = True # for some reason api returns a string and the next call expects a boolean.
        cinder.volumes.set_bootable(myvol, False)
        print "Volume", myvol.id, "created"
    else:
        print "Image", image_name, "for volume migration not found. Did you skip a step?"


def create_volume_from_image_by_vm_ids(id_file):
    ready = nova_common.check_vm_are_on('to', id_file)
    if ready:
        volume_ids = nova_common.get_volume_id_list_for_vm_ids('from', id_file)
        from_volumes = get_volume_list('from')
        for volume in from_volumes:
            if volume.id in volume_ids:
                create_volume_from_image('to', volume)
    else:
        print "All servers being migrated must be in ACTIVE status for this action to proceed."


def upload_volume_to_image_by_volume_id(destination, vol_id, single=False):
    cinder = get_cinder(destination)
    volume = cinder.volumes.get(vol_id)
    if single:
        image_name = "single_migration_volume_image_" + vol_id
    else:
        image_name = "migration_volume_image_" + vol_id
    print "image name: ", image_name
    cinder.volumes.upload_to_image(volume, force=True, image_name=image_name,
                                   container_format='bare', disk_format='raw')


def upload_volume_to_image_by_volume_name(destination, volume, name):
    cinder = get_cinder(destination)

    image_name = "migration_volume_image_" + name
    container_format = 'bare'
    disk_format = 'raw'
    if hasattr(volume, 'volume_image_metadata'):
        if volume.volume_image_metadata:
            container_format = volume.volume_image_metadata['container_format']
            disk_format = volume.volume_image_metadata['disk_format']

    cinder.volumes.upload_to_image(volume, force=True, image_name=image_name,
                                   container_format=container_format, disk_format=disk_format)
    print "Image " + image_name + " created from volume ID " + volume.id


def upload_single_volumes_to_image(destination, uuid_file):
    ids = utils.read_ids_from_file(uuid_file)

    # volumes = get_single_volumes(destination)
    for vol in ids:
        print "Creating image from volume, volume id:", vol
        upload_volume_to_image_by_volume_id(destination, vol, single=True)


def download_single_volumes(destination, path, id_file):
    volumes = utils.read_ids_from_file(id_file)
    # vols = get_single_volumes(destination)
    # volumes = map(lambda vols: vols.id, vols)
    glance_common.download_images_by_volume_uuid(destination, path, volumes, single=True)


def upload_single_volume_images_to_clouds(path, id_file):
    # vols = get_single_volumes('from')
    # volumes = map(lambda vols: vols.id, vols)
    volumes = utils.read_ids_from_file(id_file)
    glance_common.upload_volume_images(path, volumes)


def create_single_volumes_from_images(id_file):
    # vols = get_single_volumes('from')
    vols = utils.read_ids_from_file(id_file)
    for volume in vols:
        vol = get_volume_by_id('from', volume)
        create_volume_from_image('to', vol, single=True)


def create_volumes_from_images_by_vm_id(volumes):
    # vols = get_single_volumes('from')
    # vols = utils.read_ids_from_file(id_file)
    for volume in volumes:
        vol = get_volume_by_id('from', volume)
        create_volume_from_image('to', vol)


def print_volumes(destination):
    vols = get_volume_list(destination)
    vols.sort(key=lambda x: x.status)
    newlist = sorted(vols, key=lambda x: x.status)
    print "Volumes sorted by status (id status type size):"
    # print newlist
    for volume in vols:
        if hasattr(volume, 'display_name'):
            print volume.id, volume.status, volume.volume_type, volume.size, volume.display_name
        else:
            print volume.id, volume.status, volume.volume_type, volume.size, volume.name


def print_detail_volumes(destination):
    vols = get_volume_list(destination)
    vols.sort(key=lambda x: x.status)
    newlist = sorted(vols, key=lambda x: x.status)
    print "Volumes sorted by status (id status type size name host availability zone):"
    # print newlist
    for volume in vols:
        if hasattr(volume, "os-vol-host-attr:host"):
            host = getattr(volume, "os-vol-host-attr:host")
            if hasattr(volume, 'display_name'):
                print volume.id, volume.status, volume.volume_type, volume.size, volume.display_name, host, volume.availability_zone
            else:
                print volume.id, volume.status, volume.volume_type, volume.size, volume.name, host, volume.availability_zone
        else:
            host = 'no_host_info'
            print volume.id, volume.status, volume.volume_type, volume.size, volume.name, host, volume.availability_zone


def get_snapshot_by_volume_id(destination, volume_id):
    cinder = get_cinder(destination)
    name = "volume_snap_" + volume_id

    version = float(cinder.version)
    if version >= 2.0:
        snapshots = cinder.volume_snapshots.list(search_opts={'name': name})
    else:
        snapshots = cinder.volume_snapshots.list(search_opts={'display_name': name})
    if len(snapshots) > 1:
        latest = None
        datum = None
        for snap in snapshots:
            if datum < snap.updated_at:
                datum = snap.updated_at
                latest = snap
            print snap.updated_at
        print "Found latest snapshot for volume_id " + volume_id + " updated at " + latest.updated_at
        return latest
    elif len(snapshots) == 1:
        return snapshots[0]
    print "No matching snapshot found"
    return


def make_volume_from_snapshot(destination, volume_id, snapshot):
    cinder = get_cinder(destination)
    volume = get_volume_by_id(destination, volume_id)
    tenant = volume.__dict__['os-vol-tenant-attr:tenant_id']

    version = float(cinder.version)
    bootable = False
    if volume.bootable == 'true':
        bootable = True  # for some reason api returns a string and the next call expects a boolean.

    if version >= 2.0:
        print "Make volume from snapshot: snapshot id "
        print snapshot
        if hasattr(snapshot, 'metadata'):
            meta = snapshot.metadata
        else:
            meta = {}

        attachments = volume.attachments[0]
        if attachments:
            if attachments['device']:
                meta.update({'original_device': attachments['device']})

        if hasattr(snapshot, 'name'):
            snapshot_name = snapshot.name
        else:
            snapshot_name = ""
        if volume.volume_type == 'None':
            myvol = cinder.volumes.create(
                                          # size=volume.size,
                                          # snapshot_id=volume.snapshot_id,
                                          name=snapshot_name,
                                          description="Migration Volume",
                                          # volume_type=volume.volume_type,
                                          # user_id=volume.user_id, todo:fixthis
                                          project_id=tenant,
                                          availability_zone=volume.availability_zone,
                                          metadata=meta,
                                          source_volid=volume_id
                                          )
        else:
            myvol = cinder.volumes.create(size=volume.size,
                                          # snapshot_id=volume.snapshot_id,
                                          name=snapshot_name,
                                          description="Migration Volume",
                                          volume_type=volume.volume_type,
                                          # user_id=volume.user_id, todo:fixthis
                                          project_id=tenant,
                                          availability_zone=volume.availability_zone,
                                          metadata=meta,

                                          source_volid=volume_id
                                          )
        print "Volume", myvol.id, "created"
        cinder.volumes.set_bootable(myvol, bootable)
    # cinder v1:
    else:
        if hasattr(snapshot, 'metadata'):
            meta = snapshot.metadata
        else:
            meta = {}
        attachments = volume.attachments[0]
        if attachments:
            if attachments['device']:
                meta.update({'original_device': attachments['device']})
        if hasattr(snapshot, 'display_name'):
            snapshot_name = snapshot.display_name
        else:
            snapshot_name = ""
        if volume.volume_type == 'None':
            myvol = cinder.volumes.create(
                                          # size=volume.size,
                                          #snapshot_id=volume.snapshot_id,
                                          display_name=snapshot_name,
                                          display_description="Migration Volume",
                                          # volume_type=volume.volume_type,
                                          # user_id=volume.user_id, todo:fixthis
                                          project_id=tenant,
                                          availability_zone=volume.availability_zone,
                                          metadata=meta,
                                          # imageRef=volume.imageRef,
                                          source_volid=volume_id

                                          )
        else:
            myvol = cinder.volumes.create(size=volume.size,
                                          #snapshot_id=volume.snapshot_id,
                                          display_name=snapshot_name,
                                          display_description="Migration Volume",
                                          volume_type=volume.volume_type,
                                          # user_id=volume.user_id, todo:fixthis
                                          project_id=tenant,
                                          availability_zone=volume.availability_zone,
                                          metadata=meta,
                                          source_volid=volume_id
                                          )
        print "Volume", myvol.id, "created"
        try:
            print "Volume bootable status: ", bootable
            cinder.volumes.set_bootable(myvol, bootable)
        except Exception, e:
            print str(e)
            print "Old version of cinder is causing issues with setting volume bootable, boot status will be updated on the TO side."

    return myvol


def print_volume_types(destination):
    cinder = get_cinder(destination)
    types = cinder.volume_types.list()

    print "Volume Types:"
    for type in types:
        print type.name
    # print types


def get_volume_backups(destination):
    cinder = get_cinder(destination)
    backups = cinder.backups.list()
    return backups


def print_volume_backups(destination):
    backups = get_volume_backups(destination)
    print "Volume Backups (ID, volume id, name, size, status)"
    for backup in backups:
        print backup.id, backup.volume_id, backup.name, backup.size, backup.status


def get_cinder_pools(destination):
    cinder = get_cinder(destination)
    try:
        pools = cinder.pools.list()
        return pools
    except Exception, e:
        print "No pool info available"
        return []


def print_cinder_pools(destination):
    pools = get_cinder_pools(destination)
    for pool in pools:
        print pool.name


def change_volume_type(destination, volume, vtype):
    cinder = get_cinder(destination)
    # volume = get_volume_by_id(destination, volume_id)
    if hasattr(volume, 'volume_type'):
        if volume.volume_type == vtype:
            print "Volume " + volume.id + " already type " + vtype
            return
    cinder.volumes.retype(volume, vtype, "on-demand")
    print "Volume " + volume.id + " retyped to " + vtype


def retype_volumes_by_volume_ids(destination, volume_id_file, type):
    cinder = get_cinder(destination)
    volume_ids = utils.read_ids_from_file(volume_id_file)
    for volume in volume_ids:
        change_volume_type(destination, volume, type)


#cinder manage --name vol3 --volume-type lvm1 egle-pike-dns-1@lvm#LVM_iSCSI volume-e7c4df78-4dc4-4c62-ad88-3c846b901e78
def manage_volume(destination, reference, host, name, volume_type=None, bootable=False, metadata=None):
    cinder = get_cinder(destination)
    print "Will try to manage volume name " + name
    print "with reference "
    print reference
    cinder.volumes.manage(host, reference, name=name, volume_type=volume_type, bootable=bootable, metadata=metadata)
    print "Managed volume's name " + name


def manage_ssd(host, volume_name, solidfire_id):
    source = {'source-id': solidfire_id}
    manage_volume('to', host=host, reference=source, name=volume_name, volume_type='SSD')


def manage_volumes_by_vm_id(ssd_host, hdd_host, region, volume):
    # for volume in volumes:
    # vol = get_volume_by_id('from', volume)
    # vol = get_clone_volume_by_id('from', volume)
    manage_volume_from_id('to', region, ssd_host, hdd_host, volume)


def manage_volume_from_id(destination, region, ssd_host, hdd_host, volume):
    # cinder = get_cinder(destination)
    #todo: verify tenant/user info
    # try:
    #     from_tenant = volume.__dict__['os-vol-tenant-attr:tenant_id']
    #     tenant = keystone_common.find_opposite_tenant_id(from_tenant)
    # except Exception, e:
    #     print "No tenant ID found, setting tenant to None"
    #     tenant = None

    # manage_volume("to", )
    #reference, host, type, name, bootable=False, metadata=None
    meta = volume.metadata
    meta.update({'clone_volume_id': volume.id})
    original_cinder = get_cinder('from')
    version = float(original_cinder.version)
    if version >= 2.0:
        meta.update({'clone_volume_name': volume.name})
    else:
        meta.update({'clone_volume_name': volume.display_name})
    meta.update({'clone_boot_status': volume.bootable})
    print meta
    if volume.attachments:
        for att in volume.attachments:
            meta.update({'original_vm_id': att['server_id']})
            meta.update({'original_vm_device': att['device']})
    volume_type = volume.volume_type
    bootable = False
    # if volume.bootable == 'true':
    #     bootable = True  # for some reason api returns a string and the next call expects a boolean.

    # there is an issue with cinder v1 where volume set bootable didn't work, so using metadata instead.
    if meta['bootable'] == 'true':
        bootable = True

    #name = volume.name
    name = meta['original_volume_name']
    print "original name: " + name
    source = {}
    print "Volume type is:", volume_type
    if volume_type == 'SolidFire':
        sfid = solidfire_common.get_volume_by_volume_name(volume.id)
        ref = "%(id)s" % {"id": sfid}
        # source = {'source-id': ref}
        source = {'source-id': ref}
        host = ssd_host
    else:
        ref = 'volume-' + volume.id
        source = {'source-name': ref}
        host = hdd_host
    print "reference: "
    print source
    manage_volume(destination, source, host, name, volume_type=volume_type, bootable=bootable, metadata=meta)
    print "Volume id: " + volume.id + " managed!"


def print_manageable_volumes(destination, host):
    cinder = get_cinder(destination)
    mvs = cinder.volumes.list_manageable(host=host, detailed=True)
#{u'cinder_id': None, u'reason_not_safe': u'volume in use', u'reference': {u'source-name': u'cinder-volumes-pool'}, u'safe_to_manage': False, u'extra_info': None, u'size': 973}

    print '{:38}'.format("Cinder ID "), '{:45}'.format("Source name  "), "Safe to manage  Reason not safe    Size      Extra info"
    for mv in mvs:
        print  '{:38}'.format(mv._info['cinder_id']), '{:45}'.format(mv._info['reference']['source-name']), \
            mv._info['safe_to_manage'], "          ", \
            '{:17}'.format(mv._info['reason_not_safe']), '{:5}'.format(mv._info['size']), "    ", mv._info['extra_info']


def print_solid_fire_id(cinder_uuid):
    sfid = solidfire_common.get_volume_by_volume_name(cinder_uuid)
    print sfid


def main():
    # get_volume_list('from')
    # get_volume_list('to')
    #create_volume('from')
    #compare_and_create_volumes()
    #upload_volume_to_image_by_volume_id('from', 'cc6ff51b-faaf-443f-8835-a985611db39a')
    # print get_single_volumes('from')
    # upload_single_volumes_to_image('from')
    # download_single_volumes('from', './downloads/')
    # create_volume_from_image_by_vm_ids('./id_file')
    # print_volumes('from')
    # snaps = get_snapshot_by_volume_id("from", "15b70ee6-a4fe-4733-ba81-49bbd8abeced")
    # get_volume_list_by_vm_id("from", "91914190-dc7e-4fee-b5cf-a094abdc14c1")
    # get_cinder("from")
    # print_cinder_pools("to")
    # make_volume_from_snapshot("from", "ed1692f3-de70-4787-96b4-927c27deceb6", "b0730b31-9c82-4534-a4a3-5d739462dbbe ")
    # change_volume_type("to", 'f10073c4-3292-4585-b165-23174b0656f6', 'lvm1')
    # print_manageable_volumes("to", host='egle-pike-dns-1@lvm#LVM_iSCSI')
    # manage_volume("to", 'volume-886398cf-c9c0-40cc-bfd4-f5cf7a56d1ab', 'egle-pike-dns-1@lvm#LVM_iSCSI', 'foo', bootable=True)
    # get_volume_by_id('from', '15b70ee6-a4fe-4733-ba81-49bbd8abeced')
    retype_volumes_by_volume_ids('to', 'volume_ids', 'lvm1')


if __name__ == "__main__":
        main()
