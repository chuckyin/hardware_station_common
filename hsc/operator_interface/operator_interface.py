__author__ = 'chuckyin'

# pylint: disable=F0401

import os
import time
from factory_test_common import utils

class OperatorInterfaceError(Exception):
    pass


class OperatorInterface(object):
    def __init__(self, station_config, console, prompt, log_to_file=True):
        self._console = console
        self._prompt = prompt
        self._debug_log = log_to_file
        if log_to_file:
            self._debug_log_dir = os.path.join(station_config.ROOT_DIR, "factory-test_debug")
            if not os.path.isdir(self._debug_log_dir):
                utils.os_utils.mkdir_p(self._debug_log_dir)
            self._debug_file_name = os.path.join(self._debug_log_dir, utils.io_utils.timestamp() + "_debug.log")
            try:
                self._debug_log_obj = open(self._debug_file_name, 'w', 0)  # use unbuffered file for writing debug info
            except:
                raise

    def prompt(self, msg, color=None):
        self._prompt.config(text=(msg))
        if color is not None:
            self._prompt.config(bg=color)
        self._prompt.update()

    def print_to_console(self, msg, color=None):
        self._console.print_msg('[{0}]: '.format(utils.io_utils.timestamp()) + msg)
        if color is not None:
            self._console.set_bg(color)
        if self._debug_log:
            self._debug_log_obj.write('[{0}]: '.format(utils.io_utils.timestamp()) + msg)

    def clear_console(self):
        self._console.clear()
        if self._debug_log:

            self._debug_log_obj.close()
            self._debug_file_name = os.path.join(self._debug_log_dir, utils.io_utils.timestamp() + "_debug.log")
            self._debug_log_obj = open(self._debug_file_name, 'w', 0)  # use unbuffered file for writing debug info

    def close(self):
        if self._debug_log:
            self._debug_log_obj.close()

    def operator_input(self, title=None, msg=None, msg_type='info'):
        if msg_type == 'info':
            utils.gui_utils.MessageBox.info(title, msg)
        elif msg_type == 'warning':
            utils.gui_utils.MessageBox.warning(title, msg)
        elif msg_type == 'error':
            utils.gui_utils.MessageBox.error(title, msg)
        else:
            raise OperatorInterfaceError("undefined operator input type!")

    def wait(self, pause_seconds, rationale=None):
        """
        an attempt to manage random magic sleeps in test code
        :param pause_seconds:
        :param rationale:
        :return:
        """
        message = 'Sleeping for {0}: '.format(pause_seconds)
        if rationale is not None:
            message += rationale + ' \n'
        else:
            message += 'ZZZ \n'
        self.print_to_console(message)
        time.sleep(pause_seconds)

    def display_image(self, image_file):
        utils.gui_utils.ImageDisplayBox.display(image_file)
