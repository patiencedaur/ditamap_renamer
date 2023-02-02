import re
import os, sys
import xml.etree.ElementTree as ET
import msvcrt as m
#from tkinter import filedialog as fd

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


def not_missing(title_text):
	'''
	Checks if the title is missing, returns True in case there is an actual title, otherwise returns False.
	'''
	return False if title_text == 'MISSING TITLE, PLEASE UPDATE' or title_text == None else True

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
	if topic_root.tag in doctypes and not_missing(title):
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


def rename_folder_items(map_name):
	'''
	Mass rename files in the folder according to the style guide.
	'''
	map_tree = get_xml_tree(ditamap_name)
	map_root = map_tree.getroot()
	# parse every topic mentioned in ditamap
	for topicref in map_root.iter('topicref'):
		# parse dita file with name that is in href
		new_dita_filename = rename_files(topicref) + '.dita'
		# rename file in ditamap
		topicref.set('href', new_dita_filename)
		map_tree.write(ditamap_name)
		print('Updated in ditamap:', topicref.attrib)
		print()

	ditamap_header = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE map\n  PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">\n'
	append_header(ditamap_name, ditamap_header)


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
			 	os.system('notepad.exe ' + os.path.join(folder, file))
					


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
	print('Files with missing shortdesc tag:', len(problematic_files))
	
	# Open files prompt
	while True:
		openfiles = input('Open files one by one? (y/n) ')
		if openfiles == 'n':
			# Save files prompt
			while True:
				savefiles = input('Save file list to document? (y/n) ')
				if savefiles == 'n':
					print('Press any key to exit.')
					break
				elif savefiles == 'y':
					open('status.txt', 'w').close() # clear the contents
					status = open('status.txt', 'a')
					status.write('Folder:\n' + folder + '\n\nEdit shortdescs in the following files:\n\n')
					for f in problematic_files:
						status.write(f + '\n')
					status.close()
					print('Wrote to file "status.txt" in the script folder. Press any key to exit.')
					break
			break
		elif openfiles == 'y':
			for file in problematic_files:
				os.system('notepad.exe ' + os.path.join(folder, file))
			print('Press any key to exit.')
			break




## DONE: show a list of files with missing title or shortdesc in Notepad, put cursor at the problematic spot
## DONE: Revision history, printing instructions, confidentiality notice- add predefined shortdescs
# TODO: process libvar correctly
## DONE: user input of map, get folder location from map location
# TODO: Tkinter interface to select the map file
# TODO: topic titles in Sentence case
# TODO: add 'img_<userinput>_meaningful_name' to images (track them by GUID and convert fig titles)
# TODO: insert &nbsp between auxiliary tables

if __name__ == '__main__':

	#ditamap_name = r'C:\hp_cheetahr5\CA493-04620 - Stock Storage Guidelines\Step1_Transform\CA493-04620.ditamap'
	ditamap_name = input('Enter full address of the DITA map you want to process (C:\\hpcheetahr5\\...\\*.ditamap):\n')
	#ditamap_name = os.path.abspath(fd.askopenfilename(filetypes=[('DITA maps', '.ditamap')]))
	folder, ditamap_shortname = os.path.split(ditamap_name)
	rename_folder_items(ditamap_name)
	mass_edit(folder)
	view_shortdescriptions(folder)

	m.getch() # prevent Windows from closing the terminal
