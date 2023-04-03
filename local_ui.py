from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
import subprocess
from local import *


class MainFrame(ttk.Frame):
    pass


class App(Tk):

    def __init__(self) -> None:
        super().__init__()
        self.ditamap: LocalMap | None = None
        self.title('MaryTreat - Cheetah-to-DITA Conversion Step No. 1.5')
        self.ditamap_var = StringVar()  # something used by Tkinter, here acts as a buffer for ditamap path
        self.ditamap_var.trace('w', self.turn_on_buttons)
        self.padding = {'padx': 5, 'pady': 5}
        self.no_images = True

        button_file = Button(self, text='Select map...', command=self.get_ditamap_name)
        button_file.grid(row=0, column=0, sticky=NW, **self.padding)

        self.target_file = Entry(self, textvariable=self.ditamap_var, width=60, bg='white', relief=SUNKEN, bd=4,
                                 justify=LEFT)
        self.target_file.grid(row=0, column=1, sticky=NW, **self.padding, columnspan=2)

        self.button_rename = Button(self,
                                    text='Rename folder items',
                                    command=self.call_rename_topics,
                                    state=DISABLED)
        self.button_rename.grid(row=1, column=1, sticky=EW, **self.padding)

        self.button_mass_edit = Button(self,
                                       text='Mass edit typical shortdescs',
                                       command=self.call_mass_edit,
                                       state=DISABLED)
        self.button_mass_edit.grid(row=1, column=2, sticky=EW, **self.padding)

        self.button_view_shortdescs = Button(self,
                                             text='Edit missing shortdescs',
                                             command=self.call_get_problematic_files,
                                             state=DISABLED)
        self.button_view_shortdescs.grid(row=2, column=1, sticky=EW, **self.padding)

        self.button_edit_image_names = Button(self,
                                              text='Mass edit image names',
                                              command=self.create_image_prefix_prompt_window,
                                              state=DISABLED)
        self.button_edit_image_names.grid(row=2, column=2, sticky=EW, **self.padding)

        button_exit = Button(self, text='Exit', command=self.exit)
        button_exit.grid(row=2, column=0, sticky=SW, **self.padding)

    def exit(self):
        self.destroy()
        exit()

    def get_ditamap_name(self):
        """
        Show a file selection dialog. Remember the file that was selected.
        """
        file = filedialog.askopenfilename(filetypes=[('DITA maps', '.ditamap')])
        if file:
            self.ditamap_var.set(os.path.abspath(file))
            print('var:', self.ditamap_var.get())
            self.ditamap = LocalMap(self.ditamap_var.get())
            print(self.ditamap.image_folder)
            if len(self.ditamap.images) > 0:
                self.no_images = False
            self.turn_on_buttons()

    def turn_on_buttons(self, *args):
        """
        Every time the Tkinter StringVar is changed, the DITA map path also gets changed.
        """
        if self.ditamap_var:
            self.button_rename['state'] = NORMAL
            self.button_mass_edit['state'] = NORMAL
            self.button_view_shortdescs['state'] = NORMAL
            if self.no_images is False:
                self.button_edit_image_names['state'] = NORMAL
            else:
                self.button_edit_image_names['state'] = DISABLED

    def create_image_prefix_prompt_window(self) -> None:
        new_window = ImageNamesWindow(self.ditamap)

    # new_window.top.call('wm', 'attributes', '.', '-topmost', 'true')

    '''
    Calls to 'backend' functions that actually modify files.
    '''

    def call_rename_topics(self, *args):
        if self.ditamap:
            number_renamed_topics = self.ditamap.rename_topics()
            rename_msg = 'Processed %s topics in map folder.' % str(number_renamed_topics)
            messagebox.showinfo(title='Renamed files', message=rename_msg)

    def call_mass_edit(self, *args):
        if self.ditamap:
            processed_files = self.ditamap.mass_edit()
            if len(processed_files) > 0:
                mass_edit_msg = 'Edited shortdescs in files:\n\n' + '\n'.join([f for f in processed_files])
            else:
                mass_edit_msg = 'Nothing to rename automatically.'
            messagebox.showinfo(title='Mass edited files', message=mass_edit_msg)

    def call_get_problematic_files(self, *args):
        if self.ditamap:
            new_window = MissingItemsWindow(self.ditamap)


class ImageNamesWindow:

    def __init__(self, ditamap):
        self.image_prefix_var = StringVar()
        self.ditamap = ditamap
        self.padding = {'padx': 5, 'pady': 5}

        self.top = Toplevel()
        self.top.title = 'Mass edit image names'

        label_top_text = 'Enter a prefix associated with the document subject.'
        prompt_label_top = Label(self.top, justify=LEFT,
                                 text=label_top_text)
        prompt_label_top.grid(row=0, column=0, sticky=NW, **self.padding)

        label_bottom_text = '(Example: \'inkcab\' for a document about the ink cabinet\nwill produce image names' \
                            ' like \'img_inkcab_***\' and \'scr_inkcab_\'.)'
        prompt_label_bottom = Label(self.top, justify=LEFT,
                                    text=label_bottom_text)
        prompt_label_bottom.grid(row=1, column=0, sticky=NW, **self.padding)

        prompt_entry = Entry(self.top, textvariable=self.image_prefix_var, width=60, bg='white', relief=SUNKEN, bd=4,
                             justify=LEFT)
        prompt_entry.grid(row=2, column=0, sticky=EW, **self.padding)

        save_image_prefix = Button(self.top,
                                   text='OK',
                                   command=self.call_edit_image_names)
        save_image_prefix.grid(row=2, column=1, sticky=EW, **self.padding)

    def call_edit_image_names(self):
        """
        Show the image prefix dialog. Remember the prefix.
        """
        if self.ditamap:
            prefix = self.image_prefix_var.get()
            self.ditamap.edit_image_names(prefix)
            messagebox.showinfo(title='Mass edit image names', message='Images renamed.')
            self.top.destroy()


class MissingItemsWindow(Tk):

    def __init__(self, ditamap):

        super().__init__()

        self.ditamap = ditamap
        self.padding = {'padx': 7, 'pady': 7}

        self.title('Edit titles and shortdescs')
        self.resizable(True, True)
        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()
        # self.geometry('%dx%d' % (self.width/2, self.height/2))

        self.table_frame = None
        self.table = None
        self.open_topic = None
        self.topic_text = None
        self.title_button = None
        self.shortdesc_button = None
        self.open_button = None
        self.title_field = None
        self.shortdesc_field = None
        self.save_title_btn = None
        self.save_shortdesc_btn = None
        self.title_var = None
        self.shortdesc_var = None

        self.create_table_frame()
        self.create_text_frame()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def create_table_frame(self):

        self.table_frame = Frame(self)
        # self.table_frame.pack(fill='both', expand=True, side=LEFT)
        self.table_frame.grid(row=0, column=0, sticky=NS)

        label = Label(self.table_frame, justify=LEFT, text='Double-click a file to edit.')
        label.grid(row=0, column=0, sticky=EW, **self.padding)

        refresh = Button(self.table_frame, text='Refresh', command=self.refresh_table)
        refresh.grid(row=0, column=0, sticky=EW, **self.padding)

        save_files = Button(self.table_frame, text='Save list to file', command=self.save_file_list)
        save_files.grid(row=0, column=1, sticky=EW, **self.padding)

        self.table = self.create_table()
        self.table.grid(row=1, column=0, columnspan=4, sticky=NS, **self.padding)
        self.fill_table()

    def create_table(self):

        columns = ['title', 'shortdesc', 'draft']
        table = ttk.Treeview(
            self.table_frame,
            columns=columns,
            show='tree headings',
            padding='10 10',
            height=25,
            selectmode='browse')

        table.heading('title', text='Title?')
        table.heading('shortdesc', text='Shortdesc?')
        table.heading('draft', text='Draft comment?')

        # table.column('title', minwidth=100, width=200, anchor=W)

        for column in columns[2:]:
            table.column(column, minwidth=30, width=100, anchor=CENTER)

        scrollbar = Scrollbar(self.table_frame, orient=VERTICAL, command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=4, sticky=NS)

        table.tag_configure('greyed_out', foreground='grey')

        table.tag_bind('')
        table.bind('<<TreeviewSelect>>', self.item_selected)
        table.bind('<<TreeviewOpen>>', self.c_topic_open)
        table.bind('<<Treeview.Close>>', self.c_topic_close)

        return table

    def item_selected(self, event):
        item = self.table.focus()
        for topic in self.ditamap.topics:
            if topic.name == self.table.item(item, 'text'):
                self.open_topic = topic
                self.fill_text_frame(self.open_topic)

    def c_topic_open(self, event):
        item = self.table.focus()
        for topic in self.ditamap.topics:
            if topic.name == self.table.item(item, 'text') and len(topic.children) > 0:
                self.table.item(item, open=True)

    def c_topic_close(self, event):
        item = self.table.focus()
        self.table.item(item, open=False)

    def fill_table(self):

        self.ditamap.refresh()
        pfiles = self.ditamap.get_problematic_files()

        def create_table_row(*args):
            topic = args[0]
            parent_id = ''
            tags = ''
            if len(args) == 2:
                parent_id = args[1]
                if topic not in pfiles:
                    tags = 'greyed_out'
            if topic in pfiles:
                pfiles.remove(topic)
            content = topic.content
            has_title = '-' if content.title_missing() else content.title_tag.text
            has_shortdesc = '-' if content.shortdesc_missing() else content.shortdesc_tag.text
            has_draft_comments = 'Yes' if len(content.draft_comments) > 0 else ''
            topic_id = self.table.insert(parent_id, END, text=topic.name, open=False, tags=tags,
                                         values=(has_title, has_shortdesc, has_draft_comments))
            if len(topic.children) > 0:
                for child in topic.children:
                    create_table_row(child, topic_id)
            return topic_id

        while pfiles:
            p = pfiles[0]
            create_table_row(p)
        self.focusmodel()

    def refresh_table(self):
        for item in self.table.get_children():
            self.table.delete(item)
        self.fill_table()

    def save_file_list(self):
        status_name = 'status_' + self.ditamap.basename + '.txt'
        status_path = os.path.join(self.ditamap.folder, status_name)
        if os.path.exists(status_path):
            open(status_path, 'w').close()  # clear the contents
        with open(status_path, 'a') as status:
            status.write('Edit shortdescs in the following files:\n\n')
            for f in self.ditamap.get_problematic_files():
                status.write(f.path + '\n')
        save_filelist_msg = 'Wrote to file ' + status_path + '. Press OK to close the window.'
        messagebox.showinfo(title='Wrote to file', message=save_filelist_msg)

    def create_text_frame(self):
        self.file_frame = Frame(self)
        self.file_frame.grid(row=0, column=1, sticky=EW)

        self.title_button = Button(self.file_frame, text='Edit title',
                                   command=self.show_edit_title, state=DISABLED)
        self.title_button.grid(row=0, column=0, sticky=EW)

        self.shortdesc_button = Button(self.file_frame, text='Edit shortdesc',
                                       command=self.show_edit_shortdesc, state=DISABLED)
        self.shortdesc_button.grid(row=0, column=1, sticky=EW)

        self.open_button = Button(self.file_frame, text='Open in Notepad', command=self.open_simple, state=DISABLED)
        self.open_button.grid(row=0, column=2, sticky=EW)

        self.topic_text = Text(self.file_frame, width=50, height=25, wrap='word')
        self.topic_text.grid(row=2, column=0, columnspan=3, sticky=NSEW, **self.padding)
        self.topic_text.insert(END, 'Click a file to preview.')
        self.topic_text.config(state=DISABLED)

        scrollbar = Scrollbar(self.file_frame)
        scrollbar.grid(row=1, column=3, sticky=NS)
        self.topic_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.topic_text.yview)

    def fill_text_frame(self, topic):
        self.topic_text.config(state=NORMAL)
        self.topic_text.delete('1.0', END)
        self.topic_text.tag_configure('highlight', background='#AA66AA')
        content = topic.content
        for elem in content.root.iter():
            text = (elem.text.strip() + '\n') if elem.text is not None else ''
            title_not_found = (elem.tag == 'title' and content.title_missing())
            shortdesc_not_found = (elem.tag == 'shortdesc' and content.shortdesc_missing())
            draft_comment_found = (elem.tag == 'draft-comment')
            if title_not_found or shortdesc_not_found or draft_comment_found:
                self.topic_text.insert(END, text, 'highlight')
            else:
                self.topic_text.insert(END, text)
        self.topic_text.config(state=DISABLED)

        self.title_button.config(state=NORMAL)
        self.shortdesc_button.config(state=NORMAL)
        self.open_button.config(state=NORMAL)

        self.title_var = StringVar(self, topic.content.title_tag.text)
        self.shortdesc_var = StringVar(self, topic.content.shortdesc_tag.text)

    def show_edit_title(self):
        self.title_field = Entry(self.file_frame, textvariable=self.title_var)
        self.title_field.grid(row=1, column=1, sticky=EW, **self.padding)

        self.title_label = Label(self.file_frame, text='Title:')
        self.title_label.grid(row=1, column=0, sticky=EW)

        self.save_title_btn = Button(self.file_frame, text='OK', command=self.save_title)
        self.save_title_btn.grid(row=1, column=2, sticky=EW)

    def show_edit_shortdesc(self):
        self.shortdesc_var.set(self.open_topic.content.shortdesc_tag.text)

        self.shortdesc_label = Label(self.file_frame, text='Shortdesc:')
        self.shortdesc_label.grid(row=1, column=0, sticky=EW)

        self.shortdesc_field = Entry(self.file_frame, textvariable=self.shortdesc_var)
        self.shortdesc_field.grid(row=1, column=1, sticky=EW, **self.padding)

        self.save_shortdesc_btn = Button(self.file_frame, text='OK', command=self.save_shortdesc)
        self.save_shortdesc_btn.grid(row=1, column=2, sticky=EW)

    def save_title(self):
        new_title = self.title_var.get()
        self.open_topic.set_title(new_title)
        self.fill_text_frame(self.open_topic)
        self.title_label.grid_forget()
        self.title_field.grid_forget()
        self.save_title_btn.grid_forget()

    def save_shortdesc(self):
        new_shortdesc = self.shortdesc_var.get()
        self.open_topic.set_shortdesc(new_shortdesc)
        self.fill_text_frame(self.open_topic)
        self.shortdesc_label.grid_forget()
        self.shortdesc_field.grid_forget()
        self.save_shortdesc_btn.grid_forget()

    def open_simple(self):
        self.attributes('-topmost', False)
        subprocess.Popen(['notepad.exe', self.open_topic.path])
