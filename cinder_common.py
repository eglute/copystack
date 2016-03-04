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
import keystone_common
import requests
import collections


from requests import exceptions as exc

from maas_common import (get_keystone_client, get_auth_ref, get_cinder_client, status_err, status_ok,
                         metric_bool, print_output)


def get_cinder1(destination):
        #TODO: fix this part...
    if destination == 'to':
        IDENTITY_IP = '172.16.56.129'
    else:
        IDENTITY_IP = '172.16.56.128'
    #CINDER_ENDPOINT = 'http://{ip}:8776'.format(ip=IDENTITY_IP)
    IDENTITY_ENDPOINT = 'http://{ip}:35357/v2.0'.format(ip=IDENTITY_IP)

    auth_ref = get_auth_ref(destination)
    keystone = get_keystone_client(destination, auth_ref, endpoint=IDENTITY_ENDPOINT)
    auth_token = keystone.auth_token
    VOLUME_ENDPOINT = ('http://{ip}:8776/v1/{tenant}'.format
                       (ip=IDENTITY_IP, tenant=keystone.tenant_id))

    s = requests.Session()

    s.headers.update(
        {'Content-type': 'application/json',
         'x-auth-token': auth_token})

    try:
        vol = s.get('%s/volumes/detail' % VOLUME_ENDPOINT,
                    verify=False,
                    timeout=10)
        milliseconds = vol.elapsed.total_seconds() * 1000
        snap = s.get('%s/snapshots/detail' % VOLUME_ENDPOINT,
                     verify=False,
                     timeout=10)
        is_up = vol.ok and snap.ok

    except (exc.ConnectionError,
            exc.HTTPError,
            exc.Timeout) as e:
        is_up = False
    except Exception as e:
           status_err(str(e))
    else:
        # gather some metrics
        vol_statuses = [v['status'] for v in vol.json()['volumes']]
        vol_status_count = collections.Counter(vol_statuses)
        total_vols = len(vol.json()['volumes'])

        snap_statuses = [v['status'] for v in snap.json()['snapshots']]
        snap_status_count = collections.Counter(snap_statuses)
        total_snaps = len(snap.json()['snapshots'])

    # only want to send other metrics if api is up
    if is_up:
        print "yay"


#working version.... yippy. need to move it out to the other class
def get_cinder_old(destination):

    #TODO: fix this part...
    if destination == 'to':
        IDENTITY_IP = '172.16.56.129'
    else:
        IDENTITY_IP = '172.16.56.128'
    IDENTITY_ENDPOINT = 'http://{ip}:35357/v2.0'.format(ip=IDENTITY_IP)

    auth_ref = get_auth_ref(destination)
    keystone = get_keystone_client(destination, auth_ref, endpoint=IDENTITY_ENDPOINT)
    auth_token = keystone.auth_token
    VOLUME_ENDPOINT = ('http://{ip}:8776/v1/{tenant}'.format
                       (ip=IDENTITY_IP, tenant=keystone.tenant_id))


    user = 'myadmin'
    pr_id = 'MyProject'
    client = cinderclient.Client('1', user, auth_token,
                                 project_id=pr_id,
                                 auth_url=IDENTITY_ENDPOINT)
    client.client.auth_token = auth_token
    client.client.management_url = VOLUME_ENDPOINT

    l = client.volumes.list()
    print l
    return client


def get_cinder(destination):
        #TODO: fix this part...
    if destination == 'to':
        IDENTITY_IP = '172.16.56.129'
    else:
        IDENTITY_IP = '172.16.56.128'

    try:
        cinder = get_cinder_client(destination, identity_ip=IDENTITY_IP)
    except Exception as e:
        status_err(str(e))
    return cinder


def get_volume_list(destination):
    cinder = get_cinder(destination)
    volumes = cinder.volumes.list()
    #print volumes
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

    # myvol = cinder.volumes.create(size=volume.size,
    #                               consistencygroup_id=None,
    #                               snapshot_id=volume.snapshot_id,
    #                               source_volid=volume.source_volid,
    #                               name=volume.display_name,
    #                               description=volume.display_description,
    #                               volume_type=volume.volume_type,
    #                               user_id=None,
    #                               project_id=tenant,
    #                               availability_zone=volume.availability_zone,
    #                               metadata=volume.metadata,
    #                               imageRef=None,
    #                               scheduler_hints=None,
    #                               source_replica=None,
    #                               multiattach=False)


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
    return myvol

def main():
    #get_volume_list('from')
    #get_volume_list('to')
    #create_volume('from')
    compare_and_create_volumes()

if __name__ == "__main__":
    with print_output():

        main()
