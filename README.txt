Quantum Migrate Tool
====================
Author: wallnerryan
	wallnerryan@gmail.com

Version 1.0
	-Supports Openstack Grizzly Release
	-Quantum Version 2.0

Controller Support
	-NVP v3.0 and v.3.2
	-(TODO) Floodlight
	-(TODO  OpenDaylight

DB Support? (this may not exist b/c backend may not matter)
	-MySQL (tested with)
	
Neutron Support-
	-not yet, b/c its needed for Grizz right now.
	-eventually yes, and a rename will be needed :)
	
Dependencies:
	-simplejson
	-docopt
	-
	-
	-
	-

This migrate tool came into fruition when I was constantly testing and messing with
openstack deployments with NVP. Sometimes, though misconfiguration or just some back luck
NVP nor Quantum could restore the state from quantum-db when they were "out-of-sync". Quantum would hold a 
bunch of logical switches, ports, routers etc and NVP would be either blank(new install) or
recovered and out of sync after failure. NOTE: NVP has tools, a support portal and procedures
to deal with this, but sometimes it just didnt work, meaning a manual re-addition of logical
components needs to happen. This is merely to re-add all logical state and UUIDs to the controller
of choice. I am leaving this modular so someone may "import <said-controller-api>" and use it
in much the same manner.

USAGE
====================

Probably best to clear any excess switches, routers etc that
pertain to the openstack deployment you are using, this will
pry the uuid's and logical state from quantum DB and call the controller
api to re-add them.

./migrate.py <controller-arch>
	e.g. " #migrate nvp"
