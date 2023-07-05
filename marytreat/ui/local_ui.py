from queue import Queue, Empty
from subprocess import Popen
from tkinter import Button, Label, Frame, PanedWindow, Entry, StringVar, Scrollbar, Text, Toplevel, Tk, END
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from marytreat.core.constants import Constants
from marytreat.core import process_word
import marytreat.core.local as l
from marytreat.core.rename_flare_images import RenameImageFile
from marytreat.core.threaded import ThreadedLocalMapFactory, ThreadedLocalTopicRenamer
from marytreat.ui.utils import MaryProgressBar, get_icon, position_window
from marytreat.core.mary_debug import logger

padding = Constants.PADDING.value


class LocalTab(PanedWindow):

    def __init__(self, master) -> None:
        super().__init__(master, orient='vertical')

        step_one_and_a_half = LocalMapProcessing(self)
        self.add(step_one_and_a_half, **padding)

        flare_image_renamer = RenameImageFile(self)
        self.add(flare_image_renamer, **padding)


class LocalMapProcessing(ttk.LabelFrame):

    def __init__(self, master) -> None:
        super().__init__(master, text='Process a local DITA project')
        self.ditamap: l.LocalMap | None = None
        self.ditamap_var = StringVar()  # something used by Tkinter, here acts as a buffer for ditamap path
        self.ditamap_var.trace('w', self.turn_on_buttons)
        self.padding = l.Constants.PADDING.value
        self.no_images = True

        self.q = Queue()
        self.pb = MaryProgressBar()

        button_file = Button(self, text='Select map...', command=self.call_select_map)
        button_file.grid(row=0, column=0, sticky='nw', **self.padding)

        self.target_file = Entry(self, textvariable=self.ditamap_var, width=60, bd=4, justify='left')
        self.target_file.grid(row=0, column=1, sticky='nsew', **self.padding, columnspan=2)

        self.button_rename = Button(self,
                                    text='Rename folder items',
                                    command=self.call_rename_topics,
                                    state='disabled')
        self.button_rename.grid(row=1, column=1, sticky='ew', **self.padding)

        self.button_mass_edit = Button(self,
                                       text='Mass edit typical shortdescs',
                                       command=self.call_mass_edit,
                                       state='disabled')
        self.button_mass_edit.grid(row=1, column=2, sticky='ew', **self.padding)

        self.button_view_shortdescs = Button(self,
                                             text='Edit missing shortdescs',
                                             command=self.call_get_problematic_files,
                                             state='disabled')
        self.button_view_shortdescs.grid(row=2, column=1, sticky='ew', **self.padding)

        self.button_edit_image_names = Button(self,
                                              text='Mass edit image names',
                                              command=self.create_image_prefix_prompt_window,
                                              state='disabled')
        self.button_edit_image_names.grid(row=2, column=2, sticky='ew', **self.padding)

    def call_select_map(self):
        """
        Show a file selection dialog. Remember the file that was selected.
        """
        file = filedialog.askopenfilename(filetypes=[('DITA maps', '.ditamap')])
        if not file:
            return
        do_process_map = messagebox.askokcancel('Map processing',
                                                'The map ' + l.os.path.basename(file) + ' will be pre-processed.\n\n' +
                                                'If the project was derived from a Word file, ' +
                                                'basic formatting will be added, ' +
                                                'but you will still need to clean up the topics afterwards')
        if do_process_map:
            self.ditamap_var.set(l.os.path.abspath(file))
            l.logger.debug('ditamap_var: ' + self.ditamap_var.get())
            self.pb.start()
            t = ThreadedLocalMapFactory(l.os.path.abspath(file), self.q)
            t.start()
            self.after(100, self.check_queue_for_map)

    def check_queue_for_map(self):
        try:
            self.ditamap = self.q.get_nowait()
            l.logger.debug(self.ditamap.image_folder)
            if len(self.ditamap.images) > 0:
                self.no_images = False
            if self.ditamap.source == 'word':
                self.ditamap.cast_topics_from_word()
                process_word.after_conversion(self.ditamap.folder)
            self.pb.stopandhide()
            self.turn_on_buttons()
        except Empty:
            self.after(100, self.check_queue_for_map)

    def turn_on_buttons(self, *args):
        """
        Every time the Tkinter StringVar is changed, the DITA map path also gets changed.
        """
        if self.ditamap:
            self.button_rename['state'] = 'normal'
            self.button_mass_edit['state'] = 'normal'
            self.button_view_shortdescs['state'] = 'normal'
            if self.no_images is False:
                self.button_edit_image_names['state'] = 'normal'
            else:
                self.button_edit_image_names['state'] = 'normal'

    def create_image_prefix_prompt_window(self) -> None:
        ImageNamesWindow(self.ditamap)

    '''
    Calls to 'backend' functions that actually modify files.
    '''

    def call_rename_topics(self, *args):
        if self.ditamap:
            self.pb.start()
            t = ThreadedLocalTopicRenamer(self.ditamap, self.q)
            t.start()
            self.after(100, self.check_queue_for_renamed_topics)

    def check_queue_for_renamed_topics(self):
        try:
            number_renamed_topics = self.q.get_nowait()
            if number_renamed_topics and number_renamed_topics != -1:
                self.pb.stopandhide()
                rename_msg = 'Processed %s topics in map folder.' % str(number_renamed_topics)
                messagebox.showinfo(title='Renamed files', message=rename_msg)
        except Empty:
            self.after(100, self.check_queue_for_renamed_topics)
        except Exception as e:
            self.pb.stopandhide()
            self.q.put(-1)
            logger.error(e)

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
        position_window(self.top, 440, 120)
        self.top.iconbitmap(get_icon())
        self.top.title = 'Mass edit image names'

        label_top_text = 'Enter a prefix associated with the document subject.'
        prompt_label_top = Label(self.top, justify='left',
                                 text=label_top_text)
        prompt_label_top.grid(row=0, column=0, sticky='nw', **self.padding)

        label_bottom_text = '(Example: \'inkcab\' for a document about the ink cabinet\nwill produce image names' \
                            ' like \'img_inkcab_***\' and \'scr_inkcab_\'.)'
        prompt_label_bottom = Label(self.top, justify='left',
                                    text=label_bottom_text)
        prompt_label_bottom.grid(row=1, column=0, sticky='nw', **self.padding)

        prompt_entry = Entry(self.top, textvariable=self.image_prefix_var, width=60, bg='white', relief='sunken', bd=4,
                             justify='left')
        prompt_entry.grid(row=2, column=0, sticky='nw', **self.padding)

        save_image_prefix = Button(self.top,
                                   text='OK',
                                   command=self.call_edit_image_names)
        save_image_prefix.grid(row=2, column=1, sticky='nw', **self.padding)

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
        self.iconbitmap(get_icon())
        self.state('zoomed')  # maximize window

        self.ditamap = ditamap
        self.padding = {'padx': 7, 'pady': 7}

        self.title('Edit titles and shortdescs')

        self.table_frame = None
        self.file_frame = None
        self.table = None
        self.open_topic = None
        self.topic_text = None
        self.title_label = None
        self.shortdesc_label = None
        self.title_button = None
        self.shortdesc_button = None
        self.open_button = None
        self.title_field = None
        self.shortdesc_field = None
        self.save_title_btn = None
        self.save_shortdesc_btn = None
        self.gen_shortdesc_btn = None
        self.remove_context_btn = None
        self.title_var = None
        self.shortdesc_var = None

        self.create_table_frame()
        self.create_text_frame()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def create_table_frame(self):

        self.table_frame = Frame(self)
        self.table_frame.grid(row=0, column=0, sticky='ns')

        label = Label(self.table_frame, justify='left', text='Double-click a file to edit.')
        label.grid(row=0, column=0, sticky='ew', **self.padding)

        refresh = Button(self.table_frame, text='Refresh', command=self.refresh_table)
        refresh.grid(row=0, column=0, sticky='ew', **self.padding)

        save_files = Button(self.table_frame, text='Save list to file', command=self.save_file_list)
        save_files.grid(row=0, column=1, sticky='ew', **self.padding)

        self.table = self.create_table()
        self.table.grid(row=1, column=0, columnspan=4, sticky='ns', **self.padding)
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

        for column in columns[2:]:
            table.column(column, minwidth=30, width=100, anchor='center')

        scrollbar = Scrollbar(self.table_frame, orient='vertical', command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=4, sticky='ns')

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

        def create_table_row(topic: l.LocalTopic, parent_id=''):
            tags = ''
            if parent_id != '' and topic not in pfiles:
                tags = 'greyed_out'
            if topic in pfiles:
                pfiles.remove(topic)
            content: l.XMLContent = topic.content
            if content.title_missing():
                has_title = '-'
            else:
                has_title = content.title_tag.text or ' '.join(list(content.title_tag.itertext()))
            if content.shortdesc_missing():
                has_shortdesc = '-'
            else:
                has_shortdesc = content.shortdesc_tag.text or ' '.join(list(content.shortdesc_tag.itertext()))
            has_draft_comments = 'Yes' if len(content.draft_comments) > 0 else ''
            topic_id_in_table = self.table.insert(parent_id, END, text=topic.name, open=False, tags=tags,
                                                  values=(has_title, has_shortdesc, has_draft_comments))
            if len(topic.children) > 0:
                for child in topic.children:
                    create_table_row(child, topic_id_in_table)
            return topic_id_in_table

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
        status_path = l.os.path.join(self.ditamap.folder, status_name)
        if l.os.path.exists(status_path):
            open(status_path, 'w').close()  # clear the contents
        with open(status_path, 'a') as status:
            status.write('Edit shortdescs in the following files:\n\n')
            for f in self.ditamap.get_problematic_files():
                status.write(f.path + '\n')
        save_filelist_msg = 'Wrote to file ' + status_path + '. Press OK to close the window.'
        messagebox.showinfo(title='Wrote to file', message=save_filelist_msg)

    def create_text_frame(self):
        self.file_frame = Frame(self)
        self.file_frame.grid(row=0, column=1, sticky='ew')

        self.title_button = Button(self.file_frame, text='Edit title',
                                   command=self.show_edit_title, state='disabled')
        self.title_button.grid(row=0, column=0, sticky='ew')

        self.shortdesc_button = Button(self.file_frame, text='Edit shortdesc',
                                       command=self.show_edit_shortdesc, state='disabled')
        self.shortdesc_button.grid(row=0, column=1, sticky='ew')

        self.open_button = Button(self.file_frame, text='Open in Notepad', command=self.open_simple, state='disabled')
        self.open_button.grid(row=0, column=2, sticky='ew')

        self.gen_shortdesc_btn = Button(self.file_frame, text='Generate shortdesc (task)',
                                        command=self.gen_shortdesc, state='disabled')
        self.gen_shortdesc_btn.grid(row=1, column=0, columnspan=2, sticky='ew')

        self.remove_context_btn = Button(self.file_frame, text='Remove context (task)',
                                         command=self.remove_context, state='disabled')
        self.remove_context_btn.grid(row=1, column=2, sticky='ew')

        self.topic_text = Text(self.file_frame, width=50, height=25, wrap='word')
        self.topic_text.grid(row=3, column=0, columnspan=3, sticky='nsew', **self.padding)
        self.topic_text.insert(END, 'Click a file to preview.')
        self.topic_text.config(state='disabled')

        scrollbar = Scrollbar(self.file_frame)
        scrollbar.grid(row=3, column=3, columnspan=3, sticky='nse')
        self.topic_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.topic_text.yview)

    def fill_text_frame(self, topic):
        self.topic_text.config(state='normal')
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
        self.topic_text.config(state='disabled')

        self.title_button.config(state='normal')
        self.shortdesc_button.config(state='normal')
        self.open_button.config(state='normal')
        if content.outputclass == 'procedure':
            self.gen_shortdesc_btn.config(state='normal')
            self.remove_context_btn.config(state='normal')

        self.title_var = StringVar(self, topic.content.title_tag.text)
        self.shortdesc_var = StringVar(self, topic.content.shortdesc_tag.text)

    def show_edit_title(self):
        self.title_field = Entry(self.file_frame, textvariable=self.title_var)
        self.title_field.grid(row=2, column=1, sticky='ew', **self.padding)

        self.title_label = Label(self.file_frame, text='Title:')
        self.title_label.grid(row=2, column=0, sticky='ew')

        self.save_title_btn = Button(self.file_frame, text='OK', command=self.save_title)
        self.save_title_btn.grid(row=2, column=2, sticky='ew')

    def show_edit_shortdesc(self):
        self.shortdesc_var.set(self.open_topic.content.shortdesc_tag.text)

        self.shortdesc_label = Label(self.file_frame, text='Shortdesc:')
        self.shortdesc_label.grid(row=2, column=0, sticky='ew')

        self.shortdesc_field = Entry(self.file_frame, textvariable=self.shortdesc_var)
        self.shortdesc_field.grid(row=2, column=1, sticky='ew', **self.padding)

        self.save_shortdesc_btn = Button(self.file_frame, text='OK', command=self.save_shortdesc)
        self.save_shortdesc_btn.grid(row=2, column=2, sticky='ew')

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
        Popen(['notepad.exe', self.open_topic.path])

    def gen_shortdesc(self):
        new_shortdesc = self.open_topic.content.gen_shortdesc()
        self.open_topic.set_shortdesc(new_shortdesc)
        self.fill_text_frame(self.open_topic)

    def remove_context(self):
        self.open_topic.remove_context()
        self.fill_text_frame(self.open_topic)
