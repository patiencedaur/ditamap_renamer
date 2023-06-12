import uuid

import _initialize
from uuid import uuid5, NAMESPACE_OID
from lxml import etree
from pathlib import Path
from msvcrt import getch

"""
Generates a .3sish file for a .dita topic.
"""


def gen_guid(path_obj):
    """
    :param path_obj: Path("C:\...path\to\file.dita")
    :return: GUID-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """
    guid = uuid5(NAMESPACE_OID, path_obj.stem)
    return 'GUID-' + str(guid).upper()


def get_fmoduletype(root):
    """
    :param root: lxml.etree.Element
    :return: lxml.etree.Element(tag='ishfield')
    """
    outputclass = root.attrib.get('outputclass')
    if outputclass == 'referenceinformation':
        fmoduletype = 'Reference Information'
    else:
        fmoduletype = outputclass.capitalize()
    return fmoduletype


def guidize(path_obj):
    # Get GUID, if there isn't, then generate one
    # Add new GUID to the object XML code
    ditatree = etree.parse(path_obj)
    ditaroot = ditatree.getroot()
    guid = ditaroot.attrib.get('id')
    try:
        uuid.UUID(guid[5:])
    except ValueError:
        guid = gen_guid(path_obj)
        ditaroot.set('id', guid)
        ditatree.write(path_obj)
    return guid


def gen_ishfields(path_obj):
    """
    :param path_obj: Path("C:\...path\to\file.dita")
    :return: Ishfields etree.Element containing several ishfields
    """
    if not isinstance(path_obj, Path):
        path_obj = Path(path_obj)
    if not path_obj.exists():
        raise FileNotFoundError('Path does not exist: ' + str(path_obj))
    if path_obj.suffix == '.dita':
        root = etree.parse(path_obj).getroot()
    else:
        print('This is neither a topic not a map. Why would you need an ish file for it? Exiting.')
        return

    title_text = path_obj.stem
    print(title_text)
    ftitle = etree.Element('ishfield', attrib={
        'name': 'FTITLE',
        'level': 'logical',
    })
    ftitle.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    ftitle.text = title_text

    version = etree.Element('ishfield', attrib={
        'name': 'VERSION',
        'level': 'version',
    })
    version.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    version.text = '1'

    doclanguage = etree.Element('ishfield', attrib={
        'name': 'DOC-LANGUAGE',
        'level': 'lng',
    })
    doclanguage.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    doclanguage.text = 'en-US'

    searchable = etree.Element('ishfield', attrib={
        'name': 'FHPISEARCHABLE',
        'level': 'logical',
    })
    searchable.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    searchable.text = 'Yes'

    fmoduletype_text = get_fmoduletype(root)
    fmoduletype = etree.Element('ishfield', attrib={
        'name': 'FMODULETYPE',
        'level': 'logical',
    })
    fmoduletype.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    fmoduletype.text = fmoduletype_text

    ishfields = etree.Element('ishfields')
    ishfields.append(ftitle)
    ishfields.append(version)
    ishfields.append(doclanguage)
    ishfields.append(searchable)
    ishfields.append(fmoduletype)

    guid = guidize(path_obj)

    ishobject = etree.Element('ishobject', attrib={
        'ishref': guid,
        'ishtype': 'ISHModule'
    })
    ishobject.append(ishfields)

    return ishobject


def write_ish_file(ditapath_obj):
    """
    Creates a .3sish file on disk.
    :param ditapath_obj: Path(C:\..path\to\dita_file.dita)
    """

    if not isinstance(ditapath_obj, Path):
        ditapath_obj = Path(ditapath_obj)

    ishtree = gen_ishfields(ditapath_obj)
    etree.dump(ishtree)

    content = etree.tostring(ishtree, encoding='utf-8', pretty_print=True, xml_declaration=True)
    content = content.decode()
    ish_path = Path(ditapath_obj.parent / ditapath_obj.with_suffix('.3sish'))
    with open(ish_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Wrote ' + str(ish_path))


if __name__ == '__main__':
    uinput = input('Enter path to DITA topic to create an ish file: ')
    path = Path(uinput.strip('"'))
    write_ish_file(path)
