__author__ = 'chuckyin'

#!/usr/bin/env python
# pylint: disable=F0401

# Interface to Factory Shop Floor Systems
# Mimic factory, say Foxlink log file Shopfloor interface
from datetime import datetime
from ..test_log import TestRecord
import os
import station_config

TGS_MONITORED_DIRECTORY = "D:/XID"

# General idea:
#   Generate file with format below.
#   Save this file to TGS_MONITORED_DIRECTORY
#       filename can be anything, as long as it's unique.
#       extension is .txt
#   Foxlink's TGS system has a process that's scraping this directory for new logs.
#
# contents sample:
# from file C4M251401T2F798A7.txt
# TTime=2012/12/15_05:30:21;SN=C4M251401T2F798A7;Result=FAIL;ErrorCode=17;WorkOrder=NKA0000001


def make_tgs_timestamp():
    stamp = datetime.now()
    return stamp.strftime("%Y/%m/%d_%H:%M:%S")


def generate_file_contents(log):
    """Save Relevant Results from the Test Log to the Shop Floor System"""

    #Extract the data we need from the testRecord instance
    serial_number = log.get_uut_sn()
    result = log.get_pass_fail_string()
    errorcode = log.get_overall_error_code()
    test_time = make_tgs_timestamp()
    station_id = log.get_station_id()

    workorder = ""
    log_metadata = log.get_user_metadata_dict()
    if (log_metadata is not None) and ('workorder' in log_metadata):
        workorder = log_metadata['workorder']

    if(hasattr(station_config, 'FOXLINK_SFC_NEEDS_STATION_ID') and station_config.FOXLINK_SFC_NEEDS_STATION_ID):
        file_contents = ("TTime=%s;SN=%s;Result=%s;ErrorCode=%s;Station_ID=%s;WorkOrder=%s" % (test_time, serial_number, result,errorcode, station_id, workorder))
    else:
        file_contents = ("TTime=%s;SN=%s;Result=%s;ErrorCode=%s;WorkOrder=%s" % (test_time, serial_number, result,
                                                                             errorcode, workorder))
    return file_contents


def saveresult(log, monitored_directory=None):
    contents = generate_file_contents(log)
    output_directory = TGS_MONITORED_DIRECTORY
    if monitored_directory is not None:
        output_directory = monitored_directory
    filename = os.path.join(output_directory, (log.get_unique_test_instance_id() + ".txt"))
    fileobj = open(filename, 'w')
    fileobj.write(contents)
    fileobj.close()

if __name__ == '__main__':

    print 'Testing shopFloor.py'

    MY_LOG = TestRecord('dummy_sn')
    DICTIONARY = {}
    DICTIONARY['specialSauce'] = '21'
    DICTIONARY['workOrder'] = '9999999'
    # simplest way to make a dictionary: dict = { 'workOrder': 'js;lakjfas' }

    MY_LOG.set_user_metadata_dict(DICTIONARY)
    print generate_file_contents(MY_LOG)
    saveresult(MY_LOG)

    print MY_LOG.sprint_meta_data_to_csv()
