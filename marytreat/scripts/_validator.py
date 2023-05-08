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
            obj = tree.xpath('/ishobjects/ishobject')[0]
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
