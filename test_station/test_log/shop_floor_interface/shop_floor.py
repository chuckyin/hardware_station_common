__author__ = 'chuckyin'

#!/usr/bin/env python
# pylint: disable=R0921
# pylint: disable=F0401
# Mimic Generic Interface to Factory Shop Floor Systems

import importlib
FACEBOOK_IT_ENABLED = False
import station_config
import os


class ShopFloorError(Exception):
    pass


class ShopFloor(object):
    _floor = False
    def __init__(self):
        if station_config.FACEBOOK_IT_ENABLED:
            if not( (hasattr(station_config, 'SHOP_FLOOR_DBG') and station_config.SHOP_FLOOR_DBG)
                      or (not ShopFloor._floor) ):
                return
            py = None
            try:
                config_path = os.path.join(os.getcwd(), '..\\shop_floor_interface')
                if os.path.exists(__file__):
                    config_path = os.path.join(os.getcwd(), 'shop_floor_interface')
                py = os.path.join(config_path, 'shop_floor_{0}.py'.format(station_config.SHOPFLOOR_SYSTEM))
                if os.path.exists(py):
                    exec(open(py, 'rb').read(), globals())
                    init_load = globals().get('initialize')
                    if init_load is not None:
                        init_load(station_config)
                    ShopFloor._floor = True
                else:
                    print(f'Unable to find shop_floor_interface: {py}\n')
            except Exception as e:
                print('Fail to initialised shop_floor: {0}, {1}'.format(station_config.SHOPFLOOR_SYSTEM, py))
                ShopFloor._floor = False


    def ok_to_test(self, serial_number):
        """
        Query Shop Floor System To Determine if a given Unit is Ok To Be Tested
        """
        if not station_config.FACEBOOK_IT_ENABLED:
            return True
        if not ShopFloor._floor:
            return False
        ok_to_test =  globals().get('ok_to_test')
        return ok_to_test(serial_number) if ok_to_test is not None else False

    def save_results(self, log):
        """
        Save Relevant Results from the Test Log to the Shop Floor System
        """
        if not station_config.FACEBOOK_IT_ENABLED:
            return True
        if not ShopFloor._floor:
            return False
        save_results = globals().get('save_results')
        return save_results(log) if save_results is not None else False