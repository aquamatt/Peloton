##############################################################################
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved.
#
# This software  is licensed under the terms of the BSD license, a copy of
# which should accompany this distribution.
#
##############################################################################


# The registry contains run-time configuration details.
# By default the keys, once set, cannot be modified
from peloton.utils.structs import ReadOnlyDict
registry = ReadOnlyDict()