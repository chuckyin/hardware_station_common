__author__ = 'chuckyin'

# pylint: disable=R0901
# pylint: disable=R0904
# pylint: disable=R0924
# pylint: disable=C0103
# pylint: disable=W0613

import tkinter as tk
#import tkMessageBox
from tkinter import messagebox
import clr
# clr.AddReference('WPFMessageBox')
# clr.AddReference('Hsc')
from UIDep import UIDepHelper
for c in UIDepHelper.all_depencies():
    clr.AddReference(c)
from MessageBoxUtils import WPFMessageBox
from Hsc import ImageDisplayBox as imgDispBox

class MessageBox(object):
    @classmethod
    def warning(cls, title=None, msg=None, msgbtn=0):
        return WPFMessageBox.Show(msg, title, msgbtn, 48)

    @classmethod
    def error(cls, title=None, msg=None, msgbtn=0):
        return WPFMessageBox.Show(msg, title, msgbtn, 16)

    @classmethod
    def info(cls, title=None, msg=None, msgbtn=0):
        return WPFMessageBox.Show(msg, title, msgbtn, 64)


class ImageDisplayBox(object):
    @classmethod
    def display(cls, image_file_name):
        img_box = imgDispBox()
        img_box.Show()
        img_box.DisplayImage(image_file_name)
