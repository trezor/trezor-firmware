"""
The components/common module contains code that is used by both components/tt
and components/t1.
"""
from micropython import const

SWIPE_UP = const(0x01)
SWIPE_DOWN = const(0x02)
SWIPE_LEFT = const(0x04)
SWIPE_RIGHT = const(0x08)
