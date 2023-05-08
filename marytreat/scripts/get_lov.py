import _initialize
from marytreat.core.tridionclient import LOV

lov = input('Enter value name: ')
if lov.startswith(('f', 'F')):  # example: 'fhpisuppresstitlepage' (ishfield) instead of 'dhpisuppresstitlepage'
    lov = 'D' + lov[1:]
xml = LOV.get_value_tree(lov.upper())
for ishlovvalue in xml.iter('ishlovvalue'):
    value = ishlovvalue.attrib.get('ishref')
    label = ishlovvalue.find('label')
    print(value)
    print(label.text)
    print()
