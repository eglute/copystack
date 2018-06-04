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

import os
import keystone_common
import nova_common
import utils
from auth_stack2 import AuthStack


def get_glance(destination):
    auth = AuthStack()
    client = auth.get_glance_client(destination)
    return client


def get_image(destination, uuid):
    glance = get_glance(destination)
    image = glance.images.get(uuid)
    return image


def get_images(destination):
    glance = get_glance(destination)
    images = glance.images.list()
    return images


def get_image_by_name(destination, name):
    images = get_images(destination)
    print "looking for inamge name: " + name
    for img in images:
        if img.name == name:
            print "Found image name " + name
            return img


# Find image id by pre-migration image id
def get_image_by_original_id(destination, original_id):
    images = get_images(destination)
    for img in images:
        if img.properties:
            if 'original_image_id' in img.properties:
                original_image_id = img.properties['original_image_id']
                if original_image_id == original_id:
                    return img
    return None


# Create all images found, since name uniqueness in images is not guaranteed...
def create_images(path, uuid_file):
    ids = utils.read_ids_from_file(uuid_file)
    for uuid in ids:
        filename = path + uuid
        image = get_image('from', uuid)
        if image.status == 'active':
            print "Uploading image name:", image.name
            image_create('to', image, filename)


def download_images(destination, path, uuid_file):
    ids = utils.read_ids_from_file(uuid_file)

    if os.access(os.path.dirname(path), os.W_OK):
        for uuid in ids:
            i = get_image(destination, uuid=uuid)
            if i.name.startswith('migration_vm_image_') or i.name.startswith('migration_volume_image_'):
                continue
            else:
                if i.status == 'active':
                    image_download(i.id, path)
                else:
                    print "Image with this id is not available for downloads: " + i.id
    else:
        print "Invalid directory provided"


def download_image_by_uuid(destination, path, uuid):
    if os.access(os.path.dirname(path), os.W_OK):
        i = get_image(destination, uuid=uuid)
        if i.status == 'active':
            image_download(i.id, path)
        else:
            print "Image with this id is not available for downloads: " + i.id
    else:
        print "Invalid directory provided"


def download_images_by_vm_uuid(destination, path, uuid_file):
    ids = utils.read_ids_from_file(uuid_file)
    ready = True
    for uuid in ids:
        image_name = "migration_vm_image_" + uuid
        image = get_image_by_name(destination, image_name)
        if image.status != "active":
            print "Image", image.name, "is not in active status. All migration images must be active before proceeding"
            ready = False
            return ready
    for uuid in ids:
        image_name = "migration_vm_image_" + uuid
        print "Downloading image name:", image_name
        image = get_image_by_name(destination, image_name)
        image_download(image.id, path, fname=image_name)
    return ready


def download_images_by_volume_uuid(destination, path, volumes, single=False):
    for uuid in volumes:
        if single:
            image_name = "single_migration_volume_image_" + uuid
        else:
            image_name = "migration_volume_image_" + uuid
        print "Downloading image name:", image_name
        image = get_image_by_name(destination, image_name)
        if image:
            if image.status == 'active':
                image_download(image.id, path, fname=image_name)
            else:
                print "WARNING: Image", image_name, "must be in active status to proceed. Please update and try again!"
        else:
            print "No image ", image_name, "found."


def upload_images_by_vm_uuid(path, uuid_file):
    ids = utils.read_ids_from_file(uuid_file)

    for uuid in ids:
        image_name = "migration_vm_image_" + uuid
        filename = path + image_name
        image = get_image_by_name('from', image_name)
        print "Uploading image name:", image_name
        image_create('to', image, filename)

    #todo: update volume stuff
    # volume_ids = nova_common.get_volume_id_list_for_vm_ids('from', './id_file')
    # for volume_id in volume_ids:
    #     image_name = "migration_volume_image_" + volume_id
    #     filename = path + image_name
    #     image = get_image_by_name('from', image_name)
    #     print "Uploading image name:", image_name
    #     image_create('to', image, filename)


def upload_volume_images(path, volumes):
    for vol in volumes:
        image_name = "single_migration_volume_image_" + vol
        filename = path + image_name
        image = get_image_by_name('from', image_name)
        print "Uploading image name:", image_name
        image_create('to', image, filename)


def image_create(destination, image, url):
    glance = get_glance(destination)
    # props = image.properties

    # tenant = keystone_common.find_opposite_tenant_id(image.owner)
    #insert original image id into the properties:
    props = {'original_image_id': image.id}
    # props.update({'original_image_id': image.id})
    min_disk = 0
    if image.min_disk is not None:
        min_disk = image.min_disk
    min_ram = 0
    if image.min_ram is not None:
        min_ram = image.min_ram
    print "this might take a while..."
    img = glance.images.create(name=image.name,
                                   container_format=image.container_format,
                                   disk_format=image.disk_format,
                                   min_ram=min_ram,
                                   min_disk=min_disk,
                                   # properties=props,
                                   visibility=image.visibility,
                                   protected=image.protected)
    glance.image_tags.update(img.id, props)
    print url
    glance.images.upload(img.id, open(url, 'rb'))

    # with open(url, 'r') as fimage:
    #     img = glance.images.create(data=fimage,
    #                                name=image.name,
    #                                container_format=image.container_format,
    #                                disk_format=image.disk_format,
    #                                # owner=tenant,
    #                                size=image.size,
    #                                min_ram=min_ram,
    #                                min_disk=min_disk,
    #                                #properties=image.properties, #dont want to copy all the properties, as they cause lots of unpleasant issues
    #                                properties=props,
    #                                visibility=image.visibility,
    #                                protected=image.protected
    #                                )
    #     print img
    # fimage.closed


def image_download(id, path, fname='default'):
    glance = get_glance('from')
    if fname == 'default':
        fname = path + id
    else:
        fname = path + fname
        print "Fname: "+ fname
    data = glance.images.data(id)
    print "Downloading to " + fname
    save_image(data, fname)


def save_image(data, path):
    """Save an image to the specified path.
    :param data: binary data of the image
    :param path: path to save the image to
    """
    print "Path: " + path
    image = open(path, 'wb')
    print "this might take a while..."
    try:
        for chunk in data:
            image.write(chunk)
    finally:
        if path is not None:
            image.close()


def print_images(destination):
    fi = get_images(destination)
    from_images = sorted(fi, key=lambda x: x.name)

    print "Image UUID / Image Status / Image Name"
    for i in from_images:
        print i.id, " ", i.status, " ", i.name


def main():
    #auth_ref = get_auth_ref('from')
    #check('from', auth_ref)
    # download_images('from', './downloads/')
    #image_create()
    #image_download()
    #create_images("./downloads/")
    #get_image_by_original_id('to', '64737c30-b1fe-4a93-a14d-259395f61364')

    # from_images = get_images('from')
    # print "Image UUID / Image Status / Image Name"
    # for i in from_images:
    #     print i.id, " ", i.status, " ", i.name
    #print get_images('to')
    #download_images_by_vm_uuid('from', './downloads/', 'id_file')
    #upload_images_by_vm_uuid('./downloads/', 'id_file')
   # get_image_by_name('to', 'migration_vm_image_fbe348eb-ac32-46f3-b44d-c9477837266e')

    # volumes = nova_common.get_volume_id_list_for_vm_ids('from', './id_file')
    # download_images_by_volume_uuid('from','./downloads/', volumes=volumes)
    download_image_by_uuid('from', '/downloads', 'dd752ad4-6a97-41fe-b996-1231a6ded587')
if __name__ == "__main__":
        main()
