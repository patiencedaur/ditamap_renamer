from marytreat.core.tridionclient import LOV

# while True:
lov = input('Enter value name: ')
if lov.startswith('f'):  # example: 'fhpisuppresstitlepage' (ishfield) instead of 'dhpisuppresstitlepage'
    lov = 'd' + lov[1:]
xml = LOV.get_value_tree(lov)
for ishlovvalue in xml.iter('ishlovvalue'):
    value = ishlovvalue.attrib.get('ishref')
    label = ishlovvalue.find('label')
    print(value)
    print(label.text)
    print()
