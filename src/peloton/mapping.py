# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

"""Mapping consists of the following core tasks, each represented by
a class in this module:

    - Loading: determining what PSCs should be asked to start a service, and
      getting them to do so (i.e. maps service to PSC).
      
    - Routing: Working out where a request should be sent to be satisfied, then
      sending it (ie maps request to psc.service). 
      
The RoutingTable is required by all.
"""

from twisted.internet import reactor

class ServiceLoader(object):
    """ The loader consults the routing table to find a set of PSCs 
that conform to a service profile's [psclimits]. Once a subset has been 
found that could run it, a number are chosen to conform to the profile's
[launch] configuration (ie n hosts, m PSCs etc).

The chosen PSCs are instructed to start the service; if a PSC refuses for
whatever reason then another is chosen. If there are  no suitable PSCs 
remaining the issue is logged and the request for the un-satisfied launches
is placed on a queue to be re-tried in some seconds.
"""

    def __init__(self, kernel):
        pass
    
    def launchService(self, serviceName):
        """ Start the process of launching a service which will require
the following steps:
    
    1. Locate the service and ensure  it exists
    2. Load the profile, extract the psclimits and launch parameters
    3. Search through routing table for all PSCs, filter on those that 
       match the psclimits for the service.
    3. Create a service launch request
    4. Request a suitable number of PSCs from the filtered batch
       to start the service.
    5. Any failures/refusals; select from 'spares' list
    6. If run out of PSCs before satisfying launch parameters, put
       the serivce launch request onto the stack for trying later.
 """
        pass
    
class ServiceLaunchRequest(object):
    """ State object used to keep track of a particular request to launch 
a service. As the loading is an asynchronous process it is easiest to track
by keeping all state in one object. """
    def __init__(self):
        pass