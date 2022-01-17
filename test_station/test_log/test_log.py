__author__ = 'chuckyin'

import time
from datetime import datetime
from datetime import timedelta
import re
import os
import sys
import hardware_station_common.utils as utils  # pylint: disable=F0401
import hardware_station_common.test_station.test_log.shop_floor_interface as shop_floor_interface # pylint: disable=W0403
import collections

ERROR_CODE_UNKNOWN = 9999
ERROR_CODE_NO_RESULTS = 9998


class TestLimitsError(Exception):
    pass


def make_printable(value):
    '''Helper function to make sure a value is printable before we send it to a %s printf.'''
    if (value is None):
        return "[None]"
    else:
        return str(value)


def format_as_testresult_string(name, val):
    '''Use TestResult object's built-in print functions to print arbitrary name-val pair in the same format.

    Useful for adding meta data and headers to a test log file.
    '''

    temp_result = TestResult(name)
    temp_result.set_unique_id(0)
    temp_result.set_measured_value(val)
    return temp_result.s_print_csv(with_new_line=True)


def print_csv_headers():
    '''Use TestResult object's print functions to generate headers for a one-line-per-result CSV file.'''

    temp_result = TestResult("")
    return temp_result.s_print_csv(print_headers_only=True, with_new_line=True)


class TestRecord(object):
    '''Represents the results from one full test sequence on one unit.

    Primarily a collection of TestResult instances, with some extras to do meaningful stuff with those results:
        Print those results (to various formats).
        Examine Pass/Fail result of each result to determine whether the over result is a Pass or a Fail.

    Basic usage:
        thisRun = TestRecord("302TF0340000002")
        thisRun.AddResult()
        thisRun.EndTest()

    '''
    def __del__(self):
        del self._results_array, self._user_meta_data_dict, self._shopfloor

    def __init__(self, uut_sn, logs_dir="logs", station_id=None, sorted_export_log=True):
        self._uut_sn = uut_sn
        self._start_time = datetime.now()
        self._end_time = None
        self._results_array = collections.OrderedDict()

        self._overall_did_pass = None
        self._overall_error_code = None
        self._first_failing_test_result = None
        self._sorted_export_log = sorted_export_log

        # keeping with the idea that a test log should carry enough data to print a report,
        # allow folks to enter their own arbitrary metadata
        self._user_meta_data_dict = None

        self._next_test_id = 1  # Back to starting with 1.  the 0 in the metadata lines comes from
                                # FormatAsTestResultString, not actually from the test log's result
                                # counter.

        # construct the testtype portion of the filename.
        # if we have a testtype, log file will be ${SN}_{DATE-TIME}_${TESTTYPE}_${P|F}.log
        # otherwise, leave out the _${TESTTYPE}: ${SN}_{DATE-TIME}_${P|F}.log
        self._station_id = station_id
        tt_string = ''
        if station_id is not None:
            tt_string = "%s_" % station_id

        self._unique_instance_id = ("%s_%s%s" % (uut_sn, tt_string, utils.io_utils.timestamp(self._start_time)))
        self._filename = ("%s_x.log" % self._unique_instance_id)  # _x indicates Test not finished yet.
                                                                #  Will be converted to 'p' or 'f' once overall
                                                                # test result is known.
        self._logs_dir = logs_dir  # no trailing '/'.

        self._overalls_are_uptodate = False  # flag to track whether or not results have been added since the last time
                                            # the overall result (or error code) was queried.

        self._shopfloor = shop_floor_interface.shop_floor.ShopFloor()

    def set_user_metadata_dict(self, meta):
        if self._user_meta_data_dict is None:
            self._user_meta_data_dict = meta
        else:
            # err out for now.   In the future, just iterate the new dict and add key by key.
            print (self._user_meta_data_dict)
            raise TestLimitsError("you're trying to overwrite a pre-existing test_record metadata dictionary.")

    def get_user_metadata_dict(self):
        return self._user_meta_data_dict

    def add_keyvalue_pair_to_user_metadata_dict(self, key, value):
        if self._user_meta_data_dict is None:
            new_dict = {key: value}
            self.set_user_metadata_dict(new_dict)
        else:
            self._user_meta_data_dict[key] = value

    def add_result(self, test_result_object):
        if test_result_object.get_test_name() in self._results_array:
            raise TestLimitsError("Test result names must be unique. {0}".format(test_result_object.get_test_name()))
        else:
            self._overalls_are_uptodate = False
            if test_result_object.get_unique_id() is 1:
                # default unique id is 1, if default then set an incremental unique id
                test_result_object.set_unique_id(self._next_test_id)
            self._next_test_id += 1
            self._results_array[test_result_object.get_test_name()] = test_result_object
        return self._results_array

    def add_comment(self, name, value, low_limit=None, high_limit=None):
        '''Provide a handy one-line way to add comment to a test log.

        Note that if limits are passed in, they are only logged. This is still not a Pass/Fail test.

        Main point is to free caller from having to remember TestResult interface.  e.g.
                log.AddComment("Another_comment_test", "55")
            - instead of -
                temp = TestResult("Another_comment_test")
                temp.SetMeasuredValue("55")
                log.AddResult(temp)
        '''
        temp_result = TestResult(name, low_limit, high_limit, apply_limits=False)
        temp_result.set_measured_value(value)
        self.add_result(temp_result)

    def create_and_add_result(self, name, value, low_limit=None, high_limit=None, pass_fail_result=None):
        '''Note that calling this without limits or passFailResult is the same as AddComment().'''
        temp_result = TestResult(name, low_limit, high_limit, meas=value)
        if (pass_fail_result is not None):
            temp_result.set_pass_failure_result(pass_fail_result)
        self.add_result(temp_result)
        return temp_result.did_pass()

    # todo: learn how to set up the TestLog __iter__ to do this
    def results_array(self):
        return self._results_array

    def get_overall_result(self):
        if not self._overalls_are_uptodate:
            self.calculate_overall_result()   # loads the member variable. We don't need to.
        return self._overall_did_pass

    def get_uut_sn(self):
        return self._uut_sn

    def get_station_id(self):
        return self._station_id

    def get_unique_test_instance_id(self):
        return self._unique_instance_id

    def _sort_test_results_by(self):
        return self._results_array.values()

    def calculate_overall_result(self):
        '''Callers should use the GetOverallResult() and GetOverallErrorCode functions instead.
        Calculate needs to iterate the array, so if there aren't any changes,
        the GetOverall... functions will be much faster.
        '''
        overall_did_pass = True
        if not self._results_array:
            self._overall_did_pass = False
            self._overall_error_code = ERROR_CODE_NO_RESULTS
        else:
            for test in self._sort_test_results_by():
                # grab the unique id of the first test that failed.
                if not test.did_pass():
                    overall_did_pass = False
                    if not self._overall_error_code:
                        self._first_failing_test_result = test
                        self._overall_error_code = self._first_failing_test_result.get_unique_id()
                    # once we've found one fail, we're done.
                    break

        self._overall_did_pass = overall_did_pass
        if self._overall_did_pass:
            self._overall_error_code = 0
        self._overalls_are_uptodate = True
        return self._overall_did_pass

    def end_test(self):
        self._end_time = datetime.now()
        final_result = self.calculate_overall_result()

        # cram the pass/fail result onto the filename
        result_suffix = '_F.log'
        if (final_result):
            result_suffix = '_P.log'
        self._filename = re.sub('_x.log', result_suffix, self._filename)

        elapsed_time = (self._end_time - self._start_time)
        elapsed_seconds = elapsed_time.total_seconds()

        self.add_keyvalue_pair_to_user_metadata_dict('elapsed_seconds', elapsed_seconds)

        return final_result

    def get_pass_fail_string(self):
        if self.get_overall_result():
            return 'PASS'
        else:
            return 'FAIL'

    def get_overall_error_code(self):
        if not self._overalls_are_uptodate:
            self.calculate_overall_result()   # loads the member variable. We don't need to.
        return self._overall_error_code

    # Return the entire TestResult object of the test that failed.
    def get_first_failed_test_result(self):
        if not self._overalls_are_uptodate:
            self.calculate_overall_result()   # loads the member variable. We don't need to.
        return self._first_failing_test_result

    def sprint_csv_summary_header(self):
        csv_line = "UUT_Serial_Number,Station_ID,StartTime,EndTime,OverallResult,OverallErrorCode"
        user_dictionary = self.get_user_metadata_dict()
        if user_dictionary is not None:
            for key in user_dictionary:
                csv_line += "," + key
        for test in self._results_array.values():
            csv_line += "," + test.s_print_csv(True, print_measurements_only=True)
        csv_line += "\n"

        csv_line += "UpperLimit--->,NA,NA,NA,NA,NA"
        if user_dictionary is not None:
            for key in user_dictionary:
                csv_line += ",NA"
        for test in self._results_array.values():
            csv_line += f",{test._high_limit}"
        csv_line += "\n"

        csv_line += "LowerLimit--->,NA,NA,NA,NA,NA"
        if user_dictionary is not None:
            for key in user_dictionary:
                csv_line += ",NA"
        for test in self._results_array.values():
            csv_line += f",{test._low_limit}"
        csv_line += "\n"

        return csv_line

    def sprint_csv_summary_line(self, print_headers_only=False, print_measurements_only=False):
        csv_line = ""

        # Meta data
        # NOTE: this is currently NOT writing out the user_metadata_dict.
        if (print_headers_only):
            csv_line = "UUT_Serial_Number, Station_ID, StartTime, EndTime, OverallResult, OverallErrorCode"
        else:
            csv_line = "%s, %s, %s, %s, %s, %d" % (self._uut_sn,
                                                   self._station_id,
                                                   utils.io_utils.timestamp(self._start_time),
                                                   utils.io_utils.timestamp(self._end_time),
                                                   self.get_pass_fail_string(),
                                                   self.get_overall_error_code())

        # Add user-defined meta data dictionary, if any
        user_dictionary = self.get_user_metadata_dict()
        if user_dictionary is not None:
            for key in user_dictionary:
                if (print_headers_only):
                    csv_line += ", " + key
                else:
                    csv_line += ", " + "{0}".format(user_dictionary[key])

        # Individual Test results
        for test in self._results_array.values():
            csv_line += ", " + test.s_print_csv(print_headers_only, print_measurements_only=print_measurements_only)

        csv_line += "\n"
        return csv_line

    def print_to_csvfile(self):
        if not os.path.isdir(self._logs_dir):
            utils.os_utils.mkdir_p(self._logs_dir)
        full_path = self.get_file_path()

        try:
            log_file = open(full_path, 'w')
            log_file.write(self.sprint_meta_data_to_csv())

            for test in self._sort_test_results_by():
                log_file.write(test.s_print_csv(with_new_line=True))

            log_file.close()
        except:
            print ("ERROR: couldn't open file [%s] for writing!\n" % full_path)
            raise

    # This function currently only applies to the one-log-per-test csv logfile.  Doesn't work for csv summary file.
    def sprint_meta_data_to_csv(self):
        #  mirror TestResult csv format: TestName, MeasuredVal, LoLim, HiLim, Timestamp, Result, ErrorCode
        header_string = print_csv_headers()
        header_string += format_as_testresult_string("UUT_Serial_Number", self._uut_sn)
        header_string += format_as_testresult_string("Station_ID", self._station_id)
        header_string += format_as_testresult_string("Start_Time", utils.io_utils.timestamp(self._start_time))
        header_string += format_as_testresult_string("End_Time", utils.io_utils.timestamp(self._end_time))
        header_string += format_as_testresult_string("Overall_Result", self.get_pass_fail_string())
        header_string += format_as_testresult_string("Overall_ErrorCode", self._overall_error_code)
        user_dictionary = self.get_user_metadata_dict()
        if user_dictionary is not None:
            for key in user_dictionary:
                header_string += format_as_testresult_string(key, user_dictionary[key])
        return header_string

    def set_logs_directory(self, logs_dir="./"):
        '''Allow caller to change the directory to which the results logs are written.

        If someone passes in a directory with a trailing '/', strip that off.
        '''

        self._logs_dir = re.sub(r'/$', '', logs_dir)

    def get_filename(self):
        '''Provide public access in case someone wants to know where our file was/will be written.'''
        return self._filename

    def get_file_path(self):
        return os.path.join(self._logs_dir, self._filename)

    def ok_to_test(self, serial_number):
        return self._shopfloor.ok_to_test(serial_number)

    def save_results(self):
        return self._shopfloor.save_results(self)

    def get_test_by_name(self, test_name):
        if test_name not in self._results_array:
            raise TestResultError("No test named [{0}] found in limits file.".format(test_name))
        return self._results_array[test_name]

    def set_measured_value_by_name(self, test_name, measured_value):
        result = self.get_test_by_name(test_name)
        res = result.set_measured_value(measured_value)
        return res

    def load_limits(self, station_config):
        """
        Loads the limits from the limits file (e.g., station_limits_x1StationA.py), generates
        TestResult objects, and stores them here in the testResult dictionary
        :param station_config:
        :return:
        """

        # allow running of test_log standalone for module testing.
        items = TestRecord.pre_load_limit(station_config)
        for test_result in items:
            self.add_result(test_result)

    @staticmethod
    def pre_load_limit(station_config):
        if station_config is None:
            return

        global STATION_LIMITS  # from station_limits_file
        #  add by elton:1028/2019
        config_path = os.getcwd()
        if os.path.exists(station_config.__file__):
            config_path = os.path.dirname(station_config.__file__)
        station_limits_file = os.path.join(
            config_path, 'config', ('station_limits_' + station_config.STATION_TYPE + '.py'))
        print(station_limits_file)
        try:
            exec(open(station_limits_file).read(), globals(), locals())# imports station_limits into current namespace
            # also provides "self" and "station_config" to station_limits_file
            # this is probably bad infosec practice :)
        except Exception as e:
            raise TestLimitsError("Error loading {0}: \n\t{1}".format(station_limits_file, str(e)))
        ids = [limit['unique_id'] for limit in STATION_LIMITS]
        if len(ids) != len(set(ids)):
            raise TestLimitsError("error codes are not unique!")
        test_record_items = []
        for station_limit in STATION_LIMITS:
            # ['name','low_limit', 'high_limit', 'uniqe_id']
            test_result = TestResult(name=station_limit['name'], low_limit=station_limit['low_limit'],
                                     high_limit=station_limit['high_limit'], unique_id=station_limit['unique_id'])
            test_record_items.append(test_result)
        return test_record_items

NO_ERROR_CODE_REGISTERED = -1
TEST_PASSED_CODE = 0
FAIL_MEASURED_VALUE_TOO_LOW = 2
FAIL_MEASURED_VALUE_TOO_HIGH = 3
FAIL_MANUALLY_ENTERED = 4
SCRIPT_ERROR_ON_MANUAL_ENTRY = 5


class TestResultError(Exception):
    pass


class TestResult(object):

    def __init__(self, name, low_limit=None, high_limit=None, meas=None, unique_id=1, apply_limits=True):
        self._test_name = name
        self._numeric_error_code = -1   # -1 is no code. 0 is passed.  other is an error.
        self._measured_value = None
        self._did_pass = False
        # HACKED LIMITS:
        # can only spec limits in init.
        # can't pick comptype.  Options are <= hilim and/or >= lolim
        self._low_limit = low_limit
        self._high_limit = high_limit

        self._comp_type = 'TEST'       # later should be EQ/NE/GE/LE/GT/LT/GTLT/GELE/ etc...
        if not apply_limits:
            self._comp_type = 'NOTEST'

        self._unique_id = unique_id  # never 0 to avoid confusion with 'test passed' return code

        if meas is not None:
            # self.set_measured_value(meas)
            raise TestResultError("Specifying a measurement when creating a test result is deprecated")

    def get_test_name(self):
        '''Short description of the test.  Use text that's CSV-friendly.'''
        return self._test_name

    def get_numeric_error_code(self):
        if (self._numeric_error_code is None):
            return NO_ERROR_CODE_REGISTERED
        else:
            return self._numeric_error_code

    def get_error_code_as_string(self):
        return make_printable(self._numeric_error_code)

    def set_error_code(self, numeric_error_code):
        '''Allow callers to set their own error codes.

        If people don't set this, default is to just report how the test failed.
        (too high, too low, or pass)

        '''

        self._numeric_error_code = numeric_error_code
        if (self._numeric_error_code == 0):
            self._did_pass = True
        else:
            self._did_pass = False
        self._comp_type = 'TEST'   # setmeasuredvalue without limits will have set this to 'notest' if a user is setting
                                    # error codes, that means they do want a test.

    def set_measured_value(self, value):
        self._measured_value = value
        low_ok = False
        no_test_done = True

        # skip the limits-auto-detect if (apply_limits=False) already set comp_type to NOTEST.
        if self._comp_type == 'TEST':
            if self._low_limit is None:  # no lower threshold enforced.
                low_ok = True
            else:
                no_test_done = False
                if value < self._low_limit:
                    # self.set_error_code(FAIL_MEASURED_VALUE_TOO_LOW)  # handles the didPass as well
                    low_ok = False
                else:
                    low_ok = True
            if self._high_limit is None:  # no upper threshold enforced
                high_ok = True
            else:
                no_test_done = False
                if value > self._high_limit:
                    # self.set_error_code(FAIL_MEASURED_VALUE_TOO_HIGH)  # handles the didPass as well
                    high_ok = False
                else:
                    high_ok = True

            # Set the error code (which will also trigger the didPass value to update)
            if (high_ok and low_ok):  # There were neither high limits nor low limts.
                self.set_error_code(TEST_PASSED_CODE)  # fill this in to differentiate TESTED GOOD from unknown.
                # if we checked HiLim and LoLim and no_test_done is still set, that means both limits
                # were None.  (i.e. a TestResult was created without apply_limits explicitly set to False, but both limits are None.)
                # In that case, we set the NOTEST flag now.
                if (no_test_done):
                    self._comp_type = 'NOTEST'
            elif (not low_ok):
                self.set_error_code(FAIL_MEASURED_VALUE_TOO_LOW)
            elif (not high_ok):
                self.set_error_code(FAIL_MEASURED_VALUE_TOO_HIGH)
        else:   # NOTEST
            self.set_error_code(TEST_PASSED_CODE)

        return self._measured_value

    def get_measured_value(self):
        return self._measured_value

    def set_unique_id(self, unique_id):
        self._unique_id = unique_id
        return self._unique_id

    def get_unique_id(self):
        return self._unique_id

    def set_pass_failure_result(self, result):
        '''Manually set Pass/Fail result.

        Can accept strings: "PASS" or "FAIL"
        or python True/False.

        If you've specified limits, you are not allowed to manually set PassFail resuls.
        Running this function will have no effect.

        '''

        if (self._low_limit is None) and (self._high_limit is None):
            unhandled_input = False  # flag used to track unhandled input.
            if type(result) is str:
                normalized = result.upper()

                if normalized == 'PASS':
                    self._did_pass = True
                elif normalized == 'FAIL':
                    self._did_pass = False
                    self._numeric_error_code = FAIL_MANUALLY_ENTERED
                # edit by elton
                elif normalized == self._high_limit.upper() and normalized == self._low_limit.upper():
                    self._did_pass = True
                else:
                    self._did_pass = False
                    unhandled_input = True
                    self._numeric_error_code = SCRIPT_ERROR_ON_MANUAL_ENTRY
            else:
                if result is True:
                    self._did_pass = True
                elif result is False:
                    self._did_pass = False
                    self._numeric_error_code = FAIL_MANUALLY_ENTERED
                else:
                    self._did_pass = False
                    unhandled_input = True
                    self._numeric_error_code = SCRIPT_ERROR_ON_MANUAL_ENTRY

            if unhandled_input:
                print ("DEBUG: testResult.SetPassFailResult received strange input.  %s\n" % result)

        else:   # have limits
            print ("DEBUG: testResult.SetPassFailResult cannot be used if you've specified limits.\n")

        # if someone called this, they intended this to be a test.  (even if the call failed.)
        self._comp_type = 'MANUAL'
        return self._did_pass

    def did_pass(self):
        if self._did_pass is None:
            if self._numeric_error_code is not None:
                if self._numeric_error_code == 0:
                    self._did_pass = True
                else:
                    self._did_pass = False

        return self._did_pass

    def get_pass_fail_string(self):
        if self._did_pass:
            return 'PASS'
        else:
            return 'FAIL'

    def s_print_csv(self, print_headers_only=False, with_new_line=False, print_measurements_only=False):
        '''Represent test result members in a handy CSV format.

        Can be printed with newline (for per-unit logs with one result per line)
                    or without (for summary logs with one full test instance per line)
        '''

        csv_line = ''

        if (print_headers_only):
            if print_measurements_only:
                # in this case, the header is the test name.
                # In the case where we're printing the full results, the header is just 'MeasuredVal'
                csv_line = self._test_name
            else:
                csv_line = ("Index, TestName, MeasuredVal, LoLim, HiLim, Result, ErrorCode")
        else:

            # Processing of MeasuredValue is common to both paths:
            val = str(self.get_measured_value())
            # If we're using this function to generate the individual unit logfile,
            # write the whole enchilada.  If we're adding our result to the csv summary file,
            # we want to get of any newlines within the Measured Value string.
            if with_new_line is False:
                val = val.rstrip('\r\n')
                newline_count = val.count('\r') + val.count('\n')
                if newline_count:
                    val = '(LONG STRING - SEE LOGFILE)'

            if print_measurements_only:
                csv_line = val
            else:

                # Make the NOTEST lines obviously different from the test lines.
                test_index = self.get_unique_id()
                name = self._test_name
                # val calculated above.
                error = self.get_error_code_as_string()

                if (self._comp_type is 'NOTEST'):
                    if self._low_limit is not None:
                        low = make_printable(self._low_limit)
                    else:
                        low = ' '
                    if self._high_limit is not None:
                        high = make_printable(self._high_limit)
                    else:
                        high = ' '
                    pass_fail = '(LOG)'
                else:
                    low = make_printable(self._low_limit)
                    high = make_printable(self._high_limit)
                    pass_fail = self.get_pass_fail_string()

                csv_line = ("%d, %s, %s, %s, %s, %s, %s" % (test_index,
                                                                name,
                                                                val,
                                                                low,
                                                                high,
                                                                pass_fail,
                                                                error))

        if with_new_line:
            csv_line += "\n"
        return csv_line


if __name__ == '__main__':
    from time import sleep

    try:
        LOG = TestRecord("aabbccdd3")  # optional: pass logsDir argument.
        LOG.load_limits(None)

        # set limits
        TEST1 = TestResult("test 1", low_limit=20)
        TEST1.set_measured_value(21)
        #test1.SetPassFailResult(True)
        LOG.add_result(TEST1)
        print ("Sleeping for a bit to get better elapsed time.")
        sleep(1)

        # manually set Pass/Fail
        TEST2 = TestResult("test 2")
        TEST2.set_measured_value("string value")
        TEST2.set_pass_failure_result("PASS")
        LOG.add_result(TEST2)

        # no compare, note only
        TEST3 = TestResult("test 3")
        TEST3.set_measured_value("Just a comment.")
        LOG.add_result(TEST3)

        TEST5 = TestResult("should_fail-manual")
        TEST5.set_measured_value("string value")
        TEST5.set_pass_failure_result("FAIL")
        LOG.add_result(TEST5)

        TEMP = TestResult("fail high but pass low", high_limit=30, low_limit=20)
        TEMP.set_measured_value(31)
        LOG.add_result(TEMP)

        TEMP = TestResult("fail-script_sent_bad_pf_result")
        TEMP.set_measured_value("string value")
        TEMP.set_pass_failure_result("Pail")
        LOG.add_result(TEMP)

        LOG.add_comment("Another_comment_test", "55")

        LOG.add_keyvalue_pair_to_user_metadata_dict('workorder', 'just_a_test_001')

        LOG.end_test()

        print ("-----------------------------------------")
        print ("Test Overview for CSV summary file:\n")

        print ("::HEADERS::")
        print (LOG.sprint_csv_summary_line(True))
        print ("::DATA::")
        print (LOG.sprint_csv_summary_line())
        print ("-----------------------------------------\n")

        print ("Per-instance log file: %s" % LOG.get_filename())

        print ("-----------------------------------------\n")
        LOG.print_to_csvfile()

    except KeyboardInterrupt as keyboard_interrupt:
        print("Exiting...\n")
        sys.exit(0)
