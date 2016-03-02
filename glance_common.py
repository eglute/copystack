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

import argparse
import collections
import sys
import os
import six.moves.urllib.parse as urlparse
from ipaddr import IPv4Address
import keystone_common
from maas_common import (status_ok, status_err, get_keystone_client, get_glance_client, get_auth_ref, print_output)
from requests import Session
from requests import exceptions as exc


IMAGE_STATUSES = ['active', 'queued', 'killed']


def check(destination, auth_ref):
    # We call get_keystone_client here as there is some logic within to get a
    # new token if previous one is bad.
         #TODO: fix this part...
    if destination == 'to':
        IDENTITY_IP = '172.16.56.129'
    else:
        IDENTITY_IP = '172.16.56.128'
    IDENTITY_ENDPOINT = 'http://{ip}:35357/v2.0'.format(ip=IDENTITY_IP)

    keystone = get_keystone_client(destination, auth_ref, endpoint=IDENTITY_ENDPOINT)
    auth_token = keystone.auth_token
    api_endpoint = 'http://{ip}:9292/v1'.format(ip=IDENTITY_IP)

    s = Session()

    s.headers.update(
        {'Content-type': 'application/json',
         'x-auth-token': auth_token})

    try:
        # Hit something that isn't querying the glance-registry, since we
        # query glance-registry in separate checks
        r = s.get('%s/' % api_endpoint, verify=False,
                  timeout=10)
        milliseconds = r.elapsed.total_seconds() * 1000
        is_up = r.ok
    except (exc.ConnectionError, exc.HTTPError, exc.Timeout):
        is_up = False
    except Exception as e:
        status_err(str(e))
    else:
        # gather some metrics to report
        try:
            r = s.get('%s/images/detail' % api_endpoint, verify=False,
                      timeout=10)
        except Exception as e:
            status_err(str(e))
        else:
            image_statuses = [i['status'] for i in r.json()['images']]
            print image_statuses


def get_glance(destination):
   #TODO: fix this part...
    if destination == 'to':
        IDENTITY_IP = '172.16.56.129'
    else:
        IDENTITY_IP = '172.16.56.128'
    NETWORK_ENDPOINT = 'http://{ip}:9292'.format(ip=IDENTITY_IP)

    try:
        glance = get_glance_client(destination, endpoint=NETWORK_ENDPOINT)
        return glance
    except Exception as e:
        print "ugh"
        print e.details
    return 'meh'


def get_images(destination):
    glance = get_glance(destination)
    images = glance.images.list()
    return images


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
def create_images(path):
    from_images = get_images('from')
    for i in from_images:
        if (i.status == 'active') and (i.deleted == False):
            filename = path + i.id
            image_create('to', i, filename)


def download_images(destination, path):
    if os.access(os.path.dirname(path), os.W_OK):
        images = get_images(destination)
        for i in images:
            if (i.status == 'active') and (i.deleted == False):
                image_download(i.id, path)
            else:
                print "Image with this id is not available for downloads: " + i.id
    else:
        print "Invalid directory provided"


def image_create(destination, image, url):
    glance = get_glance(destination)
    props = image.properties

    tenant = keystone_common.find_opposite_tenant_id(image.owner)
    #insert original image id into the properties:
    props.update({'original_image_id': image.id})
    with open(url, 'r') as fimage:
        img = glance.images.create(data=fimage,
                                   name=image.name,
                                   container_format=image.container_format,
                                   disk_format=image.disk_format,
                                   owner=tenant,
                                   size=image.size,
                                   min_ram=image.min_ram,
                                   min_disk=image.min_disk,
                                   properties=image.properties,
                                   is_public=image.is_public,
                                   protected=image.protected
                                   )
        print img
    fimage.closed


def image_download(id, path):
    glance = get_glance('from')
    fname = path + id
    data = glance.images.data(id)
    print "Downloading " + fname
    save_image(data, fname)


def save_image(data, path):
    """Save an image to the specified path.
    :param data: binary data of the image
    :param path: path to save the image to
    """
    image = open(path, 'wb')
    try:
        for chunk in data:
            image.write(chunk)
    finally:
        if path is not None:
            image.close()

def main():
    #auth_ref = get_auth_ref('from')
    #check('from', auth_ref)
    #download_images('from')
    #image_create()
    #image_download()
    #create_images("./downloads/")
    #get_image_id_by_original_id('to', '64737c30-b1fe-4a93-a14d-259395f61364')
    print "foo"

if __name__ == "__main__":
        main()
