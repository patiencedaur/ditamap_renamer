from marytreat.core.tridionclient import Publication, Metadata
from _validator import get_guid

guid = get_guid('Enter publication GUID or copy the publication (p_***) string here: ')

pub = Publication(id=guid)
pub.publish_to_portals()
