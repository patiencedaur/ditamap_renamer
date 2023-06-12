import _initialize
from ish_generator import write_ish_file
from clear_attribute import get_map_from_folder

"""
This script operates on a DITA map.
It creates GUIDs for DITA topics that don't have them and puts them in the topic XML code.
It also creates an ISH file for each topic.
In this way, it facilitates work with SDL Tridion Docs Content Importer.
"""

uinput = input('Enter folder to guidize: ')
ditamap = get_map_from_folder(uinput)
for t in ditamap.topics:
    write_ish_file(t.path)



