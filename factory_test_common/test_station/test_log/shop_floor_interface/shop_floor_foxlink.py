# pylint: disable = W0403

__author__ = 'chuckyin'

# pylint: disable=W0403
# Mimic Another factory, say Foxlink shopfloor interface


import foxlink_logfile_interface


class FoxlinkShopFloor(object):
    """
    Class to contain the shop floor interface to Foxlink
    """
    def __init__(self):
        pass

    @staticmethod
    def ok_to_test(serial_number):
        if serial_number:
            return True

    @staticmethod
    def save_results(log):
        foxlink_logfile_interface.saveresult(log)
        return True
