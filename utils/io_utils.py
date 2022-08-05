__author__ = 'chuckyin'

"""
Various I/O helper functions
"""
import os
import time
import datetime
import math


def read_line_from_file(filename):
    val = ''
    try:
        infile = open(filename)
        line = infile.readline()
        infile.close()
        val = line.rstrip()
    except:
        raise

    return val


def append_results_log_to_csv(test_log, summary_filename, print_measurements_only=True):
    current_header = ''
    print_headers_first = False
    line = test_log.sprint_csv_summary_header()
    if not os.path.exists(summary_filename):
        print_headers_first = True
    else:
        with open(summary_filename, 'r') as f:
            for i in range(3):
                current_header += f"{f.readline()}"
        if  current_header.upper() != line.upper():
            os.rename(summary_filename, f"{os.path.splitext(summary_filename)[0]}_{time.strftime('%H%M%S')}.csv")
            print_headers_first = True

    summary_file = open(summary_filename, 'a')
    if print_headers_first:
        summary_file.write(line)
    line = test_log.sprint_csv_summary_line(print_headers_only=False, print_measurements_only=print_measurements_only)
    summary_file.write(line)
    summary_file.close()

# actually datetime, but whatever...
def timestamp(datetime_object=None):
    """Helper function to standardize timestamp formats used in this module."""

    if datetime_object is None:
        datetime_object = datetime.datetime.now()
    return datetime_object.strftime("%Y%m%d-%H%M%S")


def datestamp(datetime_object=None):
    if datetime_object is None:
        datetime_object = datetime.datetime.now()
    return datetime_object.strftime("%Y%m%d")

def round_ex(number, ndigits=2, rounding='ROUND_HALF_UP'):
    if not math.isfinite(number):
        return number
    if rounding == 'ROUND_HALF_UP':
        return round(number * (10 ** ndigits)) / float(10 ** ndigits)
    elif rounding == 'ROUND_HALF_EVEN':
        return round(number, ndigits)
