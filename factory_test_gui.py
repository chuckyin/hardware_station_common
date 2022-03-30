__author__ = 'chuckyin'

#!/usr/bin/env python
# pylint: disable=R0902
# pylint: disable=R0904
# pylint: disable=R0924
# pylint: disable=W0201

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
import clr


clr.AddReference("PresentationFramework.Classic, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35")
clr.AddReference("PresentationCore, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35")
clr.AddReference('AgLib')
clr.AddReference('CommonServiceLocator')
clr.AddReference('ErrorHandler')
clr.AddReference('GalaSoft.MvvmLight')
clr.AddReference('GalaSoft.MvvmLight.Extras')
clr.AddReference('GalaSoft.MvvmLight.Platform')
clr.AddReference('log4net')
clr.AddReference('Newtonsoft.Json')
clr.AddReference('PresentationFramework.Aero2')
clr.AddReference('System.Windows.Interactivity')
clr.AddReference('Util')
clr.AddReference('WPFMessageBox')
clr.AddReference('Xceed.Wpf.DataGrid')
clr.AddReference('Xceed.Wpf.Toolkit')
clr.AddReference('Hsc')

from System.Windows import Application, Window
from System.Threading import Thread, ApartmentState, ThreadStart
from System import Action, Delegate

from Hsc import MainWindow, App, InputMsgBox
from System.Collections.Generic import Dictionary
from Hsc.ViewModel import ViewModelLocator, MainViewModel
from hardware_station_common.utils.gui_utils import MessageBox


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
        self._vm_locator = None
        self._vm_main_view_model = None
        self.g_workorder = ""
        self.root = None

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
            msg = "completed %d of %d loops.  %d passed" % (self._g_num_loops_completed,
                                                            self._g_target_num_loops, self._g_num_passing_loops)
            self._operator_interface.update_root_config({'Hint': msg})

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
        setup_ok = False
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
                self._vm_main_view_model.MovFocusToSn()
                setup_ok = True
            except (test_station.test_station.TestStationError, Exception) as e:
                self._operator_interface.print_to_console(f"Error Initializing Test Station {str(e)}.\n", "red")
                setup_ok = False
        if setup_ok:
            self._operator_interface.print_to_console("Initialization complete.\n")
            self._operator_interface.update_root_config({'IsEnabled': 'True'})
            self._operator_interface.print_to_console("waiting for sn\n")
            self._operator_interface.prompt("Scan or type the DUT Serial Number", 'green')

    def thread_it(self, func, *args):
        import threading
        t = threading.Thread(target=func, args=args)
        t.setDaemon(True)
        t.start()
        return t

    def test_iteration(self, serial_number):
        self._operator_interface.print_to_console("Running Test.\n")
        overall_result = False
        first_failed_test_result = None
        if self.station_config.USE_WORKORDER_ENTRY:
            self.station.workorder = self.g_workorder
        try:
            (overall_result, first_failed_test_result) = self.station.test_unit(serial_number.upper())
        except test_station.test_station.TestStationProcessControlError as e:
            msg = 'Process Control Error: Unit %s [  %s  ] ...\n' % (serial_number, e.message)
            self._operator_interface.print_to_console(msg, 'red')
            self._operator_interface.print_to_console('*******************\n')
            self._g_loop_sn = None  # cancle the loop test while error
            return
            
        except Exception as e:
            self._operator_interface.print_to_console("Test Station Error:{0}\n".format(str(e)), "red")
            self._g_loop_sn = None

        self.gui_show_result(serial_number, overall_result, first_failed_test_result)

    # def set_running_status(self, status):
    #     if Application.Current.Dispatcher.CheckAccess():
    #         self.root.IsBusy = status
    #     else:
    #         Application.Current.Dispatcher.Invoke(Action[bool](self.set_running_status), status)

    def run_test(self, serial_number):
        # self.set_running_status(True)
        self._operator_interface.update_root_config({'IsBusy': 'True'})
        self._operator_interface.print_to_console (f'SERINAL_NUMBER:{serial_number}\n')

        if self.is_looping_enabled():
            self._g_loop_sn = serial_number  # record the SN into the persistent global for next time.
        self.test_iteration(serial_number)
        while self._g_loop_sn is not None:
            time.sleep(1)
            self._operator_interface.clear_console()
            self._operator_interface.clear_test_values()
            self._operator_interface.update_root_config(
                {'FinalResult': '', 'ResultMsg': '', 'ResultMsgEx': ''})
            self.test_iteration(serial_number)
        gc.collect()

        self._operator_interface.update_root_config({'IsBusy': 'False', 'SN': ''})
        self._operator_interface.prompt('Scan or the type DUT Serial Number', 'green')
        self._vm_main_view_model.MovFocusToSn()
        # Application.Current.Dispatcher.Invoke(Action(self.reset_running_status))

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

    def on_app_exit(self, sender, e):
        if self.station is not None:
            self.station.close()
        if self._operator_interface is not None:
            self._operator_interface.close()
        ViewModelLocator.Cleanup()
        time.sleep(0.5)
        self.root.Close()

    def gui_show_result(self, serial_number, overall_result, first_failed_test_result=None):
        self._operator_interface.print_to_console('-----------------------------------\n')
        did_pass = False
        if overall_result:
            did_pass = True
            error_code = '[0]'
        else:
            if first_failed_test_result is None:
                error_code = "(unknown)"
            else:
                error_code = "{0}.{1}".format(
                    first_failed_test_result.get_unique_id(),
                    first_failed_test_result.get_error_code_as_string())

        if did_pass:
            self._operator_interface.update_root_config({
                'FinalResult': 'OK',
                'ResultMsg': ''})
            self._operator_interface.print_to_console(f'Unit {serial_number} OK\n')
        else:
            self._operator_interface.update_root_config({
                'FinalResult': 'NG',
                'ResultMsg': error_code})
            self._operator_interface.print_to_console(f'Unit {serial_number} NG, Errcode = {error_code}\n')
        self.update_loop_counter(did_pass)

    def create_station(self):
        try:
            self._operator_interface.print_to_console('Station Type: %s\n' % self.station_config.STATION_TYPE)
            self.station = self._test_station_init(self.station_config, self._operator_interface)
            station_id = (f'{self.station_config.STATION_TYPE}_{self.station_config.STATION_NUMBER}')
            self._operator_interface.update_root_config({'Title': f'Oculus HWTE {station_id}'})
        except:
            raise

    def update_workorder(self):
        self._operator_interface.update_root_config({'WorkOrder': self.g_workorder})

    @staticmethod
    def parse_arguments():
        # Arg handling
        # handle command-line args
        parser = argparse.ArgumentParser(description='GUI for Programming/Test station.')
        loop_help = 'FOR STATION VERIFICATION ONLY: number of timesto repeat the test without cycling the fixture.'
        parser.add_argument('-l', '--numloops',
                            type=int,
                            help=loop_help)

        args = parser.parse_args()
        return args

    def mu_action(self, sender, e):
        if sender == 'Browser':
            import subprocess
            subprocess.Popen(rf'explorer "{self.station_config.ROOT_DIR}"')
        elif sender == "Active":
            self.station_config.IS_STATION_ACTIVE = bool(e)
        elif sender == "WO":
            self.update_workorder_display()
        elif sender == 'Offline':
            self.station_config.FACEBOOK_IT_ENABLED = not bool(e)
        elif sender == 'AutoScan':
            self.station_config.AUTO_SCAN_CODE = bool(e)

    def start_loop(self, user_value):
        if not self.station_config.IS_STATION_ACTIVE or not self.check_free_space_ready():
            return
        try:
            self._operator_interface.clear_console()
            self._operator_interface.clear_test_values()
            self._operator_interface.update_root_config(
                {'FinalResult': '', 'Hint': '', 'ResultMsg': '', 'ResultMsgEx': ''})
            self._operator_interface.prompt('', '')

            self.station.validate_sn(user_value)
            if self.is_looping_enabled():
                self._g_num_loops_completed = 0
                self._g_num_passing_loops = 0
                self.update_loop_counter()
            self.station.is_ready()
            self.thread_it(self.run_test, user_value)
        except test_station.test_station.TestStationSerialNumberError as teststationerror:
            self._operator_interface.print_to_console(msg="%s" % str(teststationerror), color='red')
        except Exception as e:
            self._operator_interface.operator_input(msg="Exception: %s" % str(e), msg_type='error')
        finally:
            self._operator_interface.print_to_console("waiting for sn\n")
            self._g_loop_sn = None

    def _app_startup(self):
        self._vm_locator = ViewModelLocator.Instance
        self._vm_main_view_model = ViewModelLocator.Instance.Main
        self._vm_main_view_model.MuStartLoop += self.start_loop

        # version info
        init_config = {}
        version_file = "VERSION.TXT"
        version_dir = os.getcwd()
        version_filename = os.path.join(version_dir, version_file)
        if os.path.isfile(version_filename):
            version_fileobj = open(version_filename, "r")
            version_data = version_fileobj.read()
            init_config['VersionData'] = version_data
        if hasattr(self.station_config, 'SW_TITLE'):
            init_config['SwTitle'] = self.station_config.SW_TITLE
        init_config['Offline'] = str(not self.station_config.FACEBOOK_IT_ENABLED)
        init_config['Active'] = 'True'
        init_config['IsEnabled'] = 'False'
        if hasattr(self.station_config, 'Active'):
            init_config['Active'] = str(self.station_config.IS_STATION_ACTIVE)

        log_dir = os.path.join(self.station_config.ROOT_DIR, "factory-test_debug")
        self._operator_interface = operator_interface.OperatorInterface(self, self._vm_main_view_model, log_dir)

        self._operator_interface.update_root_config(init_config)

        self._vm_main_view_model.ShowWorkOrder = True if self.station_config.USE_WORKORDER_ENTRY else False
        if isinstance(self.station_config.STATION_NUMBER, int) and self.station_config.STATION_NUMBER == 0:
            self.update_stationtype_display()
        else:
            self.create_station()
            self.setguistate_initializetester(self.station)

    def AppStartUp(self, sender, e):
        try:
            self.root = MainWindow()
            self.root.Title = "Please scan test_station id !!!!"
            self.root.Show()
            self.root.MuAction += self.mu_action
            self._app_startup()
        except:
            pass

    def STAMain(self):
        app = App()
        app.Startup += self.AppStartUp
        app.Exit += self.on_app_exit
        app.Run()

    def main_loop(self):
        try:
            t = Thread(ThreadStart(self.STAMain))
            t.ApartmentState = ApartmentState.STA
            t.Start()

            args = self.parse_arguments()

            # FIRST THINGS FIRST: Figure out our station type
            # keep init of all the station config values up here
            # to make it clear which settings are coming in from there.

            self._g_num_loops_completed = 0
            self._g_num_passing_loops = 0
            self._g_loop_sn = None
            if args.numloops is not None:
                self._g_target_num_loops = args.numloops

            t.Join()
        except Exception as e:
            self._operator_interface.print_to_console(f'Exception from station : {str(e)}')

    def update_workorder_display(self):
        sub_window_title = "Edit Work Order"
        UpdateWorkorderDialog(self, self.root, sub_window_title)

    def update_stationtype_display(self):
        sub_window_title = "Scan Station Label"
        UpdateStationIdDialog(self, self.root, sub_window_title)


class UpdateWorkorderDialog(object):
    def __init__(self, factory_gui, parent, title):
        self._gui = factory_gui
        self._wo_dlg = InputMsgBox()
        self._wo_dlg.Owner = parent
        self._wo_dlg.Title = title
        self._wo_dlg.MuAction += self._workorder_dlg_action
        self._wo_dlg.Show()

    def _workorder_dlg_action(self, sender, e):
        self._gui.g_workorder = self._wo_dlg.InputText
        self._wo_dlg.Hide()
        self._gui.update_workorder()
        return 1


class UpdateStationIdDialog(object):
    def __init__(self, factory_gui, parent, title):
        self._gui = factory_gui
        self._station_id = None
        self._station_id_pattern = r'[\\/:*?"<>|\r\n]+'
        self._station_type_dlg = InputMsgBox()
        self._station_type_dlg.Owner = parent
        self._station_type_dlg.Title = title
        self._station_type_dlg.MuAction += self._station_type_dlg_action
        self._station_type_dlg.Show()

    def apply(self):
        self._gui.root.Title = f"Oculus HWTE {self._station_id}"
        self._gui.setguistate_initializetester(self._gui.station)
        self._station_type_dlg.Hide()
        if self._gui.station_config.USE_WORKORDER_ENTRY:
            self._gui.update_workorder_display()

    def _station_type_dlg_action(self, sender, e):
        self._station_id = self._station_type_dlg.InputText
        try:
            if re.search(self._station_id_pattern, self._station_id, re.I|re.S):
                raise ValueError
            (self._gui.station_config.STATION_TYPE,
             self._gui.station_config.STATION_NUMBER) = re.split('-', self._station_id)
            self._gui.create_station()
            self.apply()
            return True
        except ValueError:
            MessageBox.error(title="Station Config Error",
                             msg="Station ID is of the form stationId-stationNumber")
            return False
        except test_station.test_station.TestStationError:
            MessageBox.error(title="Station Config Error",
                             msg=f"{self._gui.station_config.STATION_TYPE} is not a valid station type!")
            return False
        except:
            # raise any other weird exceptions we might get
            raise
