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

class ServiceLoader(object):
    def __init__(self, kernel):
        