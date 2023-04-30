from marytreat.core.tridionclient import LOV
from marytreat.core.constants import Constants
from lxml import etree

# while True:
lov = input('Enter value name: ')
# if lov.upper() in Constants.ISHFIELDS.value.keys():
xml = LOV.get_value_tree(lov)
for ishlovvalue in xml.iter('ishlovvalue'):
    value = ishlovvalue.attrib.get('ishref')
    label = ishlovvalue.find('label')
    print(value)
    print(label.text)
    print()
