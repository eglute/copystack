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
import utils
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
        if vol.metadata['original_boot_status'] == 'true':
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


def find_bootable_volume(volumes):
    for vol in volumes:
        if vol.bootable == 'true':
            return vol

    return None


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
    name = "volume_snap_" + volume.id
    # if volume.bootable == "true":
    # if hasattr(volume, 'bootable'):
    meta = {'original_vm_id': original_vm_id, 'original_volume_id': volume.id, 'bootable': volume.bootable}
    # else:
    #     meta = {'original_vm_id': original_vm_id, 'original_volume_id': volume.id}
    snap = cinder.volume_snapshots.create(volume_id=volume.id, force=True, name=name, description="Migration snapshot", metadata=meta)
    print "Volume snapshot created: " + snap.name
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
        if volume.volume_type == 'None':
            myvol = cinder.volumes.create(size=volume.size,
                                          snapshot_id=volume.snapshot_id,
                                          # name=volume.name,
                                          # description=volume.description,
                                          #volume_type=volume.volume_type,
                                          # user_id=user, #todo:fixthis
                                          project_id=tenant,
                                          # availability_zone=volume.availability_zone,
                                          metadata=meta,
                                          imageRef=image.id,
                                          source_volid=volume.source_volid
                                          )
        else:
            myvol = cinder.volumes.create(size=volume.size,
                                          snapshot_id=volume.snapshot_id,
                                          # name=volume.name,
                                          # description=volume.description,
                                          # volume_type=volume.volume_type,
                                          # user_id=user, #todo:fixthis
                                          project_id=tenant,
                                          # availability_zone=volume.availability_zone,
                                          metadata=meta,
                                          imageRef=image.id,
                                          source_volid=volume.source_volid
                                          )
        bootable = False
        if volume.bootable == 'true':
            bootable = True # for some reason api returns a string and the next call expects a boolean.
        cinder.volumes.set_bootable(myvol, False)
        print "Volume", myvol.name, "created"
        #todo: wait for status to attach
        status = myvol.status
#todo: fix this. right now, there is error related to this bug in AIO being tested, error 3 described here: https://bugs.launchpad.net/tripleo/+bug/1638350
        """
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
        """
    else:
        print "Image", image_name, "for volume migration not found. Did you skip a step?"


def create_volume_from_image_by_vm_ids(id_file):
    ready = nova_common.check_vm_are_on('to', id_file)
    if ready:
        volume_ids = nova_common.get_volume_id_list_for_vm_ids('from', id_file)
        from_volumes = get_volume_list('from')
        # to_volumes = get_volume_list('to')
        # from_names = map(lambda from_volumes: from_volumes.name, from_volumes)
        # to_names = map(lambda to_volumes: to_volumes.name, to_volumes)
        for volume in from_volumes:
            if volume.id in volume_ids:
                create_volume_from_image('to', volume)
                #print volume.name
        #print from_names
        #print to_names
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


def upload_volume_to_image_by_volume_name(destination, vol_id, name):
    cinder = get_cinder(destination)
    volume = cinder.volumes.get(vol_id)
    image_name = "migration_volume_image_" + name
    print "image name: ", image_name
    cinder.volumes.upload_to_image(volume, force=True, image_name=image_name,
                                   container_format='bare', disk_format='raw')


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
    print "Volumes sorted by status (id name status size):"
    # print newlist
    for volume in vols:
        print volume.id, volume.name, volume.status, volume.size


def get_snapshot_by_volume_id(destination, volume_id):
    cinder = get_cinder(destination)
    name = "volume_snap_" + volume_id
    snapshots = cinder.volume_snapshots.list(search_opts={'name': name})
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
    # tenant = keystone_common.find_opposite_tenant_id(from_tenant)

    if volume.volume_type == 'None':
        myvol = cinder.volumes.create(
                                      # size=volume.size,
                                      snapshot_id=volume.snapshot_id,
                                      name=snapshot.name,
                                      description="Migration Volume",
                                      # volume_type=volume.volume_type,
                                      # user_id=volume.user_id, todo:fixthis
                                      project_id=tenant,
                                      availability_zone=volume.availability_zone,
                                      metadata=snapshot.metadata,
                                      # imageRef=volume.imageRef,
                                      source_volid=volume.source_volid
                                      )
    else:
        myvol = cinder.volumes.create(size=volume.size,
                                      snapshot_id=volume.snapshot_id,
                                      name=snapshot.name,
                                      description="Migration Volume",
                                      volume_type=volume.volume_type,
                                      # user_id=volume.user_id, todo:fixthis
                                      project_id=tenant,
                                      availability_zone=volume.availability_zone,
                                      metadata=snapshot.metadata,
                                      # imageRef=volume.imageRef,
                                      source_volid=volume.source_volid
                                      )
    print "Volume", myvol.id, "created"
    # if volume.attachments:
    #     for att in volume.attachments:
    #         print att
    #         print att['server_id']
    #         device = att['device']
    #         print device
    #
    #         vm = nova_common.get_vm_by_original_id('to', att['server_id'])
    #         if vm:
    #             # myvol.attach(vm.id, device)
    #             # Followed this advice: http://www.florentflament.com/blog/openstack-volume-in-use-although-vm-doesnt-exist.html
    #             nova = nova_common.get_nova(destination)
    #             nova.volumes.create_server_volume(vm.id, myvol.id, device)
    #             print "Volume", myvol.name, "attached to VM", vm.name
    #         else:
    #             print "Original Volume", volume.name, "was attached to a VM with ID", att['server_id'], \
    #                 "but this VM was not found in the current VM list"
    return myvol


def main():
    # get_volume_list('from')
    #get_volume_list('to')
    #create_volume('from')
    #compare_and_create_volumes()
    # upload_volume_to_image_by_volume_id('from', '2fbe79d6-e2d6-4fda-80a8-11d75d3504a0')
    # print get_single_volumes('from')
    # upload_single_volumes_to_image('from')
    # download_single_volumes('from', './downloads/')
    # create_volume_from_image_by_vm_ids('./id_file')
    # print_volumes('from')
    # snaps = get_snapshot_by_volume_id("from", "15b70ee6-a4fe-4733-ba81-49bbd8abeced")
    get_volume_list_by_vm_id("from", "91914190-dc7e-4fee-b5cf-a094abdc14c1")

if __name__ == "__main__":
        main()
