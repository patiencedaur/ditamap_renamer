import _initialize

from marytreat.core.tridionclient import Map, Topic
from _validator import get_guid

"""
Wraps a topic in a map.
You can copy and paste inputs from the Publication Manager.
In this case, make sure to save and update the publication in the Publication Manager GUI
after every run. You will see the new map appear in the publication tree.
Check out the root map to make the small yellow triangle disappear.
"""

root_map_guid = get_guid('Enter root map guid or data: ')
topic_guid = get_guid('Enter topic guid or data: ')

root_map = Map(id=root_map_guid)
topic = Topic(id=topic_guid)

sbmp = topic.wrap_in_submap(root_map)

print()
print('Wrapped', topic, 'in', sbmp)
print('Root map:', root_map)
