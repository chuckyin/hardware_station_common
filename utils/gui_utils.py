__author__ = 'chuckyin'

# pylint: disable=R0901
# pylint: disable=R0904
# pylint: disable=R0924
# pylint: disable=C0103
# pylint: disable=W0613

import Tkinter as tk
import tkMessageBox


######  GUI Utilites ######

class StatusConsoleText(tk.Text):
    def print_msg(self, msg):
        self.config(state='normal')
        self.insert(tk.END, msg)
        self.see(tk.END)
        self.config(state='disabled')
        self.update()

    def set_bg(self, color):
        self.config(state='normal')
        self.config(bg=color)
        self.config(state='disabled')

    def clear(self):
        self.config(state='normal')
        self.delete("1.0", tk.END)
        self.config(state='disabled')


class MessageBox(object):
    @classmethod
    def warning(cls, title=None, msg=None):
        tkMessageBox.showwarning(title, msg)

    @classmethod
    def error(cls, title=None, msg=None):
        tkMessageBox.showerror(title, msg)

    @classmethod
    def info(cls, title=None, msg=None):
        tkMessageBox.showinfo(title, msg)


class ImageDisplayBox(object):  # pylint: disable=R0903
    @classmethod
    def display(cls, image_file_name):
        top = tk.Toplevel()
        top.title(image_file_name)
        button = tk.Button(top, text="OK", command=top.destroy)
        button.pack()
        canvas = tk.Canvas(top, width=1600, height=1200)
        tkimage = tk.PhotoImage(file=image_file_name)
        canvas.create_image((800, 600), image=tkimage)
        canvas.img = tkimage
        canvas.pack()


class Dialog(tk.Toplevel):
    def __init__(self, parent, title=None):
        tk.Toplevel.__init__(self, parent)
        self.transient(parent)
        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        self.buttonbox()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.initial_focus.focus_set()

    # construction hooks
    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden

        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = tk.Frame(self)

        w = tk.Button(box, text="OK", width=10, command=self.ok_button, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok_button)
        self.bind("<Escape>", self.cancel)

        box.pack()

    #
    # standard button semantics

    def ok_button(self, event=None):  # event is needed because it's a callback to tk.Button.  overriding W0613

        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):
        if self:
            pass  # hacky way to shut lint up about how this could be static.
        return 1  # override

    def apply(self):

        pass  # override
