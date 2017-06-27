import yaml


def read_ids_from_file(id_file):
    with open(id_file, 'r') as fimage:
        list_ids = fimage.readlines()
        #print list_ids
    fimage.closed
    ids = []
    for i in list_ids:
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