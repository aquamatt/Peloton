# Copyright 2007 Matthew Pontefract
# See LICENSE for details

# The registry contains run-time configuration details.
# By default the keys, once set, cannot be modified
from peloton.utils.structs import ReadOnlyDict
registry = ReadOnlyDict()