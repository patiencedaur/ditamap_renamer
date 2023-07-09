import _initialize
from ish_generator import write_ish_file
from marytreat.core.local import LocalMap
from pathlib import Path
from msvcrt import getch

"""
This script operates on a DITA map.
It creates GUIDs for DITA topics that don't have them and puts them in the topic XML code.
It also creates an ISH file for each topic.
In this way, it facilitates work with SDL Tridion Docs Content Importer.
"""


def get_map_from_folder(folder: str):
    folder = folder.strip()
    mp = None
    for f in Path(folder).iterdir():
        print(f)
        if f.suffix == '.ditamap':
            mp = f
    if not mp:
        raise FileNotFoundError('No map found in folder. Exiting')
    dmap = LocalMap(str(mp))
    return dmap


uinput = input('Enter folder to guidize: ')
ditamap = get_map_from_folder(uinput)
for t in ditamap.topics:
    write_ish_file(t.path)

print('Press any key to exit.')
getch()



