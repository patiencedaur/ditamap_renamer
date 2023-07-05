import _initialize
from marytreat.core.tridionclient import Publication
from _validator import get_guid_from_cli
from msvcrt import getch

guid = get_guid_from_cli('Enter publication GUID or copy the publication (p_***) string here: ')

pub = Publication(id=guid)
pub.publish_to_portals()

print('Set Publish to Portals to Yes for {}. Press any key to quit'.format(guid))

getch()
