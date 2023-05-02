from marytreat.core.tridionclient import Publication, Metadata
import uuid
from lxml import etree

while True:
    guid = input('Enter publication GUID or copy the publication (p_***) string here: ')
    try:
        uuid.UUID(guid)
        break
    except ValueError:
        tree = etree.fromstring(guid)
        obj = tree.find('ishobject')
        guid = obj.attrib.get('ishref')
        try:
            uuid.UUID(guid[5:])
            break
        except ValueError:
            continue

pub = Publication(id=guid)
pub.publish_to_portals()
