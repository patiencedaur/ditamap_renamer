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

def create_window():

	root = Tk()
	root.title('Cheetah-to-DITA Step 1.5')

	ditamap_path, folder, ditamap_shortname = '', '', ''
	ditamap_var = StringVar() # something used by Tkinter, acts as a buffer for ditamap_path

	def ditamap_callback(*args):
		'''
		Every time the Tkinter StringVar is changed, the global string DITA map path also gets changed.
		'''
		nonlocal ditamap_path, folder, ditamap_shortname
		ditamap_path = ditamap_var.get()
		folder, ditamap_shortname = os.path.split(ditamap_path)
		if ditamap_path:
			button_rename['state'] = NORMAL
			button_mass_edit['state'] = NORMAL
			button_view_shortdescs['state'] = NORMAL

	ditamap_var.trace('w', ditamap_callback)

	def get_ditamap_name():
		'''
		Show a file selection dialog. Remember the file that was selected.
		'''
		file = filedialog.askopenfilename(filetypes=[('DITA maps', '.ditamap')])
		if file:
			ditamap_var.set(os.path.abspath(file))
			
	tool_label = Label(root, justify=LEFT, text='Cheetah-to-DITA Step 1.5')
	tool_label.grid(row = 0, column = 1, sticky = N, pady = 10)

	button_file = Button(root, text = 'Select map...', command = get_ditamap_name)
	button_file.grid(row = 1, column = 0, sticky = NW, padx = 10, pady = 10)

	target_file = Entry(root, textvariable=ditamap_var, width=60, bg='white', relief=SUNKEN, bd=4, justify=LEFT)
	target_file.grid(row = 1, column = 1, sticky = NW, pady = 10, padx = 10, columnspan = 2)


	def get_xml_tree(filename):
		'''
		Transforms an XML document into a tree-like collection for easier editing with Python.
		'''
		return ET.parse(os.path.join(folder, filename))


	def create_new_filename(string):
		'''
		Creates a filename that complies with the style guide, based on the document title.
		'''
		new_name = re.sub(r'[\s\W]', '_', string).replace('___', '_').replace('__', '_').replace('_the_', '_')
		if new_name.endswith('_'):
			new_name = new_name[:-1]
		if new_name[1] == '_':
			new_name = new_name[2:]
		return new_name


	def missing(title_text):
		'''
		Checks if the title is missing, returns false in case there is an actual title.
		'''
		return True if title_text == 'MISSING TITLE, PLEASE UPDATE' or title_text == None else False

	def rename_files(topicref):
		'''
		Assigns to DITA and 3SISH files names that comply with the style guide. Renames topicrefs in the DITA map accordingly.
		'''
		old_dita_filename = topicref.attrib.get('href')
		old_filename_no_ext = old_dita_filename.replace('.dita', '')
		old_sish_filename = old_filename_no_ext + '.3sish'

		new_dita_filename = old_dita_filename # by default
		new_sish_filename = old_sish_filename
		# parse topic file
		topic_tree = get_xml_tree(old_dita_filename)
		topic_root = topic_tree.getroot()
		outputclass = topic_root.attrib.get('outputclass')
		title = topic_root.find('title').text
		print('Title:', title)
		# parse 3SISH file
		sish_tree = get_xml_tree(old_sish_filename)

		# prepare to rename files only for task, reference, or context topics
		if topic_root.tag in doctypes and not missing(title):
			new_filename = create_new_filename(title)
			# add prefix if outputclass is valid
			if outputclass in outputclasses.keys():
				prefix = outputclasses.get(outputclass)
				new_filename = prefix + new_filename	
			new_dita_filename = new_filename + '.dita'
			new_sish_filename = new_filename + '.3sish'
			# replace SISH FTITLE, which is the DITA filename, and rename sish file
			for ishfield in sish_tree.getroot().iter('ishfield'):
				if ishfield.attrib.get('name') == 'FTITLE' and ishfield.text == old_filename_no_ext:
					ishfield.text = new_filename
			sish_tree.write(os.path.join(folder, old_sish_filename))
			# rename sish file in file system
			os.rename(os.path.join(folder, old_sish_filename), os.path.join(folder, new_sish_filename))

		print('Old DITA:', old_dita_filename)
		print('Old SISH:', old_sish_filename)
		print('New DITA:', new_dita_filename)
		print('New SISH:', new_sish_filename)
		print('Outputclass:', outputclass)
	    # rename dita file in file system
		os.rename(os.path.join(folder, old_dita_filename), os.path.join(folder, new_dita_filename))

		return new_dita_filename.replace('.dita', '')


	def append_header(xml_file, header):
		'''
		The ElementTree library, which I use to parse XML contents, removes the header when writing into file.
		This function puts the header back into place.
		'''
		with open(xml_file, 'r+') as f:
			content = f.read()
			f.seek(0, 0)
			f.write(header + content)


	def rename_folder_items(map_path):
		'''
		Mass rename files in the folder according to the style guide.
		'''
		map_tree = get_xml_tree(map_path)
		map_root = map_tree.getroot()
		# parse every topic mentioned in ditamap
		for topicref in map_root.iter('topicref'):
			# parse dita file with name that is in href
			new_dita_filename = rename_files(topicref) + '.dita'
			# rename file in ditamap
			topicref.set('href', new_dita_filename)
			map_tree.write(map_path)
			print('Updated in ditamap:', topicref.attrib)
			print()

		ditamap_header = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE map\n  PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">\n'
		append_header(map_path, ditamap_header)


	def mass_edit(folder):
		'''
		Mass edit short descriptions for typical documents.
		'''
		shortdescs = {
			'Revision history and confidentiality notice': 'This chapter contains a table of revisions, printing instructions, and a notice of document confidentiality.',
			'Revision history': 'Below is the history of the document revisions and a list of authors.',
			'Printing instructions': 'Follow these recommendations to achieve the best print quality.'
		}
		for file in os.listdir(folder):
			if file.endswith('.dita'):
				tree = get_xml_tree(file)
				root = tree.getroot()
				title = root.find('title')
				if title.text in shortdescs.keys():
				 	for shortdesc in root.iter('shortdesc'):
				 		shortdesc.text = shortdescs[title.text]
				 	tree.write(os.path.join(folder, file))
		mass_edit_msg = 'Edited shortdescs in files:\n\n' + '\n'.join([k for k in shortdescs.keys()])
		messagebox.showinfo(title='Mass edited files', message=mass_edit_msg)


	def view_shortdescriptions(folder):
		'''
		View files with missing short descriptions. Can save the file list into a TXT document.
		'''
		problematic_files = []
		for file in os.listdir(folder):
			if file.endswith('.dita'):
				tree = get_xml_tree(file)
				for shortdesc in tree.getroot().iter('shortdesc'):
					if shortdesc.text == 'SHORT DESCRIPTION' or shortdesc is None:
						problematic_files.append(file)
		open_files_msg = 'Files with missing shortdesc: ' + str(len(problematic_files)) + '. Open files one by one?'
		open_files = messagebox.askyesno(title='Missing short desriptions',
							message=open_files_msg)
		if open_files:
			for file in problematic_files:
				os.system('notepad.exe ' + os.path.join(folder, file))
		else:
			save_files = messagebox.askyesno(title='Save files',
								message='Save file list to document?')
			if save_files:
				open('status.txt', 'w').close() # clear the contents
				status = open('status.txt', 'a')
				status.write('Folder:\n' + folder + '\n\nEdit shortdescs in the following files:\n\n')
				for f in problematic_files:
					status.write(f + '\n')
				status.close()
				messagebox.showinfo(title='Wrote to file', message='Wrote to file "status.txt" in the script folder. Press OK to exit.')

	button_rename = Button(root,
		text = 'Rename folder items',
		command = lambda: rename_folder_items(ditamap_path),
		state = DISABLED)
	button_rename.grid(row = 2, column = 1, sticky = EW, padx = 10, pady = 10)
    
	button_mass_edit = Button(root,
		text = 'Mass edit typical shortdescs',
		command = lambda: mass_edit(folder),
		state = DISABLED)
	button_mass_edit.grid(row = 2, column = 2, sticky = EW, padx = 10, pady = 10)
    
	button_view_shortdescs = Button(root,
		text = 'Edit missing shortdescs',
		command = lambda: view_shortdescriptions(folder),
		state = DISABLED)
	button_view_shortdescs.grid(row = 3, column = 1, sticky = EW, padx = 10, pady = 10)

	button_exit = Button(root, text = 'Exit', command = root.destroy)
	button_exit.grid(row = 3, column = 2, sticky = SE, padx = 10, pady = 10)
    
	root.mainloop()

# TODO: process libvar correctly
# DONE: Tkinter interface to select the map file
# TODO: topic titles in Sentence case
# TODO: add 'img_<userinput>_meaningful_name' to images (track them by GUID and convert fig titles)
# TODO: insert &nbsp between auxiliary tables

if __name__ == '__main__':

	create_window()
