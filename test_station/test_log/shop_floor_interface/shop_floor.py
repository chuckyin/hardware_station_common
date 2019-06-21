__author__ = 'chuckyin'

#!/usr/bin/env python
# pylint: disable=R0921
# pylint: disable=F0401
# Mimic Generic Interface to Factory Shop Floor Systems

import importlib
FACEBOOK_IT_ENABLED = False
#import station_config


class ShopFloorError(Exception):
    pass


class ShopFloor(object):
    def __init__(self):
        pass

    def ok_to_test(self, serial_number):
        """
        Query Shop Floor System To Determine if a given Unit is Ok To Be Tested
        """
        return True

    def save_results(self, log):
        """
        Save Relevant Results from the Test Log to the Shop Floor System
        """
        return True