import marytreat
import base64
import os
from tkinter import Tk, Label, StringVar, Entry, Button


class FirstLaunchWindow(Tk):

    def __init__(self, path):
        super().__init__()
        self.title('Welcome to MaryTreat')
        self.geometry('300x230+400+300')
        padding = {'padx': 10, 'pady': 10}

        self.creds = StringVar(), StringVar(), StringVar()
        self.path = path

        Label(self, text='Enter your Tridion Docs credentials:').grid(row=0, column=0,
                                                                      columnspan=2, **padding, sticky='nsew')

        Label(self, text='Host name:').grid(row=1, column=0, **padding, sticky='nsew')
        Entry(self, textvariable=self.creds[0]).grid(row=1, column=1, **padding, sticky='nsew')

        Label(self, text='User name:').grid(row=2, column=0, **padding, sticky='nsew')
        Entry(self, textvariable=self.creds[1]).grid(row=2, column=1, **padding, sticky='nsew')

        Label(self, text='Password:').grid(row=3, column=0, **padding, sticky='nsew')
        Entry(self, textvariable=self.creds[2], show='*').grid(row=3, column=1, **padding, sticky='nsew')

        Button(self, text='Exit', command=exit).grid(row=4, column=0, **padding, sticky='nsew')
        Button(self, text='OK', command=self.save_credentials).grid(row=4, column=1, **padding, sticky='nsew')

    def save_credentials(self):
        if all(self.creds):
            with open(self.path, 'wb') as f:
                f.write(base64.b64encode('\n'.join([c.get() for c in self.creds]).encode('utf-8')))
        self.destroy()


p = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                base64.b64decode('c2VjcmV0LnB5').decode("utf-8"))
if not os.path.exists(p):
    FirstLaunchWindow(p).mainloop()
