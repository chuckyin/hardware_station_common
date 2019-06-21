__author__ = 'chuckyin'

#!/usr/bin/env python
# pylint: disable=R0921
# pylint: disable=F0401
# Mimic Generic Interface to Factory Shop Floor Systems

import importlib
import station_config


class ShopFloorError(Exception):
    pass


class ShopFloor(object):
    def __init__(self):
        """
        dynamically load the correct shop floor system based
        on the station_config
        """
        if station_config.FACEBOOK_IT_ENABLED:
            shopfloortype = station_config.SHOPFLOOR_SYSTEM
            self._shopfloor_module_name = '.shop_floor_' + shopfloortype.lower()
            try:
                module_string = 'factory_test_common.test_station.test_log.shop_floor_interface'
                self.shopfloor_module = importlib.import_module("%s" % self._shopfloor_module_name,
                                                                module_string)
            except:
                raise ShopFloorError("Unable To Import %s" % self._shopfloor_module_name)
            self._shop_floor_class_name = shopfloortype + 'ShopFloor'
            try:
                self.this_shop_floor = getattr(self.shopfloor_module, self._shop_floor_class_name)
            except AttributeError:
                raise ShopFloorError('function not found "%s"' % self._shop_floor_class_name)
            try:
                self._shop_floor = self.this_shop_floor()
            except:
                raise ShopFloorError('Unable To Instantiate %s' % self._shop_floor_class_name)
        else:
            pass

    def ok_to_test(self, serial_number):
        """
        Query Shop Floor System To Determine if a given Unit is Ok To Be Tested
        """
        if station_config.FACEBOOK_IT_ENABLED is True:
            return self._shop_floor.ok_to_test(serial_number)
        else:
            return True

    def save_results(self, log):
        """
        Save Relevant Results from the Test Log to the Shop Floor System
        """
        if not station_config.FACEBOOK_IT_ENABLED:
            pass
        else:
            return self._shop_floor.save_results(log)
