# $Id$
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details

RELEASE_VERSION = 0.0.1

# The registry contains run-time configuration details.
# By default the keys, once set, cannot be modified
from peloton.utils.structs import ReadOnlyDict
registry = ReadOnlyDict()