#!/usr/bin/env python

import json
import argparse
from auth_stack2 import AuthStack
from solidfire.factory import ElementFactory


def get_solid_fire():
    auth = AuthStack()
    sf = ElementFactory.create(auth.solid_fire_ip, auth.solid_fire_user, auth.solid_fire_password)
    return sf


def get_volumes():
    sf = get_solid_fire()
    vls = sf.list_volumes_for_account()
    for vl in vls:
        print vl


def main():
    get_volumes()


if __name__== "__main__":
  main()


