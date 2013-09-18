#!/usr/bin/python
"""
Fetch current logical state from Quantum/Nuetron Database.

"""
import logging

import quantumclient  #used to varify changes have taken place
from quantum.db.l3_db import L3_NAT_db_mixin 
from quantum.db.db_base_plugin_v2 import QuantumDbPluginV2
from quantum.openstack.common.context import RequestContext

LOG = logging.getLogger(__name__)

class RetrieveValues(QuantumDbPluginV2,L3_NAT_db_mixin):
    """
    Retrieve values from Quantum/Nuetron Database switches, subnets, ports
    @entities {switches,routers} or {switches,routers,ports} or {all}
    """
    
    def __init__(self, entities={"all"}):
        QuantumDbPluginV2.__init__(self)
        L3_NAT_db_mixin.__init__(self)
        self.entities = entities
        
    def _get_entities(self):
        return self.entities
    
    #TODO return queries in lists, bases on entities. 
    
    # Getting subnets, routers, ports should
    # be inherited from QuantumDBPluginV2 and L3 mixin.
    
    
    
        
    

