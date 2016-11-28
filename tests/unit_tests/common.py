from __future__ import print_function

import sys
sys.path = ['../../'] + sys.path

from trezorlib import tx_api

tx_api.cache_dir = '../txcache'
