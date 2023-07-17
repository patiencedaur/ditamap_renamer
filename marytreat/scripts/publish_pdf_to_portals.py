import _initialize
from marytreat.core.tridionclient import Publication
from _validator import get_guid_from_cli
from msvcrt import getch

try:
    guid = get_guid_from_cli('Enter publication GUID or copy the publication (p_***) string here: ')

    pub = Publication(id=guid)
    pub.publish_to_portals()
except Exception as e:
    print('Cannot publish {} to portals. Reason:\n{}'.format(guid, e))
    getch()
