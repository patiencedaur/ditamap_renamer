import _initialize
from marytreat.core.tridionclient import Publication, Metadata
from _validator import get_guid_from_cli

"""
Fill in metadata for an existing HPI PDF publication output format.
This script is a workaround for a bug in Publication Manager
that hides dropdown menus when the screen is zoomed to 150%. 
"""

guid = get_guid_from_cli('Enter publication GUID or copy the publication string here: ')

pub = Publication(id=guid)
print('Processing', pub, '...')
pub.set_hpi_pdf_metadata()
#
# while True:
#     is_customer_viewable = input('Should this project have a colored cover? y/n ')
#     if is_customer_viewable == 'n':
#         pub.set_metadata(Metadata(('FHPISUPPRESSTITLEPAGE', 'VHPISUPPRESSTITLEPAGENO')), level='lng')
#         break
#     elif is_customer_viewable == 'y':
#         pub.set_metadata(Metadata(('FHPISUPPRESSTITLEPAGE', 'VHPISUPPRESSTITLEPAGEYES')), level='lng')
#         break

print('HPI PDF output configured.')
