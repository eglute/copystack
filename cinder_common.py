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


def get_cinder(destination):
        #TODO: fix this part...
    if destination == 'to':
        IDENTITY_IP = '172.16.56.129'
    else:
        IDENTITY_IP = '172.16.56.128'
    #CINDER_ENDPOINT = 'http://{ip}:8776'.format(ip=IDENTITY_IP)
    IDENTITY_ENDPOINT = 'http://{ip}:35357/v2.0'.format(ip=IDENTITY_IP)

    auth_ref = get_auth_ref(destination)
    keystone = get_keystone_client(destination, auth_ref, endpoint=IDENTITY_ENDPOINT,)
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

    status_ok()
    metric_bool('cinder_api_local_status', is_up)
    # only want to send other metrics if api is up
    if is_up:
        print "yay"


def main():
    get_cinder('from')
if __name__ == "__main__":
    with print_output():

        main()
