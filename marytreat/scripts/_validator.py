import uuid
from lxml import etree
import re
from sys import stdout
from getpass import getpass


def validate(user_input):
    try:
        uuid.UUID(user_input.strip())  # mask: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        return user_input.strip()
    except ValueError:
        try:
            uuid.UUID(user_input[5:])  # mask: GUID-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            return user_input
        except ValueError:
            try:
                assert user_input.startswith('<ishobjects>')
            except AssertionError:
                return -1
            finally:
                ishobject_mask = r'(\<ishobjects\>\<ishobject\ ishtype=\"(.*?)\"\ ishref=\")(?P<GUID>.*?)\"'
                match = re.search(ishobject_mask, user_input)
                object_guid = match.group('GUID')
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
