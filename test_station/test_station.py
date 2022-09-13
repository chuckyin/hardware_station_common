__author__ = 'chuckyin'

# pylint: disable=F0401
# pylint: disable=R0921

import os
from .test_log import test_log
import hardware_station_common.utils.serial_number as serial_number
import hardware_station_common.utils as utils  # pylint: disable=F0401


class TestStationError(Exception):
    pass


class TestStationProcessControlError(Exception):
    def __init__(self, message = None):
        self.message = message

class TestStationSerialNumberError(Exception):
    pass


class TestStation(object):
    """
        abstract base class for Test Stations
            this class should contain only code that is common to al projects

    """

    def __init__(self, station_config, operator_interface):
        self._operator_interface = operator_interface
        self._station_config = station_config
        self.workorder = None
        self._overall_result = None
        self._first_failing_test_result = None
        self._array = test_log.TestRecord.pre_load_limit(station_config)

        test_items = []
        if hasattr(station_config, 'FULL_TREE_UI') and station_config.FULL_TREE_UI:
            csv_line = test_log.TestRecord.CSV_LINE
            csv_headers = csv_line.split(',')
            for idx, header in enumerate(csv_headers):
                test_items.append({
                    'Item': header, 'ErrCode': '', 'Lsl': '', 'Usl': ''
                })
        for test_result in self._array:
            name = test_result.get_test_name()
            lsl = test_result._low_limit
            usl = test_result._high_limit
            err = test_result.get_unique_id()
            if (hasattr(station_config, 'FULL_TREE_UI') and station_config.FULL_TREE_UI
                    or (err > 0 and (lsl or usl))):
               test_items.append({
                   'Item': name, 'Errcode': err, 'Lsl': lsl, 'Usl': usl
               })
        self._operator_interface.update_test_item_array(test_items)

    def initialize(self):
        """ Initialize test station
        """
        raise NotImplementedError()

    def close(self):
        """
        Shut down test station
        """
        raise NotImplementedError()

    def test_unit(self, serial_num):
        """
           abstract interface for Testing A Unit
             this function should contain only code that is common to all projects
             return overall pass/fail result and overall error code
        """
        test_logs_directory = os.path.join(self._station_config.ROOT_DIR, "factory-test_logs")
        station_id = ("%s-%s" % (self._station_config.STATION_TYPE, self._station_config.STATION_NUMBER))
        testlog = test_log.TestRecord(serial_num, logs_dir=test_logs_directory, station_id=("%s" % station_id))
        if self.workorder is not None:
            testlog.set_user_metadata_dict({'work_order': self.workorder})  # add work order to log file
        self._operator_interface.print_to_console("Checking Unit %s...\n" % serial_num)
        testlog.load_limits(self._station_config)

        pre_data = {'UUT_Serial_Number': testlog.get_uut_sn(),
                    'Station_ID': testlog.get_station_id(),
                    'StartTime': utils.io_utils.timestamp(testlog._start_time)}
        for k, v in pre_data.items():
            self._operator_interface.update_test_value(item_name=k, val=v, result=0)

        # Here's where the specialized station code is called:
        # ok_to_test_res = testlog.ok_to_test(serial_num)
        (self._overall_result, self._first_failing_test_result) = self._do_test(serial_num, testlog)
        # if ok_to_test_res is True or (isinstance(ok_to_test_res, tuple) and ok_to_test_res[0]):
        #     (self._overall_result, self._first_failing_test_result) = self._do_test(serial_num, testlog)
        # else:
        #     self._operator_interface.print_to_console("[WARNING] Process Control Error for %s\n" % serial_num,
        #                                               'yellow')
        #     raise TestStationProcessControlError(f'not ok for testing, {ok_to_test_res}')

        # stuff like submit?
        # if successful submission is required for pass, check that here based on a flag

        testlog.end_test()
        # update test items after finishing.
        pre_data = {'OverallResult': testlog.get_overall_result(),
                    'OverallErrorCode': testlog.get_overall_error_code(),
                    'OverallErrorString': testlog.get_overall_error_string(),
                    'EndTime': utils.io_utils.timestamp(testlog._end_time)}
        for k, v in pre_data.items():
            self._operator_interface.update_test_value(item_name=k, val=v, result=0)

        try:
            testlog.print_to_csvfile()
            if hasattr(self._station_config, 'CSV_SUMMARY_DIR') and self._station_config.CSV_SUMMARY_DIR is not None:
                if not os.path.isdir(self._station_config.CSV_SUMMARY_DIR):
                    utils.os_utils.mkdir_p(self._station_config.CSV_SUMMARY_DIR)
                csv_basename = "{0}_{1}_summary.csv".format(station_id, utils.io_utils.datestamp())
                csv_summary_file = os.path.join(self._station_config.CSV_SUMMARY_DIR, csv_basename)
                utils.io_utils.append_results_log_to_csv(testlog, csv_summary_file, print_measurements_only=True)
        except Exception as e:
            self._operator_interface.print_to_console(f"WARNING: unable to write to test log file {str(e)}")
            raise TestStationProcessControlError('fail to save test log.')

        if self._station_config.FACEBOOK_IT_ENABLED:
            self._operator_interface.print_to_console("saving results to shopfloor system.\n")
            save_result_res = testlog.save_results()
            if not save_result_res or (isinstance(save_result_res, tuple) and not save_result_res[0]):
                self._operator_interface.print_to_console("[WARNING] Process Control Error for %s\n" % serial_num,
                                                          'yellow')
                raise TestStationProcessControlError(f'fail to save result. {save_result_res}')

        self._operator_interface.print_to_console("Testing Unit %s Complete\n" % serial_num)
        #AppendResultToCSV(startTimestamp, sn, hw_id, didUUTPass, returnCode)
        return self._overall_result, self._first_failing_test_result

    def is_ready(self):
        raise NotImplementedError()

    def validate_sn(self, serial_num):
        if self._station_config.SERIAL_NUMBER_VALIDATION:
            try:
                serial_number.validate_sn(serial_num, self._station_config.SERIAL_NUMBER_MODEL_NUMBER)
                return True
            except serial_number.SerialNumberError as serialnumbererror:
                raise TestStationSerialNumberError(str(serialnumbererror))
        else:
            return True

    def systemtime(self):
        return utils.io_utils.systemtime()

    def _do_test(self, serial_num, testlog):
        """
        Function for performing the test of a unit
        :param seria_number:
        :param test_limits:
        :param testlog:
        :return overall_result, overall_errorcode
        """
        raise NotImplementedError()

    def login(self, active, usr, pwd):
        raise NotImplementedError()
