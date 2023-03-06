import re
import os, sys, subprocess
import xml.etree.ElementTree as ET
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from typing import List, Any

'''
This script helps to convert DITA files in Cheetah-to-DITA projects for SDL Tridion Docs.
It automates menial tasks like renaming files or adding shortdescs.
Created for HP Indigo by Dia Daur
'''

prefixes = {
    # A prefix is an identifying letter that gets prepended to the filename, according to the style guide.
    'explanation': 'e_',
    'referenceinformation': 'r_',
    'context': 'c_',
    'procedure': 't_',
    'legalinformation': 'e_'
}

# Document type, indicated in the first content tag. Example: <task id=... outputclass="procedure">
doctypes = ['concept', 'task', 'reference']

outputclasses = {
    # Document outputclass, indicated as an attribute of the first content tag.
    # Example: <task id=... outputclass="procedure">
    'context': 'c_',
    'lpcontext': 'c_',
    'explanation': 'e_',
    'procedure': 't_',
    'referenceinformation': 'r_',
    'legalinformation': 'e_'}

dry_run = False

print("Dry run: ", dry_run)
print()

'''
Backend
'''


def file_rename(old_path, new_path):
    if os.path.exists(old_path):
        if old_path == new_path:
            print('Error, old path equal to new path:', old_path)
        if not dry_run:
            os.rename(old_path, new_path)
    else:
        print('Error, no file to rename:', old_path)


def file_delete(path):
    if os.path.exists(path):
        if not dry_run:
            os.remove(path)
    else:
        print('Error, no file to delete:', path)


def text_element(tag, text, *args, **kwargs):
    element = ET.Element(tag, *args, **kwargs)
    element.text = text
    return element


class DITAProjectFile:

    def __init__(self, file_path):
        """
        Based on file path, retrieve the containing folder and parse the file in advance.
        """
        self.path = file_path
        self.folder, self.name = os.path.split(self.path)
        self.basename, self.ext = os.path.splitext(self.name)
        self.tree = ET.parse(self.path)
        self.root = self.tree.getroot()
        self.header = self.get_header()
        self.ditamap = None  # is assigned during Pair creation
        self.parent_map = {c: p for p in self.tree.iter() for c in p}

    def __repr__(self):
        return '<DITAProjectFile: ' + self.name + self.ext + '>'

    def __eq__(self, other):
        return self.path == other.path

    def __ge__(self, other):
        return self.path >= other.path

    def __gt__(self, other):
        return self.path > other.path

    def __le__(self, other):
        return self.path <= other.path

    def __lt__(self, other):
        return self.path < other.path

    def __ne__(self, other):
        return self.path != other.path

    def __hash__(self):
        return hash(self.path)

    def __sortkey__(self):
        return self.path

    def get_header(self):
        header = ''
        if self.path:
            with open(self.path, 'r', encoding='utf8') as f:
                declaration = r'(<\?xml version="1.0" encoding="UTF-8"\?>\n)(<!DOCTYPE.*?>\n)?'
                beginning = ''
                for x in range(4):
                    beginning += str(next(f))
                # look for xml declaration or xml declaration followed by doctype declaration
                found_declaration = re.findall(declaration, beginning, re.DOTALL)
                if len(found_declaration) > 0:
                    header = ''.join(found_declaration[0])
                else:
                    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        return header

    def write(self):
        """
        Call this after all manipulations with the tree.
        """
        if not dry_run:
            self.tree.write(self.path)
            self.append_header()

    def append_header(self):
        """
        The ElementTree library, which I use to parse DITA file contents, removes the header when writing into file.
        This puts the header back into place.
        """
        if not dry_run:
            with open(self.path, 'r+', encoding='utf8') as f:
                content = f.read()
                f.seek(0, 0)
                f.write(self.header + content)

    def add_nbsp_after_table(self):
        """
        Finds the first section and appends a blank paragraph at its end.
        Adds this tag to the file: <#160;> </#160;>
        """
        for section in self.root.iter('section'):
            p = ET.SubElement(section, 'p')
            p.text = '\u00A0'
            self.write()
            break


class DITAMap(DITAProjectFile):

    def __init__(self, file_path):
        """
        Get list of topicrefs and their ish counterparts.
        """
        super().__init__(file_path)
        self.ditamap = self
        self.refresh()

    def __str__(self):
        return '<DITAMap: ' + self.name + '>'

    def __contains__(self, item):
        for pair in self.pairs:
            if item in pair:
                return True
        return False

    def refresh(self):
        self.images = self.get_images()
        self.pairs = self.get_pairs()
        self.libvar = self.get_libvar()

    def get_pairs(self):

        def initialize_pair(topicref):
            mappings = {
                'referenceinformation': 'ReferenceInformationDITATopic(topic_path, self)',
                'procedure': 'TaskDITATopic(topic_path, self)',
                'legalinformation': 'LegalInformationDITATopic(topic_path, self)',
                'lpcontext': 'ConceptDITATopic(topic_path, self)'
            }
            topic_path = os.path.join(self.folder, topicref.attrib.get('href'))
            if not os.path.exists(topic_path):
                print('Cannot create DITAProjectFile from path %s. Aborting.' % topic_path)
                sys.exit()
            oc = ET.parse(topic_path).getroot().attrib.get('outputclass')
            if oc in mappings.keys():
                topic = eval(mappings[oc])
            elif oc == 'context':
                topic = ConceptDITATopic(topic_path, self)
                children = topicref.findall('topicref')
                if len(children) > 0:
                    topic.children = [initialize_pair(child).dita for child in children]
            else:
                topic = DITATopic(topic_path, self)
            ish_path = topic_path.replace('.dita', '.3sish')
            ish = ISHFile(ish_path, self)
            pair = Pair(topic, ish)
            return pair

        pairs = []

        for topicref in self.root.iter('topicref'):
            pair = initialize_pair(topicref)
            pairs.append(pair)
        return set(pairs)

    def get_libvar(self):
        for file in os.listdir(self.folder):
            if file.startswith('v_'):
                path = os.path.join(self.folder, file)
                libvar = ISHFile(path, self)
                return libvar

    def get_images(self):
        image_list = []
        for file in os.listdir(self.folder):
            if file.endswith(('png', 'jpg', 'gif')):
                image_list.append(Image(file, self))
        return set(image_list)

    def rename_all(self):
        """
        Rename files in map folder according to their titles and the style guide.
        Tracks repeating topic titles.
        """
        old_pairs: list[Any] = [Pair(p.dita, p.ish) for p in self.pairs]
        self.rename_counter = 0
        topic_titles = {}
        for pair in self.pairs:
            if pair.dita.root.tag in doctypes:
                t = pair.dita.title.text
                if t in topic_titles:
                    topic_titles[t] += 1
                else:
                    topic_titles[t] = 1
                num_rep = topic_titles[t]
                pair.update_name(num_rep)
                self.rename_counter += 1
        print(topic_titles)

    def mass_edit(self):
        """
        Mass edit short descriptions for typical documents.
        """
        shortdescs = {
            'Revision history and confidentiality notice': 'This chapter contains a table of revisions, printing instructions, and a notice of document confidentiality.',
            'Revision history': 'Below is the history of the document revisions and a list of authors.',
            'Printing instructions': 'Follow these recommendations to achieve the best print quality.'
        }

        self.list_renamed = []
        for pair in self.pairs:
            topic = pair.dita
            if topic.title.text in shortdescs.keys() and topic.shortdesc_missing():
                shortdesc = shortdescs[topic.title.text]
                topic.set_shortdesc(shortdesc)
                self.list_renamed.append(topic.name)
                if topic.title.text == 'Printing instructions':
                    topic.add_nbsp_after_table()
            if isinstance(topic, ReferenceInformationDITATopic):
                topic.process_docdetails()

    def get_problematic_files(self):
        pfiles = [p.dita for p in self.pairs if
                  p.dita.shortdesc_missing() or p.dita.title_missing() or p.dita.has_draft_comments()]
        return sorted(pfiles)

    def edit_image_names(self, image_prefix):
        # there can be two images with different paths but identical titles
        # one image can be reference in multiple topics
        # count repeating titles and get image to topic map for purposes of renaming
        titles = {}
        image_to_topic = {}
        for pair in self.pairs:
            topic = pair.dita
            for image in topic.images:
                if image.title is not None:
                    if image.title in titles:
                        titles[image.title] += 1
                        image.temp_title = image.title + ' ' + str(titles[image.title])
                    else:
                        titles[image.title] = 1
                        image.temp_title = image.title
                topics = image_to_topic.setdefault(image, [])
                topics.append(topic)
        # give image files new names
        for i, topics in image_to_topic.items():
            new_name = i.generate_name(image_prefix)
            current_path = os.path.join(self.folder, i.href)
            new_path = os.path.join(self.folder, new_name)
            file_rename(current_path, new_path)
            # rename hrefs in topics
            for topic in topics:
                for fig in topic.root.iter('fig'):
                    for img_tag in fig.iter('image'):
                        if img_tag.attrib.get('href') == i.href:
                            print('Renaming', i.href, 'to', new_name)
                            img_tag.set('href', new_name)
                topic.write()


class DITATopic(DITAProjectFile):
    """
    Get DITA outputclass, title, and shortdesc.
    """

    def __init__(self, file_path, ditamap):
        super().__init__(file_path)
        self.ditamap = ditamap
        self.outputclass = self.root.attrib.get('outputclass')
        self.title = self.root.find('title')
        self.shortdesc = self.root.find('shortdesc')
        if self.shortdesc is None:
            self.insert_shortdesc_tag()
        self.local_links = self.root.findall('.//xref[@scope="local"]')
        self.images = self.get_images()
        self.draft_comments = self.get_draft_comments()
        self.children = []

    def __repr__(self):
        return '<DITATopic: ' + self.name + '>'

    def __contains__(self, item):
        contains = False
        if isinstance(item, Image) and item in self.images:
            contains = True
        if isinstance(item, str) and item in self.local_links:
            contains = True
        if isinstance(self, ConceptDITATopic) and isinstance(item, DITATopic) and item in self.children:
            contains = True
        return contains

    def get_images(self):
        topic_images = []
        for ditamap_image in self.ditamap.images:
            ditamap_href = ditamap_image.href
            for fig in self.root.iter('fig'):
                topic_image_title = fig.find('title')
                if fig.find('image').attrib.get('href') == ditamap_href:
                    if topic_image_title is not None:
                        ditamap_image.title = topic_image_title.text.strip()
                    topic_images.append(ditamap_image)
        return set(topic_images)

    def set_title(self, new_title):
        # New title is a string
        if self.title is not None:
            self.title.text = new_title
            self.write()

    def set_shortdesc(self, new_shortdesc):
        # New shortdesc is a string
        if self.shortdesc is None:
            self.insert_shortdesc_tag()
        else:
            self.shortdesc.text = new_shortdesc
            self.write()

    def title_missing(self):
        if self.title is None:
            return True
        return True if self.title.text is None or 'MISSING TITLE' in self.title.text else False

    def shortdesc_missing(self):
        if self.shortdesc is None:
            return True
        return True if (self.shortdesc.text is None
                        or self.shortdesc.text == ''
                        or 'SHORT DESCRIPTION' in self.shortdesc.text) else False

    def has_draft_comments(self):
        return True if len(self.draft_comments) > 0 else False

    def insert_shortdesc_tag(self):
        """
        Adds the <shortdesc> tag to files where this part is completely missing.
        """
        if not self.path:
            return
        shortdesc_parent = self.parent_map[self.title]
        if len(shortdesc_parent.findall('shortdesc')) == 0:
            shortdesc = text_element('shortdesc', 'SHORT DESCRIPTION')
            shortdesc_parent.insert(1, shortdesc)
            self.write()
        self.shortdesc = self.root.find('shortdesc')

    def get_draft_comments(self):
        draft_comments = []
        for dc in self.root.iter('draft-comment'):
            draft_comments.append((dc, self.parent_map[dc]))
        return draft_comments

    def update_old_links_to_self(self, old):
        """
        Update links to this topic in the entire folder.
        """
        # Compare self.name to name found in links
        for pair in self.ditamap.pairs:
            topic = pair.dita
            topic_local_links = topic.local_links
            if len(topic_local_links) == 0:
                continue
            for link in topic_local_links:
                link_href = link.attrib.get('href')
                if old in link_href:
                    print(topic.name, 'has old link to', self.name, '(%s)' % link_href)
                    new_name = link_href.replace(old, self.name)
                    print('Updated link href:', new_name, '\n')
                    link.set('href', new_name)
            topic.write()


class ISHFile(DITAProjectFile):
    """
    Get ishfields like FTITLE and FMODULETYPE.
    """

    def __init__(self, file_path, ditamap):
        super().__init__(file_path)
        self.ditamap = ditamap
        self.check_ishobject()
        ishfields = self.root.find('ishfields')
        for ishfield in ishfields.findall('ishfield'):
            if ishfield.attrib.get('name') == 'FTITLE':
                self.ftitle = ishfield.text
            elif ishfield.attrib.get('name') == 'FMODULETYPE':
                if ishfield.text == None and self.basename.startswith('v_'):  # library variable processing
                    ishfields.remove(ishfield)
                    self.root.set('ishtype', 'ISHLibrary')
                    self.write()
                else:
                    self.fmoduletype = ishfield.text

    def __repr__(self):
        return '<ISHFile: ' + self.name + '>'

    def check_ishobject(self):
        if self.root.tag != 'ishobject':
            print('Malformed ISH file, no ishobject tag:', self.ish.path)
            sys.exit()


class ReferenceInformationDITATopic(DITATopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        assert self.outputclass == 'referenceinformation' or self.outputclass == 'legalinformation'

    def __repr__(self):
        return '<DITATopic - RefInfo: ' + self.name + '>'

    def process_docdetails(self):
        # identify docdetails topic
        list_vars = list(self.root.iter('ph'))
        cond_docdetails = len(list_vars) > 0 and list_vars[0].attrib.get('varref') == 'DocTitle'
        if cond_docdetails and self.shortdesc_missing():
            # add short description
            self.set_shortdesc('Document details')
            self.add_nbsp_after_table()


class LegalInformationDITATopic(DITATopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        assert self.outputclass == 'legalinformation'

    def __repr__(self):
        return '<DITATopic - LegalInfo: ' + self.name + '>'

    def add_title_and_shortdesc(self):
        self.set_title('Legal information')
        self.insert_shortdesc_tag()
        if self.shortdesc.find('ph') is None:
            ph = ET.Element('ph', attrib={'varref': 'CopyrightYear'})
            ph.tail = ' HP Development Company, L.P.'
            self.shortdesc.insert(0, ph)
            self.set_shortdesc('© Copyright ')
            redundant_p = None
            for first_level in self.root:
                for x in first_level:
                    if 'outputclass' in x.attrib.keys() and x.attrib['outputclass'] == 'copyright':
                        redundant_p = x[0]
                        if "Copyright" in redundant_p.text:
                            x.remove(redundant_p)
                            self.write()
                            return


class ConceptDITATopic(DITATopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        assert self.outputclass == 'context' or self.outputclass == 'lpcontext'
        self.children = []

    def __repr__(self):
        return '<DITATopic - Concept: ' + self.name + '>'


class TaskDITATopic(DITATopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        assert self.outputclass == 'procedure'

    def __str__(self):
        return '<DITATopic - Task: ' + self.name + '>'


class Pair:

    def __init__(self, dita_obj, ish_obj):
        self.dita = dita_obj
        self.ish = ish_obj
        self.name = dita_obj.basename
        self.folder = dita_obj.folder
        self.ditamap = self.dita.ditamap

    # self.guid = self.ish.root.attrib['ishref']

    def __repr__(self):
        return self.name + ' <.dita, .ish>'

    def __contains__(self, item):
        if isinstance(item, DITAProjectFile):
            return True if item == self.dita or item == self.ish else False

    def create_new_name(self, num_rep):
        """
        Creates a filename that complies with the style guide, based on the document title.
        Takes into account repeating titles of different topics.
        """
        new_name = re.sub(r'[\s\W]', '_', self.dita.title.text).replace('___', '_').replace('__', '_').replace('_the_',
                                                                                                               '_')
        new_name = re.sub(r'\W+', '', new_name)
        if new_name.endswith('_'):
            new_name = new_name[:-1]
        if new_name[1] == '_':
            new_name = new_name[2:]

        if self.dita.outputclass in outputclasses.keys():
            prefix = outputclasses.get(self.dita.outputclass)
            new_name = prefix + new_name

        if num_rep > 1:
            new_name = new_name + '_' + str(num_rep)

        return new_name

    def update_name(self, num_rep):
        """
        Updates pair file names and links to them in all the documents.
        Takes into account repeating titles of different topics.
        """
        old_pair = Pair(DITATopic(self.dita.path, self.ditamap), ISHFile(self.ish.path, self.ditamap))
        print('Updating name:', old_pair)
        print()

        if isinstance(self.dita, LegalInformationDITATopic):
            self.dita.add_title_and_shortdesc()

        if self.dita.title_missing():
            print('Skipped: %s, nothing to rename (title missing)' % old_pair.name)
        else:
            new_name = self.create_new_name(num_rep)
            if old_pair.name == new_name:
                print('Skipped: %s, already renamed' % old_pair.name)
                return

            # Rename file
            self.name = new_name
            self.dita.name = self.name + self.dita.ext
            self.dita.path = os.path.join(self.folder, self.dita.name)
            if os.path.exists(self.dita.path):
                print('New path already exists:', self.dita.path)
            else:
                file_rename(old_pair.dita.path, self.dita.path)

            # Update links to this file throughout the folder
            self.dita.update_old_links_to_self(old_pair.dita.name)

            # Rename metadata file
            self.ish.ftitle = new_name
            print(self.ish.ftitle)
            self.ish.name = new_name + self.ish.ext
            self.ish.path = os.path.join(self.ish.folder, self.ish.name)
            self.ish.write()
            file_delete(old_pair.ish.path)

            # Update topicrefs in map
            for topicref in self.ditamap.root.iter('topicref'):
                if topicref.attrib.get('href') == old_pair.dita.name:
                    if old_pair.dita.name == self.dita.name:
                        print('Skipped in map: %s, nothing to rename' % old_pair.dita.name)
                        continue
                    topicref.set('href', self.dita.name)
            self.ditamap.write()


class Image:

    def __init__(self, href, ditamap):
        self.href = href
        self.ditamap = ditamap
        self.title = None
        self.temp_title = None
        self.ext = '.' + self.href.rsplit('.', 1)[1]

    def __repr__(self):
        r = '<Image ' + self.href
        if self.title:
            r = r + ': ' + str(self.title)
        r += '>'
        return r

    def generate_name(self, prefix):
        if self.temp_title is not None:
            # name the image based on its title
            name = '_'.join(self.temp_title.split(' '))
        else:
            name = self.href.rsplit('.', 1)[0]
        name = 'img_' + prefix + '_' + re.sub(r'\W+', '', name) + self.ext
        return name


'''
Frontend
'''


class App(Tk):

    def __init__(self):
        super().__init__()
        self.ditamap = None
        self.title('MaryTreat - Cheetah-to-DITA 1.5 Conversion Step')
        self.ditamap_var = StringVar()  # something used by Tkinter, here acts as a buffer for ditamap path
        self.ditamap_var.trace('w', self.turn_on_buttons)
        self.padding = {'padx': 5, 'pady': 5}
        self.no_images = True
        self.create_widgets()

    def create_widgets(self):

        button_file = Button(self, text='Select map...', command=self.get_ditamap_name)
        button_file.grid(row=0, column=0, sticky=NW, **self.padding)

        self.target_file = Entry(self, textvariable=self.ditamap_var, width=60, bg='white', relief=SUNKEN, bd=4,
                                 justify=LEFT)
        self.target_file.grid(row=0, column=1, sticky=NW, **self.padding, columnspan=2)

        self.button_rename = Button(self,
                                    text='Rename folder items',
                                    command=self.call_rename_all,
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
        sys.exit()

    def get_ditamap_name(self):
        """
        Show a file selection dialog. Remember the file that was selected.
        """
        file = filedialog.askopenfilename(filetypes=[('DITA maps', '.ditamap')])
        if file:
            self.ditamap_var.set(os.path.abspath(file))
            self.ditamap = DITAMap(self.ditamap_var.get())
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
            if self.no_images == False:
                self.button_edit_image_names['state'] = NORMAL
            else:
                self.button_edit_image_names['state'] = DISABLED

    def create_image_prefix_prompt_window(self):
        new_window = ImageNamesWindow(self.ditamap)

    # new_window.top.call('wm', 'attributes', '.', '-topmost', 'true')

    '''
    Calls to 'backend' functions that actually modify files.
    '''

    def call_rename_all(self, *args):
        if self.ditamap:
            self.ditamap.rename_all()
            rename_msg = 'Processed %s files in map folder.' % str(self.ditamap.rename_counter)
            messagebox.showinfo(title='Renamed files', message=rename_msg)

    def call_mass_edit(self, *args):
        if self.ditamap:
            self.ditamap.mass_edit()
            if len(self.ditamap.list_renamed) > 0:
                mass_edit_msg = 'Edited shortdescs in files:\n\n' + '\n'.join([k for k in self.ditamap.list_renamed])
            else:
                mass_edit_msg = 'Nothing to rename automatically.'
            messagebox.showinfo(title='Mass edited files', message=mass_edit_msg)

    def call_get_problematic_files(self, *args):
        if self.ditamap:
            new_window = MissingItemsWindow(self.ditamap)


class ImageNamesWindow():

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

        label_bottom_text = '(Example: \'inkcab\' for a document about the ink cabinet\nwill produce image names like ' \
                            '\'img_inkcab_***\' and \'scr_inkcab_\'.)'
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
        table.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=4, sticky=NS)

        table.tag_configure('greyed_out', foreground='grey')

        table.tag_bind('')
        table.bind('<<TreeviewSelect>>', self.item_selected)
        table.bind('<<TreeviewOpen>>', self.c_topic_open)
        table.bind('<<Treeview.Close>>', self.c_topic_close)

        return table

    def item_selected(self, event):
        item = self.table.focus()
        for pair in self.ditamap.pairs:
            topic = pair.dita
            if topic.name == self.table.item(item, 'text'):
                self.open_topic = topic
                self.fill_text_frame(self.open_topic)

    def c_topic_open(self, event):
        item = self.table.focus()
        for pair in self.ditamap.pairs:
            if not isinstance(pair.dita, ConceptDITATopic):
                continue
            topic = pair.dita
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
            if topic in pfiles:
                pfiles.remove(topic)
            if len(args) == 2:
                parent_id = args[1]
                tags = 'greyed_out'
            has_title = '-' if topic.title_missing() else topic.title.text
            has_shortdesc = '-' if topic.shortdesc_missing() else topic.shortdesc.text
            has_draft_comments = 'Yes' if len(topic.draft_comments) > 0 else ''
            topic_id = self.table.insert(parent_id, END, text=topic.name, open=False, tags=tags,
                                         values=(has_title, has_shortdesc, has_draft_comments))
            if len(topic.children) > 0:
                for child in topic.children:
                    child_id = create_table_row(child, topic_id)
                    return child_id
            return topic_id

        while pfiles:
            p = pfiles[0]
            create_table_row(p)
        self.attributes('-topmost', True)

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

        self.title_button = Button(self.file_frame, text='Edit title', \
                                   command=self.show_edit_title, state=DISABLED)
        self.title_button.grid(row=0, column=0, sticky=EW)

        self.shortdesc_button = Button(self.file_frame, text='Edit shortdesc', \
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
        for elem in topic.root.iter():
            text = (elem.text.strip() + '\n') if elem.text is not None else ''
            title_not_found = (elem.tag == 'title' and topic.title_missing())
            shortdesc_not_found = (elem.tag == 'shortdesc' and topic.shortdesc_missing())
            draft_comment_found = (elem.tag == 'draft-comment')
            if title_not_found or shortdesc_not_found or draft_comment_found:
                self.topic_text.insert(END, text, 'highlight')
            else:
                self.topic_text.insert(END, text)
        self.topic_text.config(state=DISABLED)

        self.title_button.config(state=NORMAL)
        self.shortdesc_button.config(state=NORMAL)
        self.open_button.config(state=NORMAL)

        self.title_var = StringVar(self, topic.title.text)
        self.shortdesc_var = StringVar(self, topic.shortdesc.text)

    def show_edit_title(self):
        self.title_field = Entry(self.file_frame, textvariable=self.title_var)
        self.title_field.grid(row=1, column=1,sticky=EW, **self.padding)

        self.title_label = Label(self.file_frame, text='Title:')
        self.title_label.grid(row=1, column=0, sticky=EW)

        self.save_title_btn = Button(self.file_frame, text='OK', command=self.save_title)
        self.save_title_btn.grid(row=1, column=2, sticky=EW)

    def show_edit_shortdesc(self):
        self.shortdesc_var.set(self.open_topic.shortdesc.text)

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


# TODO: insert &nbsp between auxiliary tables
# TODO: process draft comments, make user add titles first and foremost
# TODO: "commit" and "roll back" operations like renaming. maybe even reversing?
# TODO: treeview items that are inside the context topics in the map (to understand what they are about)

if __name__ == '__main__':
    app = App()
    app.mainloop()
