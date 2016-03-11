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