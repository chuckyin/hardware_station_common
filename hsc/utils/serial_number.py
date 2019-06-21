__author__ = 'chuckyin'

#!/usr/bin/env python
# pylint: disable=R0904
"""
serial_number class for dealing with serial numbers of units
"""
SN_NUM_CHARS = [14]
import re

class SerialNumberError(Exception):
    pass


def validate_sn(serial_number, model_number=None):
    """
    Checks if a given serial number is valid
    """
    if len(serial_number) not in SN_NUM_CHARS:
        raise SerialNumberError("SERIAL NUMBER ERROR: Invalid SN length.\n")
    if serial_number[1:4] != model_number:
        raise SerialNumberError("SERIAL NUMBER ERROR: Invalid Model Number")
    return True