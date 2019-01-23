import yaml
import math
# from os import listdir
# from os.path import isfile, join
import os
from glob import glob

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



#will round UP to the nearest GB:
#base 1024
def convert_B_to_GB(bytes):
    gig = math.pow(1024, 3)
    convert_gb = math.ceil(bytes / gig)
    return int(convert_gb)