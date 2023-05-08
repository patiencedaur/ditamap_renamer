import sys
import os

sys.path.append(os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)))))

from marytreat.core.tridionclient import Publication
from _validator import get_guid

guid = get_guid('Enter publication GUID or copy the publication (p_***) string here: ')

pub = Publication(id=guid)
pub.publish_to_portals()
