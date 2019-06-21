__author__ = 'chuckyin'

# pylint: disable=R0923
# pylint: disable=R0921

import factory_test_common.utils as utils

class DUT(object):
    """
        abstract base class for DUT

        Properties:
        unit --> an instance of the class uutType+'_DUT' for product specific implementation
        serialNumber --> the serial number of the unit

    """

    def __init__(self, serial_number, station_config, operator_interface):
        self._operator_interface = operator_interface
        self.serial_number = serial_number
        self._station_config = station_config

    def initialize(self):
        raise NotImplementedError()

    def systemtime(self):
        return utils.io_utils.systemtime()

    def close(self):
        raise NotImplementedError()
