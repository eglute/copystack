#!/usr/bin/env python

import json
import argparse
import optparse
import keystone_common
import neutron_common
import nova_common
import maas_common

def main(opts, args):
    if(opts.report):
        from_tenants = keystone_common.get_from_tenant_list()
        print "=============== From Tenants: ======================"
        print from_tenants
        print "================ end From Tenants =================="
        to_tenants = keystone_common.get_to_tenant_list()
        print "=============== To Tenants: ========================"
        print to_tenants
        print "================ end To Tenants ===================="

        from_to_tenant = keystone_common.get_from_to_name_tenant_ids()
        print "================ Tenant ID mappings: ==============="
        print json.dumps(from_to_tenant, indent=4)

        from_networks = neutron_common.get_network_list('from')
        print "=============== From Networks: ======================"
        print from_networks
        print "=============== To Networks: ========================"
        to_networks = neutron_common.get_network_list('to')
        print "===============From Security Groups: ========================"
        from_sec = nova_common.get_security_groups('from')
        print from_sec
        print "===============To Security Groups: ========================"
        print nova_common.get_security_groups('to')
    if(opts.copynets):
        neutron_common.compare_and_create_networks()
    if(opts.copysec):
        nova_common.compare_and_create_security_groups()

if __name__ == "__main__":
        parser = optparse.OptionParser()
        #parser = argparse.ArgumentParser(description='Check Options')
        parser.add_option("-r", "--report", action='store_true', dest='report', help='Print Summary of Things')
        parser.add_option("-c", "--copynets", action="store_true", dest='copynets', help='Copy networks and subnets from->to')
        parser.add_option("-s", "--copysec", action="store_true", dest='copysec', help='Copy security groups from->to')
        (opts, args) = parser.parse_args()
        main(opts, args)