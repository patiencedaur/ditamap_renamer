import os
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox

from lxml import etree

from marytreat.core.constants import Constants

padding = Constants.PADDING.value


class RenameImageFile(LabelFrame):

    def __init__(self, master):
        super().__init__(master, text='Rename images in a Flare project')
        self.project_var = StringVar()

        target_select_button = Button(self, text='Flare folder...', command=self.select_folder)
        target_select_button.grid(row=0, column=0, **padding, sticky=EW)

        target_file = Entry(self, textvariable=self.project_var, width=41)
        target_file.grid(row=0, column=1, **padding, sticky=EW)

        rename_button = Button(self, text='Rename images', command=self.call_rename_image_links)
        rename_button.grid(row=0, column=2, **padding, sticky=EW)

    def rename_image_file(self, filename, image_folder_path):
        image_extensions = ['.png', '.gif', '.jpg', '.eps', '.cdr', '.wmf']
        image_extensions += [ext.upper() for ext in image_extensions]
        if filename.endswith(tuple(image_extensions)):
            old_img_path = os.path.join(image_folder_path, filename)
            new_img_path = os.path.join(image_folder_path, 'img_' + filename)
            os.rename(old_img_path, new_img_path)
            return 'img_' + filename

    def rename_image_links(self, image_folder_path, topic_folder_path):
        if not image_folder_path or not topic_folder_path:
            return
        for image_name in os.listdir(image_folder_path):
            new_image_name = self.rename_image_file(image_name, image_folder_path)
            for topic_file in os.listdir(topic_folder_path):
                full_path = os.path.join(topic_folder_path, topic_file)
                tree = etree.parse(full_path)
                root = tree.getroot()
                for image in root.iter('img'):
                    path = image.attrib.get('src')
                    path_parts = path.split('/')
                    if path_parts[-1] == image_name:
                        new_path = path.replace(image_name, new_image_name)
                        image.set('src', new_path)
                tree.write(full_path)

    def call_rename_image_links(self):
        project_path = self.project_var.get()
        if project_path:
            image_folder = os.path.join(project_path, 'Content', 'Resources', 'Images', 'final-pics')
            topic_folder = os.path.join(project_path, 'Content', 'MyTopics')
            if os.path.exists(image_folder) and os.path.exists(topic_folder):
                self.rename_image_links(image_folder, topic_folder)
                messagebox.showinfo('Done!', 'Images renamed, links in topics updated.')

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.project_var.set(os.path.abspath(folder))
