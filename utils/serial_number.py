__author__ = 'chuckyin'

#!/usr/bin/env python
# pylint: disable=R0904
"""
serial_number class for dealing with serial numbers of units
"""
import re

class SerialNumberError(Exception):
    pass


def validate_sn(serial_number, model_number=None):
    """
    Checks if a given serial number is valid
    """
    try:
        if re.match(model_number, serial_number, re.I) is None:
            raise SerialNumberError(f"SERIAL NUMBER ERROR: Invalid Serial Number = {serial_number}. len={len(serial_number)}")
    except re.error as err:
        raise SerialNumberError("INVALID config SERIAL_NUMBER_MODEL_NUMBER = %s, exp = %s." % (model_number, err.msg))
    return True
