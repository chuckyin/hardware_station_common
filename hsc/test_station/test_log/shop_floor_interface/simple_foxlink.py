#!/usr/bin/env python
""" Module to Interface with Foxlink Shop Floor System via SajetConnect.DLL
"""
#####

import ctypes

################ MAP SAJETCONNECT.DLL FUNCTIONS TO PYTHON #####################
# SAJETCONNECT.DLL must be in the Windows System path
SAJET_DLL = ctypes.WinDLL('SajetConnect.dll')
SAJET_TRANS_START = SAJET_DLL.SajetTransStart
SAJET_TRANS_START.restype = ctypes.c_bool
SAJET_TRANS_CLOSE = SAJET_DLL.SajetTransClose
SAJET_TRANS_CLOSE.restype = ctypes.c_bool
SAJET_TRANS_DATA = SAJET_DLL.SajetTransData
# SAJET_TRANS_DATA = ctypes.c_bool

# C function prototype is SajetTransData(int, char *, int *)  I think?


######################## CTYPES EXAMPLE FROM THE WEB, REMOVE AS WE DEVELOP ##########################
# Set up prototype and parameters for the desired function call.
# HLLAPI

#hllApiProto = ctypes.WINFUNCTYPE (ctypes.c_int,ctypes.c_void_p,
#    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
#hllApiParams = (1, "p1", 0), (1, "p2", 0), (1, "p3",0), (1, "p4",0),

# Actually map the call ("HLLAPI(...)") to a Python name.

#hllApi = hllApiProto (("HLLAPI", hllDll), hllApiParams)

# This is how you can actually call the DLL function.
# Set up the variables and call the Python name with them.

#p1 = ctypes.c_int (1)
#p2 = ctypes.c_char_p (sessionVar)
#p3 = ctypes.c_int (1)
#p4 = ctypes.c_int (0)
#hllApi (ctypes.byref (p1), p2, ctypes.byref (p3), ctypes.byref (p4))
######################################################################################################


def sajet_trans_start():
    """Start Foxlink Shop Floor Transport Driver"""
    # try/except stuff needed
    return SAJET_TRANS_START()


def sajet_trans_close():
    """Shutdown Foxlink Shop Floor Transport Driver"""
    # maybe just raise an exception here?
    return SAJET_TRANS_CLOSE()


def sajet_trans_data():
    """Function binding for sending data to Foxlink Shop Floor"""
    return True


################### Module Test ############################

if __name__ == "__main__":
    sajet_trans_start()
    sajet_trans_close()
