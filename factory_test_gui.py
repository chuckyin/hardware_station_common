__author__ = 'chuckyin'

#!/usr/bin/env python
# pylint: disable=R0902
# pylint: disable=R0904
# pylint: disable=R0924
# pylint: disable=W0201

#import Tkinter as tk
#import tkMessageBox

import tkinter as tk
from tkinter import messagebox
import time
import argparse
import hardware_station_common.operator_interface as operator_interface
import hardware_station_common.test_station as test_station
import hardware_station_common.utils as utils
import re
import hardware_station_common.test_station.test_log as test_log
import os
import ctypes
import sys
import gc
import logging
import datetime


class FactoryTestGui(object):
    def __init__(self, station_config, test_station_init):
        self.station_config = station_config
        self._test_station_init = test_station_init
        #self.station = self.station_config.STATION_TYPE # I think this was a mistake somehow
        self.station = None
        self._operator_interface = None
        self._g_loop_sn = None
        self._g_num_loops_completed = 0
        self._g_num_passing_loops = 0
        self._g_target_num_loops = None   # None is special flag for "we're not looping."
        self._loop_label = None
        self.work_order_label = None
        self._work_order_edit_button = None
        self._sn_entry = None
        self.g_workorder = ""
        self._cons = None
        self._prompt = None
        self.root = None
        self._g_entry_allowed = False

    def is_looping_enabled(self):
        return self._g_target_num_loops is not None

    def update_loop_counter(self, last_test_result=None):
        '''
        Function to update the GUI with loop counts if we're looping.
        Return:
            total number of test iterations completed (if we're looping)
            OR None (if we're not looping)
        '''

        if self.is_looping_enabled():  # protect the looplabel access in case it doesn't exist.

            # update the TOTAL and PASSING counters
            if last_test_result is not None:
                self._g_num_loops_completed += 1
                if last_test_result:
                    self._g_num_passing_loops += 1

            # report counts to the user
            self._loop_label.config(text=("completed %d of %d loops.  %d passed" %
                                    (self._g_num_loops_completed, self._g_target_num_loops, self._g_num_passing_loops)))
            self._loop_label.update()
            time.sleep(1)

            # check if we're done looping
            if self._g_target_num_loops == 0:
                # num_loops = 0 is special case to indicate that you want infinite looping.
                # Skip the 'done looping' test and close-out steps.
                pass
            else:
                # are we done looping?
                if self._g_num_loops_completed >= self._g_target_num_loops:
                    self._g_loop_sn = None  # this will trigger WaitForUUT() to pause
                    self._g_num_loops_completed = 0
                    self._g_num_passing_loops = 0

            # return total number of loops
            return self._g_num_loops_completed
        else:
            # if we're not in looping mode, this function returns None
            return None

    # wait for operator to scan barcode label
    # This does not necessarily start the test.
    def setguistate_waitforsn(self):
        self._operator_interface.print_to_console("waiting for sn\n")
        self._g_entry_allowed = True
        if self._g_loop_sn is None:  # Whether we're looping or not, we need a SN.
            self._sn_entry.config(state='normal')
            if not self.station_config.FACEBOOK_IT_ENABLED:
                self._sn_entry.config(bg='yellow')
            self._sn_entry.delete(0, tk.END)   # make sure to re-enable the control BEFORE deleting.
            self._sn_entry.focus_set()
            #fixture.SetDefaultState()
            self._prompt.config(text="Scan or type DUT Serial Number:")
        elif self.is_looping_enabled():
            # SN is still left in the box from when we first got it.
            # Manually call the OnSnEnter callback since 5 minutes of googling didn't tell me how to
            # programatically enter the text into the SN text box.
            self.on_sn_enter(None)     # on_sn_enter expects the calling event to be passed in.
                                     # telling it we have None will make it use the gLoopSN

    def write(self, msg):
        """
        @type msg: str
        @return:
        """
        if not msg.isspace():
            msg = msg.strip('\n')
            msg = msg.replace('\r', '」') + '\n'
            self._operator_interface.print_to_console(msg)

    # if there are basic errors connecting to instruments, we should find out before
    # an operator starts testing.
    def setguistate_initializetester(self, station):
        self._operator_interface.print_to_console("Initializing Tester...\n", "grey")
        self._sn_entry.config(state='disabled')
        setup_ok = True
        if station:
            try:
                gc.enable()
                if (hasattr(self.station_config, 'IS_PRINT_TO_LOG')
                        and self.station_config.IS_PRINT_TO_LOG):
                    sys.stdout = self
                    sys.stderr = self
                    sys.stdin = None

                if (hasattr(self.station_config, 'IS_LOG_PROFILING')
                     and self.station_config.IS_LOG_PROFILING):
                    logger = logging.getLogger('profiling')
                    logger.setLevel(logging.DEBUG)
                    fn = f'profile_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
                    handler = logging.FileHandler(fn)
                    handler.setLevel(logging.DEBUG)
                    logger.addHandler(handler)

                station.initialize()

                show_console = 0
                whnd = ctypes.windll.kernel32.GetConsoleWindow()
                if whnd != 0:
                    if hasattr(self.station_config, 'SHOW_CONSOLE') and self.station_config.SHOW_CONSOLE:
                        show_console = 1
                ctypes.windll.user32.ShowWindow(whnd, show_console)

            except test_station.test_station.TestStationError:
                self._operator_interface.print_to_console("Error Initializing Test Station.\n", "red")
                setup_ok = False
        if setup_ok:
            self._operator_interface.print_to_console("Initialization complete.\n")
            self.setguistate_waitforsn()
        else:
            self._sn_entry.config(state='disabled')
            # then we'll drop back int mainloop(), but our controls are disabled.

    # wait for the signal that the UUT is in the fixture and everything is ready to run.
    # In the simplest case, this could be <ENTER> from the operator
    def setguistate_waitfortesterready(self):
        self._cons.set_bg('grey')
        self._sn_entry.config(state='disabled')
        self.station.is_ready()
        # if not self.is_looping_enabled():
        #     self._operator_interface.clear_console()
        self.setguistate_run()

    def thread_it(self, func, *args):
        import threading
        t = threading.Thread(target=func, args=args)
        t.setDaemon(True)
        t.start()
        return t

    def setguistate_run(self):
        self._prompt.config(text="Test in progress.")
        self._prompt.update()
        self._cons.set_bg('white')
        if hasattr(self.station_config, 'OPTIMIZE_UI_MODE') and self.station_config.OPTIMIZE_UI_MODE:
            args = self._sn_entry.get()
            self.thread_it(self.run_test, args)
        else:
            self.run_test(self._sn_entry.get())

    def test_iteration(self, serial_number):
        self._operator_interface.print_to_console("Running Test.\n")
        overall_result = False
        first_failed_test_result = None
        if self.station_config.USE_WORKORDER_ENTRY:
            self.station.workorder = self.g_workorder
        try:
            (overall_result, first_failed_test_result) = self.station.test_unit(serial_number.upper())
        except test_station.test_station.TestStationProcessControlError as e:
            # self._operator_interface.operator_input("Process Control Error",
            #                                         "Unit %s [  %s  ] ...\n" % (serial_number, e.message))
            msg = 'Process Control Error: Unit %s [  %s  ] ...\n' % (serial_number, e.message)
            self._operator_interface.print_to_console(msg, 'red')
            self._operator_interface.print_to_console('*******************\n')
            self._g_loop_sn = None  # cancle the loop test while error
            return
            
        except Exception as e:
            self._operator_interface.print_to_console("Test Station Error:{0}\n".format(str(e)), "red")
            self._g_loop_sn = None

        self.gui_show_result(serial_number, overall_result, first_failed_test_result)

    def run_test(self, serial_number):
        print (f'SERINAL_NUMBER:{serial_number}\n')
        if self.is_looping_enabled():
            self._g_loop_sn = serial_number  # record the SN into the persistent global for next time.
        self.test_iteration(serial_number)
        while self._g_loop_sn is not None:
            self.test_iteration(serial_number)
        self.setguistate_waitforsn()
        gc.collect()

    def get_free_space_mb(self, folder):
        import ctypes
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value / 1024 / 1024

    def check_free_space_ready(self):
        if not hasattr(self.station_config, 'MIN_SPACE_REQUIRED'):
            return True
        if isinstance(self.station_config.MIN_SPACE_REQUIRED, list):
            req_dirs = [c for c in self.station_config.MIN_SPACE_REQUIRED if os.path.exists(c[0])]
            chk_free_space = [self.get_free_space_mb(req_dir) >= req_size for req_dir, req_size in req_dirs]
            if not all(chk_free_space):
                msg = f"Unable to start test, please check mini-space required: {req_dirs} "
                self._operator_interface.operator_input('WARN', msg=msg, msg_type='warning')
                return False
        else:
            self._operator_interface.print_to_console(f'Please update the configuration named min_space_required.\n')
        return True

    #####################################################################
    # WaitFor Fixture Ready pollers.
    #####################################################################

    #####################################################################
    # GUI Event handler callbacks
    #####################################################################
    def on_sn_enter(self, event):
        if not self.check_free_space_ready():
            return
        if self._g_entry_allowed is True:
            self._operator_interface.clear_console()
            if (event is None):
                self._operator_interface.print_to_console(
                    "on_sn_enter (looping): Using serial number value of %s\n" % self._g_loop_sn)
                user_value = self._g_loop_sn
            else:
                user_value = event.widget.get()
            try:
                self._g_entry_allowed = False
                self.station.validate_sn(user_value)
                if self.is_looping_enabled():
                    self._g_num_loops_completed = 0
                    self._g_num_passing_loops = 0
                    self.update_loop_counter()
                    self._g_loop_sn = user_value      # record the SN into the persistent global for next time.
                self.setguistate_waitfortesterready()
            except test_station.test_station.TestStationSerialNumberError as teststationerror:
                messagebox.showwarning(message="%s" % str(teststationerror))
                self._g_entry_allowed = True
                self.setguistate_waitforsn()

    def on_app_exit(self):
        if self.station is not None:
            self.station.close()
        if self._operator_interface is not None:
            self._operator_interface.close()
        time.sleep(1)
        self.root.destroy()

    def gui_show_result(self, serial_number, overall_result, first_failed_test_result=None):

        result_message = "\n-----------------------------------\n"
        did_pass = False
        if overall_result:
            result_message += "\nUnit [ {0} ] Passed!\n".format(serial_number)
            did_pass = True
            error_code = '[0]'
        else:
            result_message += "\nUnit [ {0} ] Failed!\n".format(serial_number)
            if first_failed_test_result is None:
                error_code = "(unknown)"
            else:
                error_code = "{0}.{1}".format(
                    first_failed_test_result.get_unique_id(),
                    first_failed_test_result.get_error_code_as_string())

        result_message += "\n-----------------------------------\n"
        result_message += "Error Code = {0}\n".format(error_code)
        if not overall_result and first_failed_test_result is not None:
            result_message += first_failed_test_result.s_print_csv()
        result_message += "\n-----------------------------------\n"
        result_message += "\n\n"
        if did_pass:
            self._operator_interface.print_to_console(result_message, "green")
        else:
            self._operator_interface.print_to_console(result_message, "red")
        self.update_loop_counter(did_pass)

    def create_station(self):
        try:
            self._operator_interface.print_to_console('Station Type: %s\n' % self.station_config.STATION_TYPE)
            # may have to move this to mainloop
            self.station = self._test_station_init(self.station_config, self._operator_interface)
        except:
            raise

    @staticmethod
    def parse_arguments():
        # Arg handling
        # handle command-line args
        parser = argparse.ArgumentParser(description='GUI for Programming/Test station.')
        loop_help = 'FOR STATION VERIFICATION ONLY: number of timesto repeat the test without cycling the fixture.'
        parser.add_argument('-l', '--numloops',
                            type=int,
                            help=loop_help)
        parser.add_argument('-s', '--serialnum',
                            help='Allows you to feed in a serial number when using numloops option.')

        args = parser.parse_args()
        return args

    def main_loop(self):
        args = self.parse_arguments()

        # FIRST THINGS FIRST: Figure out our station type
        # keep init of all the station config values up here
        # to make it clear which settings are coming in from there.
        station_num = self.station_config.STATION_NUMBER
        station_id = ("%s-%d" % (self.station_config.STATION_TYPE, station_num))
        window_title = "Oculus HWTE " + station_id

        # GUI setup
        big_font = "helvetica 18"
        little_font = "helvetica 12"

        ## root window ##
        self.root = tk.Tk()
        self.root.title(window_title)

        self._prompt = tk.Label(self.root, font=big_font, height=3)
        self._prompt.config(text="Scan or type DUT Serial Number:")
        self._prompt.pack(pady=10)

        ## serial number entry box, <Return> here starts the testing process ##
        self._sn_entry = tk.Entry(self.root, font=big_font)
        self._sn_entry.pack(pady=20)
        self._sn_entry.bind('<Return>', self.on_sn_enter)

        ## status console (also goes to Debug Log) ##
        self._cons = utils.gui_utils.StatusConsoleText(self.root, font=little_font, relief='sunken',
                                                         bd=5, state='disabled')
        self._cons.set_bg("grey")
        self._cons.pack()

        ## workorder label  ##
        if self.station_config.USE_WORKORDER_ENTRY:
            self.work_order_label = tk.Label(self.root, font=little_font)
            self.work_order_label.config(text="workorder: " + self.g_workorder)
            self.work_order_label.pack()
            self._work_order_edit_button = tk.Button(self.root, font=little_font,
                                                     text='Change Work Order', command=self.update_workorder_display)
            self._work_order_edit_button.pack()

        try:
            self._operator_interface = operator_interface.OperatorInterface(self.station_config, self._cons,
                                                                            self._prompt, log_to_file=True)
        except:
            messagebox.showerror(title="Station Config Error", message=("Can't initialize operator interface!\n"))
            raise

        self._g_num_loops_completed = 0
        self._g_num_passing_loops = 0
        self._g_loop_sn = None
        if args.numloops is not None:
            self._g_target_num_loops = args.numloops
            self._loop_label = tk.Label(self.root, font=little_font)
            self._loop_label.pack()
            if args.serialnum is not None:
                self._operator_interface.print_to_console ("using serial number %s" % args.serialnum)
                self._g_loop_sn = args.serialnum
                self._sn_entry.insert(tk.END, self._g_loop_sn)
        self.update_loop_counter()

        # version info
        version_file = "VERSION.TXT"
        version_dir = os.getcwd()
        version_filename = os.path.join(version_dir, version_file)
        if os.path.isfile(version_filename):
            version_fileobj = open(version_filename, "r")
            version_data = version_fileobj.read()
            self._version_info = tk.Label(self.root, font=little_font, height=2)
            self._version_info.config(text=version_data)
            self._version_info.pack(pady=5)

        self._sn_entry['state'] = 'readonly'
        if self.station_config.USE_WORKORDER_ENTRY:
            self.update_workorder_display()
        if self.station_config.STATION_NUMBER == 0:
            self.update_stationtype_display()
        else:
            self.create_station()
            self.setguistate_initializetester(self.station)

        self.root.wm_protocol("WM_DELETE_WINDOW", self.on_app_exit)
        tk.mainloop()

    def update_workorder_display(self):
        sub_window_title = "Edit Work Order"
        UpdateWorkorderDialog(self, self.root, sub_window_title)

    def update_stationtype_display(self):
        sub_window_title = "Scan Station Label"
        UpdateStationIdDialog(self, self.root, sub_window_title)


class UpdateWorkorderDialog(utils.gui_utils.Dialog):
    def __init__(self, factory_gui, parent, title):
        utils.gui_utils.Dialog.__init__(self, parent, title)
        self._gui = factory_gui

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        tk.Label(master, text="Workorder:").grid(row=0)
        self.entry = tk.Entry(master)
        self.entry.grid(row=0, column=1)
        return self.entry  # initial focus

    def apply(self):
        self._gui.g_workorder = self.entry.get()
        self._gui.work_order_label.config(text=("workorder: " + self._gui.g_workorder))
        self._gui.work_order_label.update()

    def validate(self):
        return 1


class UpdateStationIdDialog(utils.gui_utils.Dialog):
    def __init__(self, factory_gui, parent, title):
        utils.gui_utils.Dialog.__init__(self, parent, title)
        self._gui = factory_gui
        self._station_id = None
        self._station_id_pattern = r'[\\/:*?"<>|\r\n]+'

    def body(self, master):
        tk.Label(master, text="Station ID:").grid(row=0)
        self.entry = tk.Entry(master)
        self.entry.grid(row=0, column=1)
        return self.entry  # initial focus

    def apply(self):
        if self._gui.station_config.FACEBOOK_IT_ENABLED:
            self._gui.root.title("Oculus HWTE " + self._station_id)
        else:
            self._gui.root.title("Oculus HWTE " + self._station_id + " - FACEBOOK IT DISABLED!!!")
        self._gui.setguistate_initializetester(self._gui.station)

    def validate(self):
        self._station_id = self.entry.get()
        try:
            if re.search(self._station_id_pattern, self._station_id, re.I|re.S):
                raise ValueError
            (self._gui.station_config.STATION_TYPE,
             self._gui.station_config.STATION_NUMBER) = re.split('-', self._station_id)
            self._gui.create_station()
            return True
        except ValueError:
            messagebox.showerror(title="Station Config Error",
                                   message=("Station ID is of the form stationId-stationNumber"))
            return False
        except test_station.test_station.TestStationError:
            messagebox.showerror(title="Station Config Error", message=("%s is not a valid station type!" %
                                                                          self._gui.station_config.STATION_TYPE))
            return False
        except:
            # raise any other weird exceptions we might get
            raise
