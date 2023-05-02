from marytreat.core.tridionclient import DocumentObject
import uuid
from lxml import etree


def validate(user_input):
    try:
        uuid.UUID(user_input.strip())  # mask: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        return user_input.strip()
    except ValueError:
        try:
            uuid.UUID(user_input[5:])  # mask: GUID-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            return user_input
        except ValueError:
            tree = etree.fromstring(user_input)  # Ctrl-C - Ctrl-V from Publication Manager
            obj = tree.find('ishobject')
            object_guid = obj.attrib.get('ishref')
            try:
                uuid.UUID(object_guid[5:])  # mask: GUID-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                return object_guid
            except ValueError:
                return -1


def get_guid(prompt):
    """
    Validate input as GUID or ishobject string.
    :param prompt: A prompt that explains to the user what they need to enter
    :return: GUID of the object
    """
    while True:
        input_id = input(prompt)
        if input_id == 'done' or input_id == '"done"':
            return input_id
        input_id = validate(input_id)
        if input_id != -1:
            return input_id


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
