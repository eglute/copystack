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
from auth_stack import AuthStack
import time


def get_cinder(destination):

    auth = AuthStack()
    client = auth.get_cinder_client(destination)
    return client


def get_volume_list(destination):
    cinder = get_cinder(destination)
    volumes = cinder.volumes.list()
    print volumes
    return volumes


def compare_and_create_volumes():
    from_volumes = get_volume_list('from')
    to_volumes = get_volume_list('to')
    from_names = map(lambda from_volumes: from_volumes.display_name, from_volumes)
    to_names = map(lambda to_volumes: to_volumes.display_name, to_volumes)
    for volume in from_volumes:
        if volume.display_name not in to_names:
            create_volume('to', volume)
            #print volume.display_name
    #print from_names
    #print to_names


def create_volume(destination, volume):
    cinder = get_cinder(destination)
    from_tenant = volume.__dict__['os-vol-tenant-attr:tenant_id']
    tenant = keystone_common.find_opposite_tenant_id(from_tenant)

    if volume.volume_type == 'None':
        myvol = cinder.volumes.create(size=volume.size,
                                      snapshot_id=volume.snapshot_id,
                                      display_name=volume.display_name,
                                      display_description=volume.display_description,
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
                                      display_name=volume.display_name,
                                      display_description=volume.display_description,
                                      volume_type=volume.volume_type,
                                      #user_id=volume.user_id, todo:fixthis
                                      project_id=tenant,
                                      availability_zone=volume.availability_zone,
                                      metadata=volume.metadata,
                                      #imageRef=volume.imageRef,
                                      source_volid=volume.source_volid
                                      )
    print "Volume", myvol.display_name, "created"
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
                print "Volume", myvol.display_name, "attached to VM", vm.name
            else:
                print "Original Volume", volume.display_name, "was attached to a VM with ID", att['server_id'], \
                    "but this VM was not found in the current VM list"
    return myvol


def create_volume_from_image(destination, volume):
    cinder = get_cinder(destination)
    from_tenant = volume.__dict__['os-vol-tenant-attr:tenant_id']
    tenant = keystone_common.find_opposite_tenant_id(from_tenant)
    # user = keystone_common.find_opposite_user_id(volume.user_id)
    image_name = "migration_volume_image_" + volume.id
    image = glance_common.get_image_by_name('to', image_name)
    if volume.volume_type == 'None':
        myvol = cinder.volumes.create(size=volume.size,
                                      snapshot_id=volume.snapshot_id,
                                      display_name=volume.display_name,
                                      display_description=volume.display_description,
                                      #volume_type=volume.volume_type,
                                      # user_id=user, #todo:fixthis
                                      project_id=tenant,
                                      availability_zone=volume.availability_zone,
                                      metadata=volume.metadata,
                                      imageRef=image.id,
                                      source_volid=volume.source_volid
                                      )
    else:
        myvol = cinder.volumes.create(size=volume.size,
                                      snapshot_id=volume.snapshot_id,
                                      display_name=volume.display_name,
                                      display_description=volume.display_description,
                                      volume_type=volume.volume_type,
                                      # user_id=user, #todo:fixthis
                                      project_id=tenant,
                                      availability_zone=volume.availability_zone,
                                      metadata=volume.metadata,
                                      imageRef=image.id,
                                      source_volid=volume.source_volid
                                      )
    print "Volume", myvol.display_name, "created"
    #todo: wait for status to attach
    status = myvol.status
    while True:
        vol = cinder.volumes.get(myvol.id)
        status = vol.status
        print "Volume current status:", status
        if status != 'available':
            print "sleeping... waiting for available status"
            time.sleep(5)
        else:
            break

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
                print "Volume", myvol.display_name, "attached to VM", vm.name
            else:
                print "Original Volume", volume.display_name, "was attached to a VM with ID", att['server_id'], \
                    "but this VM was not found in the current VM list"
    return myvol


def create_volume_from_image_by_vm_ids(id_file):
    volume_ids = nova_common.get_volume_id_list_for_vm_ids('from', id_file)
    from_volumes = get_volume_list('from')
    # to_volumes = get_volume_list('to')
    # from_names = map(lambda from_volumes: from_volumes.display_name, from_volumes)
    # to_names = map(lambda to_volumes: to_volumes.display_name, to_volumes)
    for volume in from_volumes:
        if volume.id in volume_ids:
            create_volume_from_image('to', volume)
            #print volume.display_name
    #print from_names
    #print to_names


def upload_volume_to_image_by_volume_id(destination, vol_id):
    cinder = get_cinder(destination)
    volume = cinder.volumes.get(vol_id)
    image_name = "migration_volume_image_" + vol_id
    cinder.volumes.upload_to_image(volume, force=True, image_name=image_name,
                                   container_format='bare', disk_format='raw')


def main():
    get_volume_list('from')
    #get_volume_list('to')
    #create_volume('from')
    #compare_and_create_volumes()
    #upload_volume_to_image_by_volume_id('from', '5ce8ff78-87a7-465e-b455-8850adeb70fa')

if __name__ == "__main__":
        main()
