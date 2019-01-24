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
from auth_stack2 import AuthStack
from solidfire.factory import ElementFactory


def get_solid_fire():
    auth = AuthStack()
    sf = ElementFactory.create(auth.solid_fire_ip, auth.solid_fire_user, auth.solid_fire_password, print_ascii_art=False)
    return sf


def get_volumes():
    sf = get_solid_fire()
    vls = sf.list_volumes()
    return vls


def get_volume_by_volume_name(name):
    vls = get_volumes()
    for vl in vls.volumes:
        if vl.name.endswith(name):
            print "Found SolidFire volume for Cinder ID " + name
            print "SolidFire volume name  %(name)s SolidFire volume ID: %(id)s" % {"name": vl.name, "id": vl.volume_id}
            return vl.volume_id
    print "No SolidFire volume found for Cinder ID " + name
    return None


def main():
    get_volume_by_volume_name('xxx81f16643-a50c-43bf-84e3-d67ba35cd222')


if __name__ == "__main__":
    main()