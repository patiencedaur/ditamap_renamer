import re
import os, sys
import xml.etree.ElementTree as ET
import msvcrt as m
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox

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
		self.ditamap = None
		
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
		# self.image_href_list = self.get_image_href_list()
		self.pairs = self.get_pairs()

	def __str__(self):
		return '<DITAMap: ' + self.name + '>'

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
		return pairs

	# def get_image_href_list(self):
	# 	image_href_list = []
	# 	for file in os.listdir(self.folder):
	# 		if file.endswith(('png', 'jpg', 'gif')):
	# 			image_href_list.append(file)
	# 	return image_href_list

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

	def mass_edit_shortdescriptions(self):
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
			dita_file = pair.dita
			if dita_file.title.text in shortdescs.keys() and dita_file.shortdesc_missing():
				shortdesc = shortdescs[dita_file.title.text]
				dita_file.set_shortdesc(shortdesc)
				self.list_renamed.append(dita_file.name)

	def view_shortdescriptions(self):
		self.problematic_files = [p.dita for p in self.pairs if p.dita.shortdesc_missing()]

	def edit_image_names(self, image_prefix):
		# there can be two images with different paths but identical titles
		# one image can be reference in multiple topics
			pass
			

class DITATopic(DITAProjectFile):
	'''
	Get DITA outputclass, title, and shortdesc.
	'''
	def __init__(self, file_path, ditamap):
		super().__init__(file_path)
		self.ditamap = ditamap
		self.outputclass = self.root.attrib.get('outputclass')
		self.title = self.root.find('title')
		self.shortdesc = self.root.find('shortdesc')
		# self.images = self.get_images()

	def __repr__(self):
		return '<DITATopic: ' + self.name + '>'

	def __contains__(self, item):
		if isinstance(item, Image) and item in self.images:
			return True
		return False

	# def get_images(self):
	# 	topic_images = []
	# 	for fig in self.root.iter('fig'):
	# 		image_title = None
	# 		image_title_tag = fig.find('title')
	# 		image_href = fig.find('image').attrib.get('href')
	# 		if image_title_tag is not None and image_href in self.ditamap.image_href_list:
	# 			image = Image(image_href, self.ditamap)
	# 			image.title = image_title_tag.text
	# 			image.topics.append(self)
	# 			topic_images.append(image)
	# 	return topic_images

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

	def update_old_links_to_self(self, old):
		'''
		Update links to this topic in the entire folder.
		'''
		#Compare self.name to name found in links
		for pair in self.ditamap.pairs:
			dita_file = pair.dita
			if dita_file == self:
				continue
			links = dita_file.root.findall('.//xref[@scope="local"]') # ex. <xref scope="local" href="c_Load_weights.dita">
			if len(links) == 0:
				continue
			for link in links:
			 	if link.attrib.get('href') == old:
			 		print(dita_file.name, 'has old link to', self.name, '(%s)' % old)
			 		link.set('href', self.name)
			 		print('Updated link href')
			 		break
			dita_file.write()


class ISHFile(DITAProjectFile):
	'''
	Get ishfields like FTITLE and FMODULETYPE.
	'''
	def __init__(self, file_path, ditamap):
		super().__init__(file_path)
		self.ditamap = ditamap
		for ishfield in self.root.iter('ishfield'):
			if ishfield.attrib.get('name') == 'FTITLE':
				self.ftitle = ishfield
			elif ishfield.attrib.get('name') == 'FMODULETYPE':
				self.fmoduletype = ishfield

	def __repr__(self):
		return '<ISHFile: ' + self.name + '>'


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
		old_pair = Pair(DITATopic(self.dita.path), ISHFile(self.ish.path))

		if self.dita.title_missing():
			print('Skipped: %s, nothing to rename' % old_pair.name)
		new_name = self.create_new_name()
		if old_pair.name == new_name:
			print('Skipped: %s, nothing to rename' % old_pair.name)
			return

		# Rename file
		self.name = new_name
		self.dita.name = self.name + self.dita.ext
		self.dita.path = os.path.join(self.folder, self.dita.name)
		if os.path.exists(self.dita.path):
			print('Error, new path already exists:', self.dita.path)
			return
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


# class Image:

# 	def __init__(self, href, ditamap):
# 		self.href = href
# 		self.ditamap = ditamap
# 		self.basename, self.ext = os.path.splitext(self.href)
# 		self.path = os.path.join(self.ditamap.folder, self.href)
# 		self.topics, self.title = self.get_topics_and_title()

# 	def __repr__(self):
# 		r = '<Image ' + self.href
# 		if self.title:
# 			r = r + ', title: ' + str(self.title)
# 		r += '>'
# 		return r

# 	def get_topics_and_titles(self):
# 		# scan all images in all topics
# 		for pair in self.ditamap.pairs:
# 			if self in pair.dita.images and self.href in self.ditamap.image_href_list:
# 				print(self)
# 		return None

# 	def create_name(self, prefix, repeat):
# 		if self.title is not None:
# 			# name the image based on its title
# 			name = '_'.join(self.title.split(' '))
# 			if repeat > 0:
# 				name = name + '_' + str(repeat)
# 			name += self.ext
# 		name = 'img_' + prefix + '_' + self.href
# 		return name

# 	def update_to_meaningful_name(self, prefix):
		
# 		pass
# 		# file_rename(old_image.path, self.path)

		# # find this image in all topics by traversal
		# for pair in self.ditamap.pairs:
		# 	if self in pair.dita:
		# 		for fig in pair.dita.root.iter('fig'):
		# 			found_image = fig.find('image')
		# 			if old_image.href == found_image.attrib.get('href'):
		# 				found_image.set('href', self.href)


'''
Frontend
'''

class App(Tk):

	def __init__(self):
		super().__init__()
		self.title('Cheetah-to-DITA Step 1.5')
		self.ditamap_var = StringVar() # something used by Tkinter, here acts as a buffer for ditamap path
		self.image_prefix_var = StringVar()
		self.ditamap_var.trace('w', self.turn_on_buttons)
		self.padding = {'padx': 5, 'pady': 5}
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
			command = self.call_mass_edit_shortdescriptions,
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


	def turn_on_buttons(self, *args):
		'''
		Every time the Tkinter StringVar is changed, the DITA map path also gets changed.
		'''
		if self.ditamap_var:
			self.button_rename['state'] = NORMAL
			self.button_mass_edit['state'] = NORMAL
			self.button_view_shortdescs['state'] = NORMAL
			self.button_edit_image_names['state'] = NORMAL


	def create_image_prefix_prompt_window(self):
		self.image_prefix_prompt = Toplevel(self)
		self.image_prefix_prompt.title = 'Mass edit image names'
		
		label_top_text = 'Enter a prefix associated with the document subject.'
		prompt_label_top = Label(self.image_prefix_prompt, justify = LEFT,
				text = label_top_text)
		prompt_label_top.grid(row = 0, column = 0, sticky = NW, **self.padding)
		
		label_bottom_text = '(Example: \'inkcab\' for a document about the ink cabinet\nwill produce image names like \'img_inkcab_***\' and \'scr_inkcab_\'.)'
		prompt_label_bottom = Label(self.image_prefix_prompt, justify = LEFT,
				text = label_bottom_text)
		prompt_label_bottom.grid(row = 1, column = 0, sticky = NW, **self.padding)

		prompt_entry = Entry(self.image_prefix_prompt, textvariable=self.image_prefix_var, width=60, bg='white', relief=SUNKEN, bd=4, justify=LEFT)
		prompt_entry.grid(row = 2, column = 0, sticky = EW, **self.padding)

		save_image_prefix = Button(self.image_prefix_prompt,
			text = 'OK',
			command = self.call_edit_image_names)
		save_image_prefix.grid(row = 2, column = 1, sticky = EW, **self.padding)
	
	'''
	Calls to 'backend' functions that actually modify files.
	'''

	def call_rename_all(self, *args):
		if self.ditamap:
			self.ditamap.rename_all()
			rename_msg = 'Processed %s files in map folder.' % str(self.ditamap.rename_counter)
			messagebox.showinfo(title='Renamed files', message=rename_msg)

	def call_mass_edit_shortdescriptions(self, *args):
		if self.ditamap:
			self.ditamap.mass_edit_shortdescriptions()
			if len(self.ditamap.list_renamed) > 0:
				mass_edit_msg = 'Edited shortdescs in files:\n\n' + '\n'.join([k for k in self.ditamap.list_renamed])
			else:
				mass_edit_msg = 'Nothing to rename automatically.'
			messagebox.showinfo(title='Mass edited files', message=mass_edit_msg)

	def call_view_shortdescriptions(self, *args):
		if self.ditamap:
			self.ditamap.view_shortdescriptions()
			problematic_files = self.ditamap.problematic_files
			open_files_msg = 'Files with missing shortdesc: %s.' % str(len(problematic_files))
			if len(problematic_files) > 0:
				open_files_msg += '. Open files one by one?'
			open_files = messagebox.askyesno(title='Missing short desriptions',
							message=open_files_msg)
			if open_files:
				for dita in self.ditamap.problematic_files:
					os.system('notepad.exe ' + dita.path)
			else:
				save_files = messagebox.askyesno(title='Save files',
									message='Save file list to document?')
				if save_files:
					status_name = 'status_' + self.ditamap.basename + '.txt'
					status_path = os.path.join(self.ditamap.folder, status_name)
					if os.path.exists(status_path):
						open(status_path, 'w').close() # clear the contents
					with open(status_path, 'a') as status:
						status.write('Edit shortdescs in the following files:\n\n')
						for f in problematic_files:
							status.write(f.path + '\n')
					save_filelist_msg = 'Wrote to file ' + status_path + '. Press OK to close the window.'
					messagebox.showinfo(title='Wrote to file', message=save_filelist_msg)

	def call_edit_image_names(self):
		'''
		Show the image prefix dialog. Remember the prefix.
		'''
		if self.ditamap:
			prefix = self.image_prefix_var.get()
			self.ditamap.edit_image_names(prefix)

		
	
    
## DONE: change internal links across project
# TODO: process libvar correctly
# DONE: Tkinter interface to select the map file
# TODO: topic titles in Sentence case
# TODO: add 'img_<userinput>_meaningful_name' to images (track them by GUID and convert fig titles)
# TODO: insert &nbsp between auxiliary tables

if __name__ == '__main__':

	#app = App()
	#app.mainloop()
	ditamap = DITAMap(r'C:\hp_cheetahr5\TS5ES-00011 - Cleaning Station Service\Step1 - Copy\TS5ES-00011.ditamap')
	ditamap.edit_image_names('CS')
	#ditamap = DITAMap(r'C:\hp_cheetahr5\CA494-24500-01 - How-to One Shot 12000\Step1 - Copy\VASONT-IP_DIG_HTG_CA494-24500_Rev01_10K12K_One-Shot.ditamap')
