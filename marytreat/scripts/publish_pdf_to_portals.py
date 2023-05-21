import _initialize
from marytreat.core.tridionclient import Publication
from _validator import get_guid_from_cli

guid = get_guid_from_cli('Enter publication GUID or copy the publication (p_***) string here: ')

pub = Publication(id=guid)
pub.publish_to_portals()
