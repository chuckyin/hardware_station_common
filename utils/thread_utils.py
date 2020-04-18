__author__ = 'chuckyin'

#!/usr/bin/env python

# pylint: disable=R0902

import threading
import time


class TimeoutThread(threading.Thread):
    def __init__(self, timeout_s, timeout_message='Timed Out!', timeout_action=None, timeout_action_parameter=None):
        self.timeout_s = timeout_s
        threading.Thread.__init__(self)
        self.exit_requested = False
        self.elapsed_ms = 0.0
        self.poll_interval_ms = 100  # could be set externally.
        self.timeout_message = timeout_message
        self.show_debug = False
        self.timeout_action = timeout_action  # allow caller to register an error action that they want us to use.
        self.timeout_action_parameter = timeout_action_parameter

    def stop(self):
        self.exit_requested = True

    def run(self):
        # start the timer
        while ((self.elapsed_ms / 1000) < self.timeout_s):
            if self.exit_requested:
                return
            time.sleep(float(self.poll_interval_ms) / float(1000))
            self.elapsed_ms += self.poll_interval_ms
            if (self.elapsed_ms % 1000) == 0:
                tick = self.timeout_s - (self.elapsed_ms / 1000)
                if self.show_debug:
                    print ("[%d]" % tick)
        print (self.timeout_message)
        if self.timeout_action:
            self.timeout_action(self.timeout_action_parameter)
        return


def main():
    thread = TimeoutThread(6)
    thread.start()

    console_input = None
    while console_input != 'a':
        console_input = raw_input("\nType the letter a.\n")

    print ("Finished normal execution path.  Stopping the timer thread...")
    thread.stop()

if __name__ == '__main__':
    main()
