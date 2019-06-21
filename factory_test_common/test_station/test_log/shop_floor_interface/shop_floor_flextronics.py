__author__ = 'chuckyin'

# pylint: disable=W0403
# Mimic Another factory, say Flextronics shopfloor interface

import sys
import subprocess


FLEXFLOW_DIR = "C:/oculus/s1-factory-test/bin"
FLEXFLOW_BIN = "ffeticlient-1.2.exe"
# MSR bring up: seems to directly contradict this.  can{t find the ini.
# EITHER WAY, use -V option for debugging.  HUGELY helpful.
FLEXFLOW_CONFIG = "ffeticlient.ini"  # eticlient looks for the ini in its own directory, not the CWD.
#	therefore we don't need to send the -config arg as long as the exe and the ini live in the same directory.
FLEXFLOW_DIR_WIN = FLEXFLOW_DIR.replace("/", "\\")
FLEXFLOW_BASE_CALL = (FLEXFLOW_DIR + "/" + FLEXFLOW_BIN + " -config:" + FLEXFLOW_DIR_WIN + "\\" + FLEXFLOW_CONFIG)
DO_DEBUG_ONLY = True


def bail(msg):
    print msg


def read_ff_etilog_into_string():
    # ffeticlient out file goes int PWD, so don't want absolute path.
    logfile = open("ffeticlient.out")
    logstring = logfile.read()
    logfile.close()
    return logstring


def ok_to_test(uut_serial_number):
    '''Return 0 if no errors, non-zero number if not.'''

    bin_call = "%s -VERIFY %s" % (FLEXFLOW_BASE_CALL, uut_serial_number)
    fferror = None
    print "verify call: [%s]" % bin_call

    if DO_DEBUG_ONLY:
        print "verify call: [%s]" % bin_call
        fferror = 0
    else:
        try:
            writeprocess = subprocess.Popen(bin_call, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, errors = writeprocess.communicate()  # waits for process to terminate, but only returns stdout
                                                        # and stderr
            fferror = writeprocess.wait()   # this is where we actually pull the return code.
            print output
            print errors
        except OSError as the_exception:
            bail('ERROR: Unable to run FlexFlow utility: \n' + str(the_exception))

    return fferror


def ff_save_result(uut_sn, did_pass_boolean, error_code):
    '''Save pass/fail result to Flex Flow.  Return the FF return code (0=pass, else error)'''

    pass_fail_string = 'FAIL'
    fferror = None
    if did_pass_boolean:
        pass_fail_string = 'PASS'
        errorstring = ''
    else:
        pass_fail_string = 'FAIL'
        errorstring = "-code:%d" % error_code     # -code DOES want a colon.
    bin_call = "%s -%s %s %s" % (FLEXFLOW_BASE_CALL, pass_fail_string, errorstring, uut_sn)

    print "SaveResult call: [%s]" % bin_call
    if DO_DEBUG_ONLY:
        print "SaveResult call: [%s]" % bin_call
        fferror = 0
    else:
        try:
            writeprocess = subprocess.Popen(bin_call, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, errors = writeprocess.communicate()
            fferror = writeprocess.wait()
            print output
            print errors
        except OSError as the_error:
            bail('ERROR: Unable to run FlexFlow utility: \n' + str(the_error))
    return fferror


def save_results(serial_number, did_uut_pass, error_code):
    print("------------------------------------\nTesting SaveResult for UUT %s" % serial_number)
    fferror = ff_save_result(serial_number, did_uut_pass, error_code)
    print("Return code = %d" % fferror)
    if not DO_DEBUG_ONLY:
        print("Log file contents = %s" % read_ff_etilog_into_string())
    return

if __name__ == '__main__':
    import random

    try:
        SERIAL_NUMBER = "302GS015000002"  # TLA
        ok_to_test(SERIAL_NUMBER)

        RESULT_TYPE = 'VERIFY_ONLY'
        if RESULT_TYPE is 'RANDOM':
            # fun to make tests that sometimes pass and sometimes fail...
            TEST_ERROR_CODE = random.randint(0, 10)
            if TEST_ERROR_CODE <= 7:
                DIDPASS = 1
                TEST_ERROR_CODE = None
            else:
                DIDPASS = 0
        elif (RESULT_TYPE is 'FORCE_FAIL'):
            TEST_ERROR_CODE = 5
            DIDPASS = False
        elif (RESULT_TYPE is 'FORCE_PASS'):
            TEST_ERROR_CODE = 0
            DIDPASS = True

        if (RESULT_TYPE is not 'VERIFY_ONLY'):
            ff_save_result(SERIAL_NUMBER, DIDPASS, TEST_ERROR_CODE)

    except KeyboardInterrupt as the_exception:
        sys.exit()
        print("Exiting...\n")


# CONSOLE SAMPLE
# c:\oculus\s1-factory-test\lib>python shop_floor_flextronics.py
# ------------------------------------
# Testing GetUnitInfo for UUT 302GS015000002
# verify call: [C:/oculus/s1-factory-test/bin/ffeticlient-1.2.exe -VERIFY 302GS015
# 000002]
# Return code = 0
# Log file contents = {OK} 302GS015000002 Unit is ready to be processed at station
 # L1 FT-10 Auto

# ------------------------------------
# Testing SaveResult for UUT 302GS015000002
# SaveResult call: [C:/oculus/s1-factory-test/bin/ffeticlient-1.2.exe -PASS  302GS
# 015000002]
# Return code = 0
# Log file contents = {OK} 302GS015000002 OK, Unit passed and moved to state #300
# (FT-10 - Pass)


# c:\oculus\s1-factory-test\lib>python shop_floor_flextronics.py
# ------------------------------------
# Testing GetUnitInfo for UUT 302GS015000002
# verify call: [C:/oculus/s1-factory-test/bin/ffeticlient-1.2.exe -VERIFY 302GS015
# 000002]
# Return code = 8
# Log file contents = {ERROR} 302GS015000002 Routing error (entered a wrong statio
# n) [uspRTECheckRouting]


# c:\oculus\s1-factory-test\lib>
