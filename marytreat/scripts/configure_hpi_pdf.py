from marytreat.core.tridionclient import Publication, Metadata
import uuid
from lxml import etree

"""
Fill in metadata for an existing HPI PDF publication output format.
This script is a workaround for a bug in Publication Manager
that hides dropdown menus when the screen is zoomed to 150%. 
"""


while True:
    guid = input('Enter publication GUID or copy the publication string here: ')
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
pub.set_hpi_pdf_metadata()

while True:
    is_customer_viewable = input('Should this project have a colored cover? y/n ')
    if is_customer_viewable == 'n':
        break
    elif is_customer_viewable == 'y':
        pub.set_metadata(Metadata(('FHPISUPPRESSTITLEPAGE', 'VHPISUPPRESSTITLEPAGEYES')), level='lng')
        break

print('Done!')
