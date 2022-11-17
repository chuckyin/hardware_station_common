__author__ = 'chuckyin'

# pylint: disable=F0401

import os
import time
import datetime
from hardware_station_common import utils
import json

import clr
import UIDep.UIDepHelper as ui_dep_helper

depencies = ui_dep_helper.all_depencies()

for c in depencies:
    clr.AddReference(c)

from System.Windows import Application, Window
from System.Threading import Thread, ApartmentState, ThreadStart
from System import Action, Delegate, Func
from System.Collections.Generic import Dictionary

class OperatorInterfaceError(Exception):
    pass


class OperatorInterface(object):
    def __init__(self, gui, console, log_dir):
        self._console = console
        self._gui = gui
        if log_dir:
            self._debug_log_dir = log_dir
            if not os.path.isdir(self._debug_log_dir):
                utils.os_utils.mkdir_p(self._debug_log_dir)
            self._debug_file_name = os.path.join(self._debug_log_dir, utils.io_utils.timestamp() + "_debug.log")
            try:
                self._debug_log_obj = open(self._debug_file_name, 'w')  # use unbuffered file for writing debug info
            except:
                raise

    def menubtn_cfg(self, key, status, text):
        if Application.Current.Dispatcher.CheckAccess():
            return self._console.UpdateMenuItem(key, status, text)
        else:
            return Application.Current.Dispatcher.Invoke(Func[str, bool, str](self.menubtn_cfg))

    def prompt(self, msg, color='aliceblue'):
        self._console.UpdatePromptMsg(msg, color)

    def print_to_console(self, msg, color=None):
        color_map = {
            'blue': 1,
            'red': 2,
        }
        if color in color_map:
            self._console.UpdateTestLogs(msg.rstrip('\n'), color_map[color])
        else:
            self._console.UpdateTestLogs(msg.rstrip('\n'), 0)
        self._debug_log_obj.write('[{0}]: '.format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")) + msg)
        self._debug_log_obj.flush()

    def update_test_item(self, item_name, lsl, usl, errcode):
        self._console.UpdateTestItem(item_name, str(lsl), str(usl), str(errcode))

    def update_test_item_array(self, items):
        self._console.UpdateTestItem(json.dumps(items))

    def update_test_value(self, item_name, val, result):
        self._console.UpdateTestValue(item_name, str(val), int(result))

    def clear_test_values(self):
        self._console.InitialiseTestValue()

    def clear_console(self):
        # self._console.clear()
        self._console.ClearTestLogs()

        self._debug_log_obj.close()
        self._debug_file_name = os.path.join(self._debug_log_dir, utils.io_utils.timestamp() + "_debug.log")
#            self._debug_log_obj = open(self._debug_file_name, 'w', 0)  # use unbuffered file for writing debug info
        self._debug_log_obj = open(self._debug_file_name, 'w')  # use unbuffered file for writing debug info

    def close(self):
        self._debug_log_obj.close()

    def operator_input(self, title=None, msg=None, msg_type='info', msgbtn=0):
        if Application.Current.Dispatcher.CheckAccess():
            if msg_type == 'info':
                return utils.gui_utils.MessageBox.info(title, msg, msgbtn)
            elif msg_type == 'warning':
                return utils.gui_utils.MessageBox.warning(title, msg, msgbtn)
            elif msg_type == 'error':
                return utils.gui_utils.MessageBox.error(title, msg, msgbtn)
            else:
                raise OperatorInterfaceError("undefined operator input type!")
        else:
            Application.Current.Dispatcher.Invoke(Action[str, str, str, int](self.operator_input), title, msg, msg_type, msgbtn)

    def wait(self, pause_seconds, rationale=None):
        """
        an attempt to manage random magic sleeps in test code
        :param pause_seconds:
        :param rationale:
        :return:
        """
        pass

    def display_image(self, image_file):
        if Application.Current.Dispatcher.CheckAccess():
            utils.gui_utils.ImageDisplayBox.display(image_file)
        else:
            Application.Current.Dispatcher.Invoke(Action[str](self.display_image), image_file)

    def update_root_config(self, dic):
        clrdict = Dictionary[str, str]()
        for k,v in dic.items():
            clrdict[k] = v
        self._console.Config(clrdict)

    def active_start_loop(self, serial_number=None):
        if serial_number is not None:
            self.update_root_config({'SN': serial_number})
        self._console.MovFocusToSn()
        self._console.StartLoop()

    def close_application(self):
        if Application.Current.Dispatcher.CheckAccess():
            Application.Current.Shutdown(-1)
        else:
            Application.Current.Dispatcher.Invoke(Action(self.close_application))

    def current_serial_number(self):
        if Application.Current.Dispatcher.CheckAccess():
            return self._console.SerialNumber
        else:
            return Application.Current.Dispatcher.Invoke(Func[str](self.current_serial_number))
