Copystack is a utility that can print a report of two OpenStack environments (environment A and environment B) and duplicate assets from one environment to the next. Assets like usernames and projects will be re-created with same names from environment A to environment B. Passwords will not be copied from A to B. VMs, images, and volumes will be downloaded from A to a location where copystack is running and uploaded from copystack to environment B. Each step in copystack must be run separately, since some steps take a very long time.

It is highly recommended to run copystack in a VM with a large disk size if you are planning on migrating large VMs, images, or volumes.

For information on copystack setup and usage please refer to the wiki: https://github.com/eglute/copystack/wiki
