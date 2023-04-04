from tkinter import *
from tkinter import Entry
from utils.constants import Constants
from utils.mary_debug import logger
from utils.tridionclient import SearchRepository, Project

padding = Constants.PADDING.value


class NarrowDownLocation(LabelFrame):

    def __init__(self, master):
        super().__init__(master, text='What to search')
        self.part_type = StringVar()

        buttons = ['3', '4', '5', '6', 'Common in Presses', 'DFE']
        for button in buttons:
            btn = Radiobutton(self, text=button, variable=self.part_type, value=button.lower(),
                              command=self.get_location_folder)
            btn.grid(row=0, column=buttons.index(button), sticky=EW, **padding)
        self.part_type.set('common in presses')

    def get_location_folder(self):
        part_type = self.part_type.get()
        logger.debug(part_type)
        if part_type:
            folder = SearchRepository.get_location(part_type)
            return folder


class SearchPartNumber(Frame):

    def __init__(self, master):
        super().__init__(master)
        self.search_query = StringVar()
        self.p_name = StringVar()
        self.p_id = StringVar()

        description = Label(self, text='Search project by part number:', anchor=W)
        description.grid(row=0, column=0, sticky=EW)

        query_field = Entry(self, textvariable=self.search_query)
        query_field.grid(row=1, column=0, columnspan=4, **padding, sticky=EW)

        search_button = Button(self, text='Search', command=self.find_project)
        search_button.grid(row=1, column=3, **padding, sticky=EW)

        self.select_part_type = NarrowDownLocation(self)
        self.select_part_type.grid(row=2, column=0, columnspan=4, **padding, sticky=EW)

    def find_project(self):
        folder = self.select_part_type.get_location_folder()
        part_no = self.search_query.get()
        logger.debug('search query: ' + part_no)
        if folder and part_no:
            result = SearchRepository.scan_folder(part_no, folder, 0)
            if result:
                self.p_name.set(result[0])
                self.p_id.set(result[1])


class ServerActionsTab(Frame):

    def __init__(self, master):
        super().__init__(master)

        search = SearchPartNumber(self)
        search.grid(row=0, column=0, columnspan=3, sticky=EW)

        button_cheetah_migration = Button(self, text='Complete project migration', state=DISABLED)
        button_cheetah_migration.grid(row=1, column=0, **padding, sticky=EW)

        button_check_titles_and_sd = Button(self, text='Check titles and shortdescs', state=DISABLED)
        button_check_titles_and_sd.grid(row=1, column=1, **padding, sticky=EW)

        button_manage_pub = Button(self, text='Manage publication...', state=DISABLED)  # submaps; mark for tagging
        button_manage_pub.grid(row=1, column=2, **padding, sticky=EW)

        button_check_tags = Button(self, text='Check Dynamic Delivery tags', state=DISABLED)
        button_check_tags.grid(row=2, column=1, **padding, sticky=EW)

        button_hpi_pdf = Button(self, text='HPI PDF publication...', state=DISABLED)
        button_hpi_pdf.grid(row=2, column=2, **padding, sticky=EW)

        self.buttons = [
            button_cheetah_migration,
            button_check_titles_and_sd,
            button_manage_pub,
            button_check_tags,
            button_hpi_pdf
        ]

        self.name_entry = search.p_name
        self.id_entry = search.p_id
        self.name_entry.trace('w', self.turn_on_buttons)

    def turn_on_buttons(self, *args):
        name = self.name_entry.get()
        if name:
            for button in self.buttons:
                button.configure(state=NORMAL)



# class ConfigureHPIPDFTab(Frame):
#
#     def __init__(self, master):
#         super().__init__(master)
#         description_text = 'Set the necessary HPI PDF parameters for publishing.'
#         description_label = Label(self, text=description_text, anchor=W)
#         description_label.grid(row=0, column=0, columnspan=5, **padding, sticky=NSEW)
#         search = SearchPartNumber(self)
#         search.grid(row=1, column=0, rowspan=4, columnspan=4, **padding, sticky=NSEW)
#         button_set_params = Button(self, text='Set parameters', command=self.call_set_params)
#         button_set_params.grid(row=1, column=5, **padding, sticky=NSEW)
#
#     def call_set_params(self):
#         pass
