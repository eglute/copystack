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

import yaml
import math
# from os import listdir
# from os.path import isfile, join
import os
from glob import glob
from lxml import etree
from shutil import copy2
from multiprocessing import Process



def read_ids_from_file(id_file):
    with open(id_file, 'r') as fimage:
        list_ids = fimage.readlines()
        #print list_ids
    fimage.closed
    ids = []
    for i in list_ids:
        if i and i.strip():
            uuid = i.split()[0]
            #print uuid
            ids.append(uuid)
    return ids


def load(filename):
    """Load a dictionary from a yaml file.
    Expects the file at filename to be a yaml file.
    Returns the parsed configuration as a dictionary.
    :param filename: Name of the file
    :type filename: String
    :return: Loaded configuration
    :rtype: Dict
    """
    with open(filename, 'r') as f:
        return yaml.safe_load(f)


def get_nfs_location(dir, volume_id):
    # for f in listdir(dir):
    #     if isfile(join(dir, f)):
    #         print f
    #     else:
    # for root, d_names, f_names in os.walk(dir):
    #     print root, d_names, f_names
    fname = []
    for root, d_names, f_names in os.walk(dir):
        for f in f_names:
            if volume_id == f:
                #print os.path.join(root, f)
                # print root
                # print f
                return root



#will round up to the nearest gb:
#base 1024
def convert_B_to_GB(bytes):
    gig = math.pow(1024, 3)
    convert_gb = math.ceil(bytes / gig)
    return int(convert_gb)


# Get macs from libvirt file. Needed for proper nic ordering on boot.
def get_macs_from_libvirt(full_path):
    print "libvirt in: " + full_path
    tree = etree.parse(full_path + '/libvirt.xml')
    root = tree.getroot()
    interfaces = root.findall('./devices/interface/mac')
    macs = []
    for interface in interfaces:
        macs.append(interface.get('address'))
    # print macs
    return macs


def copy_file(full_path, file_name, new_name):
    print "Copying " + full_path + file_name + " to " + full_path + new_name
    copy2(full_path + file_name, full_path + new_name)


def start_copy_process(full_path, file_name, new_name):
    p = Process(target=copy_file, args=(full_path, file_name, new_name))
    p.start()