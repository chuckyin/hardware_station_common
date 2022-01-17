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
        sorted_export_log = True
        if hasattr(self._station_config, 'SORTED_EXPORT_LOG'):
            sorted_export_log = self._station_config.SORTED_EXPORT_LOG
        testlog = test_log.TestRecord(serial_num, logs_dir=test_logs_directory, station_id=("%s" % station_id),
                                      sorted_export_log=sorted_export_log)
        if self.workorder is not None:
            testlog.set_user_metadata_dict({'work_order': self.workorder})  # add work order to log file
        self._operator_interface.print_to_console("Checking Unit %s...\n" % serial_num)
        testlog.load_limits(self._station_config)

        # Here's where the specialized station code is called:
        ok_to_test_res = testlog.ok_to_test(serial_num)
        if ok_to_test_res is True or (isinstance(ok_to_test_res, tuple) and ok_to_test_res[0]):
            (self._overall_result, self._first_failing_test_result) = self._do_test(serial_num, testlog)
        else:
            self._operator_interface.print_to_console("[WARNING] Process Control Error for %s\n" % serial_num,
                                                      'yellow')
            raise TestStationProcessControlError(f'not ok for testing, {ok_to_test_res}')

        # stuff like submit?
        # if successful submission is required for pass, check that here based on a flag

        testlog.end_test()
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
