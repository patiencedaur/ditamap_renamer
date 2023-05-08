import sys
import os

sys.path.append(os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)))))

from marytreat.core.tridionclient import DocumentObject
from _validator import get_guid


guid = get_guid('Enter object to copy metadata from: ')

src_obj = DocumentObject(id=guid)
fhpiproduct, fhpicss, fhpiregion = src_obj.get_current_dynamic_delivery_metadata()

if not fhpiproduct:
    print('Object', src_obj, 'has no product data.')
else:
    print('Object', src_obj, 'has product data:', fhpiproduct)
if not fhpicss:
    print('Object', src_obj, 'has no customer support stories.')
else:
    print('Object', src_obj, 'has customer support story:', fhpicss)

targets = []
print('\nTarget objects are the objects to copy the metadata to.\n',
      'Input the GUIDs or copied strings of target object. Press Enter after every item.\n',
      'When you are done, print "done" in the command line.\n')
while True:
    target_id = get_guid('Enter target object or "done": ')
    if target_id == 'done' or target_id == '"done"':
        break
    elif target_id:
        targets.append(target_id)

print('The following metadata will be copied.')
if fhpicss:
    print('Customer support stories:', fhpicss)
if fhpiproduct:
    print('Product data:', fhpiproduct)
print('Target objects will be affected:')
print(targets)
continue_or_not = input('Continue? y/n ')
if continue_or_not == 'y':
    for target_id in targets:
        target = DocumentObject(id=target_id)
        target.set_metadata_for_dynamic_delivery(fhpiproduct, fhpicss)

print('Dynamic Delivery metadata copied.')
