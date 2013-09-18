#!/usr/bin/python
"""
migrate.py  --version=1.0

Migrate is a script that incorporates network controller APIs, usually REST
based API calls are made to sync "out-of-sync" quantum database logical state
back to a network controller and or newly integrated controller

@author wallnerryan
@email  wallnerryan@gmail.com

Usage:
  migrate <cntlr> [--migrate=<cmpnt> --connected=<is_conn>]
  migrate -h | --help
  migrate --version

Options:
  -h --help             Show this screen.
  --version             Show version.
  --migrate=<cmpnt>     Logical component you want to migrate. [default: all].
  --connected=<is_conn> Is the controller connected to Openstack (Quantum/Nuetron)? [default: True].

"""

from docopt import docopt
if __name__ == '__main__':
    args = docopt(__doc__, version='Quantum Migrate 1.0')
    
    #Testing
    print args['<cntlr>']
    print args['--migrate']
    print args['--connected']
