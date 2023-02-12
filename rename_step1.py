import re
import os, sys
import xml.etree.ElementTree as ET
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

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
    'procedure': 't_'
}

# Document type, indicated in the first content tag. Example: <task id=... outputclass="procedure">
doctypes = ['concept', 'task', 'reference']

outputclasses = {
# Document outputclass, indicated as an attribute of the first content tag. Example: <task id=... outputclass="procedure">
	'context' : 'c_',
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

class DITAProjectFile:
	'''
	Based on file path, retrieve the containing folder and parse the file in advance.
	'''
	def __init__(self, file_path):
		self.path = file_path
		self.folder, self.name = os.path.split(self.path)
		self.basename, self.ext = os.path.splitext(self.name)
		self.tree = ET.parse(self.path)
		self.root = self.tree.getroot()
		self.header = self.get_header()
		self.ditamap = None # is assigned during Pair creation
		
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

	def get_header(self):
		header = ''
		if self.path:
			with open(self.path, 'r', encoding='utf8') as f:
				declaration = r'(<\?xml version="1.0" encoding="UTF-8"\?>\n)(<!DOCTYPE.*?>\n)?'
				beginning = ''
				for x in range(4):
					beginning += str(next(f))
				#look for xml decl or xml decl followed by doctype decl
				found_declaration = re.findall(declaration, beginning, re.DOTALL)
				if len(found_declaration) > 0:
					header = ''.join(found_declaration[0])
				else:
					header = '<?xml version="1.0" encoding="UTF-8"?>\n'
		return header

	def write(self):
		'''
		Call this after all manipulations with the tree.
		'''
		if not dry_run:
			self.tree.write(self.path)
			self.append_header()

	def append_header(self):
		'''
		The ElementTree library, which I use to parse DITA file contents, removes the header when writing into file.
		This puts the header back into place.
		'''
		if not dry_run:
			with open(self.path, 'r+', encoding='utf8') as f:
				content = f.read()
				f.seek(0, 0)
				f.write(self.header + content)


class DITAMap(DITAProjectFile):
	'''
	Get list of topicrefs and their ish counterparts.
	'''
	def __init__(self, file_path):
		super().__init__(file_path)
		self.ditamap = self
		self.images = self.get_images()
		self.pairs = self.get_pairs()
		self.libvar = self.get_libvar()

	def __str__(self):
		return '<DITAMap: ' + self.name + '>'

	def __contains__(self, item):
		for pair in self.pairs:
			if item in pair:
				return True
		return False

	def get_pairs(self):
		pairs = []
		for topicref in self.root.iter('topicref'):
			topic_path = os.path.join(self.folder, topicref.attrib.get('href'))
			if os.path.exists(topic_path):
				topic = DITATopic(topic_path, self)
			else:
				print('Cannot create DITAProjectFile from path %s. Aborting.' % topic_path)
				sys.exit()
			if topic.outputclass == 'referenceinformation':
				topic = ReferenceInformationDITATopic(topic_path, self)
			elif topic.outputclass == 'concept':
				topic = ConceptDITATopic(topic_path, self)
			elif topic.outputclass == 'task':
				topic = TaskDITATopic(topic_path, self)
			ish_path = topic_path.replace('.dita', '.3sish')
			ish = ISHFile(ish_path, self)
			pair = Pair(topic, ish)
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
		'''
		Rename files in map folder according to their titles and the style guide.
		'''
		old_pairs = [Pair(p.dita, p.ish) for p in self.pairs]
		self.rename_counter = 0
		for pair in self.pairs:
			if pair.dita.root.tag in doctypes and not pair.dita.title_missing():
				pair.update_name()
				self.rename_counter += 1

	def mass_edit(self):
		'''
		Mass edit short descriptions for typical documents.
		'''
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

	def insert_nbsps(self):
		'''
		Insert empty paragraph after a table before a text paragraph or another table.
		'''
		for pair in self.pairs:
			topic = pair.dita
			list_vars = list(topic.root.iter('ph'))

			cond_docdetails = (isinstance(topic, ReferenceInformationDITATopic)
				and len(list_vars) > 0 and list_vars[0].attrib.get('varref') == 'DocTitle')
			cond_revhistory = (isinstance(topic, ReferenceInformationDITATopic) 
						and topic.title.text == 'Revision history')

			if cond_docdetails or cond_revhistory:

				empty_paragraph = ET.Element('p')
				empty_paragraph.text = '\u00A0'

				print(empty_paragraph.tag, empty_paragraph.text)

	def view_shortdescriptions(self):
		self.problematic_files = [p.dita for p in self.pairs if p.dita.shortdesc_missing()]

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
	'''
	Get DITA outputclass, title, and shortdesc.
	'''
	def __init__(self, file_path, ditamap):
		super().__init__(file_path)
		self.ditamap = ditamap # got images, too
		self.outputclass = self.root.attrib.get('outputclass')
		self.title = self.root.find('title')
		self.shortdesc = self.root.find('shortdesc')
		self.local_links = self.root.findall('.//xref[@scope="local"]')
		self.images = self.get_images()
		self.get_draft_comments()

	def __repr__(self):
		return '<DITATopic: ' + self.name + '>'

	def __contains__(self, item):
		contains = False
		if isinstance(item, Image) and item in self.images:
			contains = True
		if isinstance(item, str) and item in self.local_links:
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
		self.title.text = new_title
		self.write()

	def set_shortdesc(self, new_shortdesc):
		# New shortdesc is a string
		self.shortdesc.text = new_shortdesc
		self.write()

	def title_missing(self):
		return True if self.title.text == None or 'MISSING TITLE' in self.title.text else False

	def shortdesc_missing(self):
		if self.shortdesc == None:
			self.insert_shortdesc_tag()
			return True
		return True if self.shortdesc.text == None or self.shortdesc.text == '' or 'SHORT DESCRIPTION' in self.shortdesc.text else False

	def insert_shortdesc_tag(self):
		"""
		Adds the <shortdesc> tag to files where this part is completely missing.
		"""
		if not self.path:
			return
		title_match = '</title>'
		shortdesc = '   <shortdesc>SHORT DESCRIPTION</shortdesc>\n'
		with open(self.path, 'r', encoding='utf8') as f:
			contents = f.readlines()
			for line in contents:
				if title_match in line:
					ind = contents.index(line)
					contents.insert(ind + 1, shortdesc)
		with open(self.path, 'w', encoding='utf8') as f:
			f.writelines(contents)				

	def get_draft_comments(self):
		draft_comments = []
		for dc in self.root.iter('draft-comment'):
			draft_comments.append(dc)

	def update_old_links_to_self(self, old):
		'''
		Update links to this topic in the entire folder.
		'''
		#Compare self.name to name found in links
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
	'''
	Get ishfields like FTITLE and FMODULETYPE.
	'''
	def __init__(self, file_path, ditamap):
		super().__init__(file_path)
		self.ditamap = ditamap
		self.check_ishobject()
		ishfields = self.root.find('ishfields')
		for ishfield in ishfields.findall('ishfield'):
			if ishfield.attrib.get('name') == 'FTITLE':
				self.ftitle = ishfield.text
			elif ishfield.attrib.get('name') == 'FMODULETYPE':
				if ishfield.text == None and self.basename.startswith('v_'): # library variable processing
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
		assert self.outputclass == 'referenceinformation'

	def __repr__(self):
		return '<DITATopic - RefInfo: ' + self.name + '>'


class ConceptDITATopic(DITATopic):

	def __init__(self, file_path, ditamap):
		super().__init__(file_path, ditamap)
		assert self.outputclass == 'concept'

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

	def __repr__(self):
		return self.name + ' <.dita, .ish>'

	def __contains__(self, item):
		if isinstance(item, DITAProjectFile):
			return True if item == self.dita or item == self.ish else False

	def create_new_name(self):
		'''
		Creates a filename that complies with the style guide, based on the document title.
		'''
		new_name = re.sub(r'[\s\W]', '_', self.dita.title.text).replace('___', '_').replace('__', '_').replace('_the_', '_')
		if new_name.endswith('_'):
			new_name = new_name[:-1]
		if new_name[1] == '_':
			new_name = new_name[2:]

		if self.dita.outputclass in outputclasses.keys():
			prefix = outputclasses.get(self.dita.outputclass)
			new_name = prefix + new_name
		
		return new_name

	def update_name(self):
		old_pair = Pair(DITATopic(self.dita.path, self.ditamap), ISHFile(self.ish.path, self.ditamap))

		if self.dita.title_missing():
			if self.dita.outputclass == 'legalinformation':
				self.dita.set_title('Legal information')
				self.dita.set_shortdesc('© Copyright 2017-2019 HP Development Company, L.P.')
			else:
				print('Skipped: %s, nothing to rename (title missing)' % old_pair.name)
		new_name = self.create_new_name()
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
		name = 'img_' + prefix + '_' + name + self.ext
		return name

'''
Frontend
'''

class App(Tk):

	def __init__(self):
		super().__init__()
		self.title('Cheetah-to-DITA Step 1.5')
		self.ditamap_var = StringVar() # something used by Tkinter, here acts as a buffer for ditamap path
		self.ditamap_var.trace('w', self.turn_on_buttons)
		self.padding = {'padx': 5, 'pady': 5}
		self.no_images = True
		self.create_widgets()


	def create_widgets(self):

		button_file = Button(self, text = 'Select map...', command = self.get_ditamap_name)
		button_file.grid(row = 0, column = 0, sticky = NW, **self.padding)

		self.target_file = Entry(self, textvariable=self.ditamap_var, width=60, bg='white', relief=SUNKEN, bd=4, justify=LEFT)
		self.target_file.grid(row = 0, column = 1, sticky = NW, **self.padding, columnspan = 2)

		self.button_rename = Button(self,
		text = 'Rename folder items',
		command = self.call_rename_all,
		state = DISABLED)
		self.button_rename.grid(row = 1, column = 1, sticky = EW, **self.padding)
	    
		self.button_mass_edit = Button(self,
			text = 'Mass edit typical shortdescs',
			command = self.call_mass_edit,
			state = DISABLED)
		self.button_mass_edit.grid(row = 1, column = 2, sticky = EW, **self.padding)
	    
		self.button_view_shortdescs = Button(self,
			text = 'Edit missing shortdescs',
			command = self.call_view_shortdescriptions,
			state = DISABLED)
		self.button_view_shortdescs.grid(row = 2, column = 1, sticky = EW, **self.padding)

		self.button_edit_image_names = Button(self,
			text = 'Mass edit image names',
			command = self.create_image_prefix_prompt_window,
			state = DISABLED)
		self.button_edit_image_names.grid(row = 2, column = 2, sticky = EW, **self.padding)

		button_exit = Button(self, text = 'Exit', command = self.destroy)
		button_exit.grid(row = 2, column = 0, sticky = SW, **self.padding)


	def get_ditamap_name(self):
		'''
		Show a file selection dialog. Remember the file that was selected.
		'''
		file = filedialog.askopenfilename(filetypes=[('DITA maps', '.ditamap')])
		if file:
			self.ditamap_var.set(os.path.abspath(file))
			self.ditamap = DITAMap(self.ditamap_var.get())
			if len(self.ditamap.images) > 0:
				self.no_images = False


	def turn_on_buttons(self, *args):
		'''
		Every time the Tkinter StringVar is changed, the DITA map path also gets changed.
		'''
		if self.ditamap_var:
			self.button_rename['state'] = NORMAL
			self.button_mass_edit['state'] = NORMAL
			self.button_view_shortdescs['state'] = NORMAL
			if self.no_images == False:
				self.button_edit_image_names['state'] = NORMAL


	def create_image_prefix_prompt_window(self):
		self.new_window = ImageNamesWindow(self.ditamap)
	
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

	def call_view_shortdescriptions(self, *args):
		if self.ditamap:
			self.ditamap.view_shortdescriptions()
			self.new_window = MissingItemsWindow(self.ditamap)
			

class ImageNamesWindow():

	def __init__(self, ditamap):

		self.image_prefix_var = StringVar()
		self.ditamap = ditamap
		self.padding = {'padx': 5, 'pady': 5}

		self.top = Toplevel()
		self.top.title = 'Mass edit image names'
		
		label_top_text = 'Enter a prefix associated with the document subject.'
		prompt_label_top = Label(self.top, justify = LEFT,
				text = label_top_text)
		prompt_label_top.grid(row = 0, column = 0, sticky = NW, **self.padding)
		
		label_bottom_text = '(Example: \'inkcab\' for a document about the ink cabinet\nwill produce image names like \'img_inkcab_***\' and \'scr_inkcab_\'.)'
		prompt_label_bottom = Label(self.top, justify = LEFT,
				text = label_bottom_text)
		prompt_label_bottom.grid(row = 1, column = 0, sticky = NW, **self.padding)

		prompt_entry = Entry(self.top, textvariable=self.image_prefix_var, width=60, bg='white', relief=SUNKEN, bd=4, justify=LEFT)
		prompt_entry.grid(row = 2, column = 0, sticky = EW, **self.padding)

		save_image_prefix = Button(self.top,
			text = 'OK',
			command = self.call_edit_image_names)
		save_image_prefix.grid(row = 2, column = 1, sticky = EW, **self.padding)

	def call_edit_image_names(self):
		'''
		Show the image prefix dialog. Remember the prefix.
		'''
		if self.ditamap:
			prefix = self.image_prefix_var.get()
			self.ditamap.edit_image_names(prefix)
			messagebox.showinfo(title = 'Mass edit image names', message = 'Images renamed.')
			self.top.destroy()
		
class MissingItemsWindow():

	def __init__(self, ditamap):

		self.ditamap = ditamap
		
		self.top = Toplevel()
		self.top.title = 'Edit titles and shortdescs'

		label = Label(self.top, justify=LEFT, text='Double-click a file to edit.')
		label.grid(row=0, column=0, sticky=W)

		save_files = Button(self.top, text='Save list to file', command=self.save_file_list)
		save_files.grid(row=0, column=1, sticky=E)

		self.table = self.create_table()
		self.table.grid(row=1, column=0, columnspan=2, sticky=NSEW)

	def create_table(self):

		columns = ['filename', 'title', 'shortdesc', 'draft']
		table = ttk.Treeview(self.top, columns=columns, show='headings', padding='5 5')

		table.heading('filename', text='File name')
		table.heading('title', text='Title?')
		table.heading('shortdesc', text='Shortdesc?')
		table.heading('draft', text='Draft comment?')

		table.column('filename', minwidth=300, width=500, anchor=W)

		for column in columns[1:]:
			table.column(column, minwidth=30, width=100, anchor=CENTER, stretch=NO)

		scrollbar = Scrollbar(self.top, orient=VERTICAL, command=table.yview)
		table.configure(yscroll=scrollbar.set)
		scrollbar.grid(row=1, column=2, sticky=NS)

		for p in self.ditamap.problematic_files:
			has_title = 'No' if p.title_missing() else ''
			has_shortdesc = 'No' if p.shortdesc_missing() else ''
			table.insert('', END, p.name, text=p.name, values=(p.name, has_title, has_shortdesc))
			table.tag_bind('')

		table.bind('<Double-1>', self.item_doubleclicked)

		return table

	def item_doubleclicked(self, event):
		item = self.table.selection()[0]
		for pair in self.ditamap.pairs:
			topic = pair.dita
			if topic.name == self.table.item(item, 'text'):
				os.system('notepad.exe ' + topic.path)

	def save_file_list(self):
		status_name = 'status_' + self.ditamap.basename + '.txt'
		status_path = os.path.join(self.ditamap.folder, status_name)
		if os.path.exists(status_path):
			open(status_path, 'w').close() # clear the contents
		with open(status_path, 'a') as status:
			status.write('Edit shortdescs in the following files:\n\n')
			for f in self.ditamap.problematic_files:
				status.write(f.path + '\n')
		save_filelist_msg = 'Wrote to file ' + status_path + '. Press OK to close the window.'
		messagebox.showinfo(title='Wrote to file', message=save_filelist_msg)

    
## DONE: change internal links across project
## DONE: process libvar correctly
## DONE: Tkinter interface to select the map file
# TODO: topic titles in Sentence case
## DONE: add 'img_<userinput>_meaningful_name' to images (track them by GUID and convert fig titles)
# TODO: insert &nbsp between auxiliary tables
# TODO: if no images, prevent from opening image window
# TODO: process draft comments, make user add titles first and foremost

if __name__ == '__main__':

	app = App()
	app.mainloop()
	#ditamap = DITAMap(r'C:\hp_cheetahr5\TS5ES-00011 - Cleaning Station Service\Step1 - Copy\TS5ES-00011.ditamap')
	#ditamap.insert_nbsps()
	#ditamap = DITAMap(r'C:\hp_cheetahr5\CA494-24500-01 - How-to One Shot 12000\Step1 - Copy\VASONT-IP_DIG_HTG_CA494-24500_Rev01_10K12K_One-Shot.ditamap')
	
	# ditamap = DITAMap(r'C:\hp_cheetahr5\CA494-30210 - Pack Ready Lamination Application\Step1 - Copy\r_IP_DIG_HTG_CA494-30210_Pack_Ready_Lamination_Rev02.ditamap')
