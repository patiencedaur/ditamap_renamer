from tkinter import *
from tkinter import Entry
from utils.constants import Constants

padding = Constants.PADDING.value


class SelectPartType(LabelFrame):

    def __init__(self, master):
        super().__init__(master, text='Type')
        self.part_type = StringVar()

        dfe = Radiobutton(self, text='DFE', variable=self.part_type, value='dfe')
        dfe.grid(row=0, column=0, **padding, sticky=NSEW)
        press = Radiobutton(self, text='Press', variable=self.part_type, value='press')
        press.grid(row=0, column=1, **padding, sticky=NSEW)

        self.part_type.set('press')

    def get_part_type(self):
        return self.part_type.get()


class SelectSeries(LabelFrame):

    def __init__(self, master):
        super().__init__(master, text='Series')
        self.series = StringVar()
        buttons = ['common', '3', '4', '5', '6']
        for button in buttons:
            btn = Radiobutton(self, text=button, variable=self.series, value=button)
            btn.grid(row=0, column=buttons.index(button)+2, sticky=EW, **padding)
        self.series.set('common')

    def get_series(self):
        print(self.series.get())
        return self.series.get()


class SearchPartNumber(Frame):

    def __init__(self, master):
        super().__init__(master)
        self.search_query = StringVar()

        description = Label(self, text='Search project by part number:', anchor=W)
        description.grid(row=0, column=0, sticky=EW)

        query_field = Entry(self, textvariable=self.search_query)
        query_field.grid(row=1, column=0, columnspan=3, **padding, sticky=EW)

        search_button = Button(self, text='Search', command=self.get_search_result)
        search_button.grid(row=1, column=3, **padding, sticky=EW)

        select_part_type = SelectPartType(self)
        select_part_type.grid(row=2, column=0, **padding, sticky=EW)

        select_series = SelectSeries(self)
        select_series.grid(row=2, column=1, columnspan=3, **padding, sticky=EW)

    def get_search_result(self):
        pass # found = tridionclient.SearchRepository.by_part_number()


class ServerActionsTab(PanedWindow):

    def __init__(self, master):
        super().__init__(master, orient=VERTICAL)

        search = SearchPartNumber(self)
        self.add(search, **padding)

        server_buttons = ServerActionsButtons(self)
        self.add(server_buttons, **padding)


class ServerActionsButtons(Frame):

    def __init__(self, master):
        super().__init__(master)
        button_cheetah_migration = Button(self, text='Complete Cheetah migration')
        button_cheetah_migration.grid(row=0, column=0, **padding, sticky=EW)

        button_check_titles_and_sd = Button(self, text='Check titles and shortdescs')
        button_check_titles_and_sd.grid(row=0, column=1, **padding, sticky=EW)

        button_submaps = Button(self, text='Configure submaps...')
        button_submaps.grid(row=0, column=2, **padding, sticky=EW)

        button_check_tags = Button(self, text='Check Dynamic Delivery tags')
        button_check_tags.grid(row=1, column=1, **padding, sticky=EW)

        button_hpi_pdf = Button(self, text='HPI PDF publication...')
        button_hpi_pdf.grid(row=1, column=2, **padding, sticky=EW)


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
