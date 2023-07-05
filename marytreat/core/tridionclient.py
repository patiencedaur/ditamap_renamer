import base64
import datetime
import random
import re
from copy import deepcopy
from pathlib import Path
from functools import wraps, reduce
from os import environ, path

from lxml import etree
from requests import Session
from zeep import Client, Transport, exceptions

from marytreat.core.constants import Constants
from marytreat.core.ishfields import IshField
from marytreat.core.mary_debug import logger, debugmethods
from marytreat.core.mary_xml import XMLContent

"""
A Python client for SDL Tridion Docs. Created for HP Indigo by Dia Daur.
"""

user_folder = environ['USERPROFILE']

token = None


def check_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global token
        if token is None:
            token = Auth.get_token()
        return func(*args, **kwargs)

    return wrapper


def requires_token(cls):
    for k, v in vars(cls).items():
        if callable(v):
            setattr(cls, k, check_token(v))
    return cls


class Metadata:

    def __init__(self, *args: tuple[str, str | int] | IshField | list[IshField]) -> None:
        """
        Usage:
        from_tuples = Metadata(('ftitle', 'MyGreatTitle'), ('fresources', 'GUID-666'))
        from_ishfields = Metadata(IshField('ftitle', 'MyCuteTitle'), IshField('fishmasterref': some_guid))
        from_list = Metadata([IshField('ftitle', 'I like lists'), IshField('fstatus', 'VSTATUSDRAFT')])
        :param args: Metadata objects, tuples, list
        """
        self.ishfields: list[IshField] = []
        if len(args) == 0:
            return
        if len(args) == 1 and isinstance(args[0], list):
            args = args[0]
        for arg in args:
            if isinstance(arg, IshField):
                self.ishfields.append(arg)
            elif isinstance(arg, tuple):
                self.ishfields.append(IshField(arg[0], arg[1]))
            else:
                logger.critical(self.__init__.__doc__)

    def __repr__(self) -> str:
        meta_repr = 'Metadata['
        for ishfield in self.ishfields:
            meta_repr += ishfield.__repr__() + ',\n'
        meta_repr += ']'
        return meta_repr

    def __iter__(self):
        return iter(self.ishfields)

    def __next__(self):
        return next(self.__iter__())

    def __len__(self) -> int:
        return len(self.ishfields)

    @property
    def pack(self) -> str:
        request = ''
        for ishfield in self.ishfields:
            request += ishfield.xml_form
        return '<ishfields>' + request + '</ishfields>'

    @property
    def dict_form(self) -> dict[str, dict[str, str]]:
        d = {}
        for ishfield in self.ishfields:
            d.update(ishfield.dict_form)
        return d

    def __add__(self, other):
        if isinstance(other, Metadata):
            return Metadata(self.ishfields + other.ishfields)
        elif isinstance(other, IshField):
            self.ishfields.append(other)
            return self

    def add_field(self, ishfield: IshField) -> None:
        self.ishfields.append(ishfield)

    def remove_field(self, ishfield: IshField) -> None:
        self.ishfields.remove(ishfield)


class Unpack:
    """
    Turn xml responses into Metadata objects
    """

    @staticmethod
    def wrap(bad_xml: str) -> str:
        regex = r'(<\?xml version="1.0" encoding="utf-16"\?>)'
        return re.sub(regex, r'\1<root>', bad_xml) + '</root>'

    @staticmethod
    def to_metadata(xml, search_mode: str = None) -> list[tuple[Metadata, str | int]] | list[str] | Metadata:
        if search_mode == 'ishfolders':
            xml = Unpack.wrap(xml)
            subfolder_ids: list[tuple[Metadata, str | int]] = Unpack.subfolder_ids(xml)
            return subfolder_ids
        if search_mode == 'ishobjects':
            object_ids: list[str] = Unpack.object_ids(xml)
            return object_ids
        if not search_mode:
            root = Unpack.to_tree(xml)
            fields = []
            for ishfield in root.iter('ishfield'):
                fld_text = '' if ishfield.text is None else ishfield.text
                fld = IshField(ishfield.attrib.get('name'), fld_text)
                fields.append(fld)
            metadata: Metadata = Metadata(fields)
            return metadata

    @staticmethod
    def subfolder_ids(xml: str) -> list[tuple[Metadata, str | int]]:
        multiple_objects: list[tuple[Metadata, str | int]] = []
        root = Unpack.to_tree(xml)
        for ish_thing in root.iter('ishfolder'):
            ish_thing_id = ish_thing.attrib.get('ishfolderref')
            fields_list: list[IshField] = []
            for ishfield in ish_thing.iter('ishfield'):
                fld_text = '' if ishfield.text is None else ishfield.text
                fld = IshField(ishfield.attrib.get('name'), fld_text)
                fields_list.append(fld)
            fields: Metadata = Metadata(fields_list)
            multiple_objects.append((fields, ish_thing_id))
        return multiple_objects[1:]  # remove parent

    @staticmethod
    def object_ids(xml: str) -> list[str]:
        guids: list = []
        root = Unpack.to_tree(xml)
        for ishobject in root.iter('ishobject'):
            guid = ishobject.attrib.get('ishref')
            guids.append(guid)
        return guids

    @staticmethod
    def to_tree(xml: str) -> etree.Element:
        return etree.fromstring(xml.encode('utf-16'))


@requires_token
class Tag:

    def __init__(self, name: str) -> None:
        self.hostname = Constants.HOSTNAME + 'MetadataBinding25.asmx?wsdl'
        self.service = Client(self.hostname, service_name='MetadataBinding25',
                              port_name='MetadataBinding25Soap').service
        self.name = name
        self.level = IshField.f.get(name.upper()).get('level').lower()

    def save_possible_values_to_file(self) -> str:
        xml = self.service.RetrieveTagStructure(token,
                                                psFieldName=self.name.upper(),
                                                psFieldLevel=self.level)['psXMLFieldTags']
        # with open('tag.xml', 'w', encoding='utf-8') as f:
        #     f.write(xml)
        root = Unpack.to_tree(xml)
        filename = path.join(user_folder, self.name + '-' + datetime.date.today().isoformat() + '.csv')
        with open(filename, 'w', encoding='utf-8') as dest:
            for tag in root.iter('tag'):
                selectable = tag.find('selectable').text
                if selectable == 'false':
                    continue
                key = tag.find('label').text
                value = tag.attrib.get('id')
                dest.write(str(key).rstrip() + ',' + '\t"' + str(value).rstrip() + '"\n')
        return filename


@requires_token
class LOV:

    def __init__(self):
        self.hostname = Constants.HOSTNAME + 'ListOfValues25.asmx?wsdl'
        self.service = Client(self.hostname, service_name='ListOfValues25', port_name='ListOfValues25Soap').service

    def get_value_tree(self, dname: str):
        xml = self.service.RetrieveValues(psAuthContext=token,
                                          pasFilterLovIds=dname.upper(),
                                          peActivityFilter='None',
                                          )['psOutXMLLovValueList']
        return Unpack.to_tree(xml)


@debugmethods
class Auth:

    @staticmethod
    def get_token():
        try:
            service = Client(Constants.HOSTNAME + 'Application25.asmx?wsdl',
                             service_name='Application25',
                             port_name='Application25Soap',
                             transport=Transport(session=Session())).service

            # client = Client(hostname + 'Application25.asmx?wsdl', wsse=UsernameToken(username, password))
            response = service.Login('InfoShareAuthor', Constants.USERNAME, Constants.PASSWORD)
            tkn = response['psOutAuthContext']
            logger.info('Login token: ' + tkn)
            return tkn
        except Exception as e:
            logger.warning('Working offline. Server functions are disabled\n' + str(e))

    @staticmethod
    def get_dusername():
        tree = LOV().get_value_tree('username')
        for ishlovvalue in tree.iter('ishlovvalue'):
            label = ishlovvalue.find('label')
            if label.text == Constants.USERNAME.value:
                return ishlovvalue.attrib.get('ishref')


@requires_token
class BaseTridionDocsObject:
    """
    'Glue' class to allow future tree work.
    """
    name: str
    folder_id: str
    id: str | int


@debugmethods
class DocumentObject(BaseTridionDocsObject):

    def __init__(self, name=None, folder_id=None, id=None) -> None:
        if name and folder_id and not id:
            self.name = name
            self.folder_id = folder_id
        elif id and not name and not folder_id:
            self.id = id  # use get_name() in this case
        self.hostname = Constants.HOSTNAME + 'DocumentObj25.asmx?wsdl'
        self.service = Client(self.hostname, service_name='DocumentObj25', port_name='DocumentObj25Soap').service

    def get_name(self):
        if not hasattr(self, 'name'):
            name_request_metadata = Metadata(('ftitle', ''))
            name_response = self.get_metadata(name_request_metadata)
            self.name = name_response.dict_form.get('FTITLE').get('text')
        return self.name

    def __repr__(self) -> str:
        return '<' + self.id + '>'

    def set_metadata(self, metadata: Metadata, level='logical') -> None:
        self.service.SetMetadata(token, self.id, psVersion=1, psLanguage='en-US',
                                 psXMLMetadata=metadata.pack)
        logger.info('Set metadata: ' + str(metadata) + ' for object: ' + str(self))

    def get_metadata(self, metadata: Metadata) -> Metadata:
        request: str = metadata.pack
        xml = self.service.GetMetaData(token, self.id, psVersion=1, psXMLRequestedMetaData=request)[
            'psOutXMLObjList']
        return Unpack.to_metadata(xml)

    def get_parent_folder_id(self) -> int | str:
        meta: dict = self.service.FolderLocation(token, self.id, peOutBaseFolder='Data')
        folder_id = meta['palOutFolderRefs']['long'][-1]
        return folder_id

    def set_metadata_for_dynamic_delivery(self, product: int | str = None, css: int | str = None):
        logger.info('Setting metadata: ' + str(locals()) + ' for ' + str(self))
        # ignores empty values
        if product:
            set_product: Metadata = Metadata(('fhpiproduct', product))
            self.set_metadata(set_product)

        if css:
            set_css: Metadata = Metadata(('fhpicustomersupportstories', css))
            self.set_metadata(set_css)

        worldwide = '205101142445494286415257'
        consistent_metadata = Metadata(('fhpiregion', worldwide), ('fhpisearchable', 'yes'))
        self.set_metadata(consistent_metadata)

        logger.info('Filled mandatory metadata for ' + str(self))

    def get_current_dynamic_delivery_metadata(self) -> tuple:
        mandatory_metadata: Metadata = Metadata(('fhpiproduct', ''), ('fhpicustomersupportstories', ''),
                                                ('fhpiregion', ''))
        get_meta: Metadata = self.get_metadata(mandatory_metadata)
        fhpiproduct: dict[str, str] = get_meta.dict_form.get('FHPIPRODUCT')
        fhpicss: dict[str, str] = get_meta.dict_form.get('FHPICUSTOMERSUPPORTSTORIES')
        fhpiregion: dict[str, str] = get_meta.dict_form.get('FHPIREGION')
        current_dd_meta = [field.get('text') if field is not None else ''
                           for field in (fhpiproduct, fhpicss, fhpiregion)]
        return tuple(current_dd_meta)

    def apply_dynamic_delivery_metadata_from_source(self,
                                                    source_metadata: tuple[str | int, str | int, str | int]) -> None:
        fhpiproduct = source_metadata[0]
        fhpicss = source_metadata[1]
        self.set_metadata_for_dynamic_delivery(product=fhpiproduct, css=fhpicss)

    def duplicate_dynamic_delivery_metadata(self, *args) -> None:
        dd_metadata: tuple[str | int, str | int, str | int] = self.get_current_dynamic_delivery_metadata()
        for arg in args:
            assert isinstance(arg, DocumentObject)
            arg.apply_dynamic_delivery_metadata_from_source(dd_metadata)

    def get_object_as_tree(self) -> etree.Element:
        logger.info('id: ' + str(self.id))
        content = self.service.GetObject(token, self.id, psVersion=1,
                                         psLanguage='en-US')['psOutXMLObjList']
        root = Unpack.to_tree(content)
        return root

    def get_decoded_content_as_tree(self) -> etree.Element:
        root = self.get_object_as_tree()
        content: str = ''
        for ishdata in root.iter('ishdata'):
            content = base64.b64decode(ishdata.text).decode('utf-16')
        content.replace(' encoding="UTF-16"', '')  # etree doesn't like encoding declarations
        root = etree.fromstring(content.encode('utf-16'))
        return root

    def delete(self) -> None:
        try:
            self.service.Delete(token, psLogicalId=self.id)
        except exceptions.Fault:
            logger.error('Failed to delete object. Possible reasons:\n' +
                         '- Object is referenced by another object\n' +
                         '- Object is a root map\n' +
                         '- One of the languages is used in a released publication output\n' +
                         '- One of the languages is released, and you are no Administrator\n' +
                         '- One of the languages is checked out, and you are no Administrator')

    def upload(self, data: bytes):
        """
        Encode and upload new content back to the server.
        :param data: XML root
        """
        self.service.Update(token, psLogicalId=self.id, psVersion='1', psLanguage='en-US',
                            psEdt='EDTXML', pbData=data)


@debugmethods
@requires_token
class PDFObject(DocumentObject):

    def __init__(self, name: str = None, folder_id: int | str = None, id: str = None):
        super().__init__(name, folder_id, id)
        self.type = 'ISHTemplate'
        if name and folder_id and not id:
            self.id = self.create()

    def create(self):
        folder_type = 'ISHTemplate'
        with open('../templates/pdf.pdf', 'rb') as template:
            pbdata = template.read()
        author = Auth.get_dusername()
        request: str = Metadata(
            IshField('ftitle', self.name),
            IshField('fstatus', 'VSTATUSDRAFT'),
            IshField('fauthor', author),
        ).pack

        response = self.service.Create(token, self.folder_id, folder_type, psVersion='new',
                                       psLanguage='en-US',
                                       psXMLMetadata=request, psEdt='EDTPDF', pbData=pbdata)
        id = response['psLogicalId']
        return id

    def fill_in_scitex_metadata(self,
                                disc_level='287477763180518087286275037723076',
                                product='18576095',
                                name=None,
                                map_type=None
                                ) -> None:
        """
        Default values are for Scitex PDF documents.
        :param disc_level: Disclosure level code
        :param product: Product code
        :param name: ex. 'Cleaning Anilox Rollers'
        :param map_type: ex. 'troubleshootingmap'
        :return: None
        """
        metadata = Metadata(
            IshField('FHPIDISCLOSURELEVEL', disc_level),
            IshField('FHPIPRODUCT', product),
            IshField('FHPIREGION', '205101142445494286415257'),
        )
        if map_type:
            metadata += IshField('FHPITEMPLATETYPE', map_type)

        self.set_metadata(metadata)
        if not name:
            self.name = self.get_name()
        # lng-level metadata needs to be set after logical level, otherwise it gets deleted in Tridion Docs
        self.set_metadata(Metadata(IshField('FHPITOPICTITLE', self.name)))


@requires_token
class Map(DocumentObject):

    def __init__(self, name: str = None, folder_id: str = None, id: str = None,
                 data=bytes('<?xml version="1.0" encoding="utf-8"?>\n' +
                            '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd"[]>\n' +
                            '<map></map>', 'utf-8'), map_type: str = None):
        """
        Usage:
        my_new_map = Map(name='My Awesome Map', folder_id='GUID-parent-folder-id')
        my_existing_map = Map(id='GUID-9876')
        """
        super().__init__(name, folder_id, id)
        self.type = 'ISHMasterDoc'
        if name and folder_id and not id:
            self.id = self.create(data, map_type)

    def create(self, data, map_type) -> str:
        folder_type = 'ISHMasterDoc'
        author = Auth.get_dusername()
        request = Metadata(
            IshField('ftitle', self.name),
            IshField('fstatus', 'VSTATUSDRAFT'),
            IshField('fauthor', author),
        )
        if map_type:
            request += IshField('fmastertype', map_type)
        response = self.service.Create(token, self.folder_id, folder_type, psVersion='new',
                                       psLanguage='en-US',
                                       psXMLMetadata=request.pack, psEdt='EDTXML', pbData=data)
        id = response['psLogicalId']
        return id


@requires_token
class LibVariable(DocumentObject):

    def __init__(self, name: str = None, folder_id: str = None, id: str = None, topic_guid: str = None):
        super().__init__(name, folder_id, id)
        self.type = 'ISHLibrary'
        if topic_guid and not id:  # copy library variable contents from a topic
            self.id = self.create_from_topic(topic_guid)

    def create_from_topic(self, topic_guid: str) -> str:
        topic: Topic = Topic(id=topic_guid)
        root: etree.Element = topic.get_object_as_tree()
        content = ''
        for ishdata in root.iter('ishdata'):
            content = base64.b64decode(ishdata.text).decode('utf-16')

        content.replace(' encoding="UTF-16"', '')  # etree doesn't like encoding declarations
        root = etree.fromstring(content.encode('utf-16'))
        new_root = etree.Element('topic')  # clear topic attributes
        for child in root:
            new_root.append(child)
        content = etree.tostring(new_root)
        header = '<?xml version="1.0" encoding="utf-8"?>\n' + \
                 '<!DOCTYPE topic PUBLIC "-//OASIS//DTD DITA Topic//EN" "topic.dtd"[]>'
        content = header + content.decode()

        pbdata: bytes = bytes(content, 'utf-8')
        author = Auth.get_dusername()
        request = Metadata(
            IshField('ftitle', self.name),
            IshField('fstatus', 'VSTATUSDRAFT'),
            IshField('fauthor', author),
            IshField('flibrarytype', 'VLIBRARYTYPEVARIABLESOURCE')
        ).pack

        response = self.service.Create(token, plFolderRef=self.folder_id,
                                       psIshType=self.type, psLanguage='en-US',
                                       psVersion='new', psXMLMetadata=request,
                                       psEdt='EDTXML', pbData=pbdata)['psLogicalId']
        return response


@requires_token
class Topic(DocumentObject):

    def __init__(self, name: str = None, folder_id: int | str = None, id: str = None) -> None:
        super().__init__(name, folder_id, id)

    def wrap_in_submap(self, root_map: Map, submap_type=None):
        """
        Create a map (submap) object in the maps subfolder.
        Edit the root map XML contents so that it includes the new submap, which is wrapped right around the self topic.
        Upload the root map back to the server.
        :return: new submap
        """

        # A submap needs a type not only as metadata, but also as part of the XML code, other.
        # Otherwise it won't publish. TODO: figure out how to add submap types

        map_folder_id = root_map.get_parent_folder_id()
        if not map_folder_id:
            logger.exception('Map subfolder not found for root map ' + str(root_map))
            raise Fault

        root_map_content = root_map.get_decoded_content_as_tree()

        self_xpath_in_root_map = '/map/topicref//topicref[@href="{}"]'.format(self.id)
        self_topicref = root_map_content.xpath(self_xpath_in_root_map)[0]

        # Put the new map into the server
        new_map_name = 'm_' + self.get_name()[2:]
        new_map_content = etree.Element('map')
        new_map_content.insert(0, deepcopy(self_topicref))
        new_map_string = etree.tostring(new_map_content, xml_declaration=True, encoding='utf-8',
                                        doctype='<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd"[]>')
        new_map = Map(name=new_map_name, folder_id=map_folder_id,
                      data=new_map_string, map_type=submap_type)

        # Put the new map into the root map
        new_map_topicref = etree.Element('topicref', attrib={
            'href': new_map.id,
            'format': 'ditamap'
        })

        parent_topicref = self_topicref.getparent()
        parent_topicref.replace(self_topicref, new_map_topicref)
        updated_root_map_data = etree.tostring(root_map_content,
                                               xml_declaration=True, encoding='utf-8',
                                               doctype='<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd"[]>'
                                               )
        root_map.upload(data=updated_root_map_data)

        return new_map


@requires_token
class Publication(BaseTridionDocsObject):
    disclosure_levels: dict[str, int | str] = {
        'For HP and Channel Partner Internal Use': 47406819852170807613486806879990,
        'HP and Customer Viewable': 287477763180518087286275037723076
    }

    def __init__(self, name: str = None, folder_id: str | int = None, id: str = None, metadata=Metadata()) -> None:
        """
        Usage:
        my_new_pub = Publication(name='My New Publication', folder_id=some_folder_guid)
        my_existing_pub = Publication(id='guid_that_exists_on_server')
        """
        self.hostname = Constants.HOSTNAME + 'PublicationOutput25.asmx?wsdl'
        self.service = Client(self.hostname, service_name='PublicationOutput25',
                              port_name='PublicationOutput25Soap').service
        if name and folder_id and not id:
            self.name = name
            self.folder_id = folder_id
            self.id = self.create()
        if id and not name and not folder_id:
            self.id = id
        self.metadata = metadata

    def create(self) -> str:
        meta: str = Metadata(
            IshField('ftitle', self.name),
            IshField('fhpipublishoneversion', 'true'),
            IshField('fishpubsourcelanguages', 'VLANGUAGEEN'),
            IshField('fishrequiredresolutions', 'VRESLOW'),
        ).pack
        pub_response = self.service.Create(token, self.folder_id, psVersion='new',
                                           psXMLMetadata=meta)
        return pub_response['psLogicalId']

    def get_hpi_pdf_metadata(self, metadata: Metadata) -> Metadata:
        xml = self.service.GetMetaData(token, self.id, psVersion=1,
                                       psOutputFormat='HPI PDF',
                                       psLanguageCombination='en-US',
                                       psXMLRequestedMetaData=metadata.pack)['psOutXMLObjList']
        return Unpack.to_metadata(xml)

    def get_metadata(self) -> Metadata:
        meta: str = Metadata(
            IshField('ftitle', ''),
            IshField('fusergroup', ''),
            IshField('fishmasterref', ''),
            IshField('fishresources', ''),
            IshField('fhpidisclosurelevel', '')
        ).pack
        xml = self.service.GetMetaData(token, self.id, psVersion=1, psXMLRequestedMetaData=meta)[
            'psOutXMLObjList']
        return Unpack.to_metadata(xml)

    def set_metadata(self, metadata: Metadata, level='logical', outputformat='HPI PDF') -> None:
        if level == 'lng':
            self.service.SetMetadata(token, self.id, psVersion=1, psXMLMetadata=metadata.pack,
                                     psOutputFormat=outputformat, psLanguageCombination='en-US')
        else:
            self.service.SetMetadata(token, self.id, psVersion=1, psXMLMetadata=metadata.pack)

    def set_usergroup(self) -> None:
        meta: Metadata = Metadata(('fusergroup', 'Indigo'))
        self.set_metadata(meta)

    def set_disclosure_level(self, disclosure_level: int) -> None:
        try:
            assert disclosure_level in Publication.disclosure_levels.values()
            meta = Metadata(
                ('fhpidisclosurelevel', disclosure_level)
            )
            self.set_metadata(meta)
        except AssertionError:
            logger.error('Use a disclosure level specified in the values of the' +
                         'Publication.disclosure_levels dictionary.')

    def add_map(self, map_object: Map) -> None:
        meta = Metadata(
            IshField('fishmasterref', map_object.id)
        )
        self.set_metadata(meta)

    def add_resource(self, var_object: LibVariable):
        meta: str = Metadata(
            IshField('fishresources', var_object.id)
        ).pack
        self.service.SetMetadata(token, self.id, psVersion=1, psXMLMetadata=meta)

    def get_map(self):
        meta = Metadata(
            IshField('fishmasterref', '')
        ).pack
        xml = self.service.GetMetaData(token, self.id, psVersion=1, psXMLRequestedMetaData=meta)[
            'psOutXMLObjList']
        map_data = Unpack.to_metadata(xml).dict_form
        map_id = map_data.get('FISHMASTERREF').get('text')
        return Map(id=map_id)

    def set_hpi_pdf_metadata(self):
        # Requires a created HPI PDF output
        meta = Metadata(
            ('fhpipresentationtarget', 'VHPIPRESENTATIONTARGETSCREEN'),
            ('fhpipagecountoptimized', 'VHPIPAGECOUNTOPTIMIZEDYES'),
            ('fhpichapterpagestart', 'VHPICHAPTERPAGESTARTNEXT.PAGE'),
            ('fhpinumberchapters', 'VHPINUMBERCHAPTERSYES'),
            ('fhpisecondarycolor', 'VHPISECONDARYCOLORBLUE.HP.2172C'),
            ('FHPISUPPRESSTITLEPAGE', 'VHPISUPPRESSTITLEPAGEYES')
        )
        self.set_metadata(meta, level='lng')

    def publish_to_portals(self):
        meta = Metadata(('fhpipublishtoportals', 'VHPIPUBLISHTOPORTALSYES')).pack
        # required_meta = Metadata(('fishoutputformatref', 'HPI PDF')).pack
        self.service.SetMetadata(token, self.id, psVersion=1, psXMLMetadata=meta,
                                 # psXMLRequiredCurrentMetadata=required_meta,
                                 psOutputFormat='HPI PDF', psLanguageCombination='en-US')
        logger.info('Set publication ' + self.id + ' to portal publishing')


@debugmethods
@requires_token
class Folder(BaseTridionDocsObject):

    def __init__(self, name: str = None, type: str = None, parent_id: int | str = None,
                 id: int | str = None, metadata: Metadata = Metadata([])):
        """
        Usage:
        new_folder = Folder(name='My New Folder', type='ISHPublication', parent_id='444444')
        existing_folder = Folder(id='55555')
        folder_from_metadata = Folder(metadata=my_metadata)
        """
        self.hostname = Constants.HOSTNAME + 'Folder25.asmx?wsdl'
        self.service = Client(self.hostname, service_name='Folder25', port_name='Folder25Soap').service

        self.id = id
        self.name = name
        self.type = type
        self.parent_id = parent_id
        self.metadata = metadata

        if name and type and parent_id and not id:
            new_folder_response = self.service.Create(token, self.parent_id, self.type, self.name,
                                                      plOutNewFolderRef=str(random.randrange(2 ^ 32)))
            self.id = new_folder_response['plOutNewFolderRef']
            logger.debug('Created folder: ' + str(self.id) + str(self.name))
        if metadata:
            self.name = self.metadata.dict_form.get('FNAME').get('text')
            self.type = self.metadata.dict_form.get('FDOCUMENTTYPE').get('text')

    def __repr__(self):
        r = '<Folder (' + str(self.id)
        if self.name:
            r = r + ' ' + str(self.name)
        r += ')>'
        return r

    def get_location(self) -> list[str | int]:
        response = self.service.FolderLocation(token, plFolderRef=self.id, peOutBaseFolder='Data')
        folder_location = response['palOutFolderRefs']['long']
        location = [str(item) for item in folder_location]
        return location

    def get_metadata(self, search_mode: str = None):
        """
        :return: Metadata object
        """
        logger.debug('Getting metadata...')
        meta: str = Metadata(('fname', ''), ('fishfolderpath', ''), ('fdocumenttype', '')).pack
        xml = self.service.GetMetaDataByIshFolderRef(token, plFolderRef=self.id,
                                                     psXMLRequestedMetaData=meta)['psOutXMLFolderList']
        if search_mode == 'ishfolders':
            return Unpack.to_metadata(xml, 'ishfolders')
        return Unpack.to_metadata(xml)

    @property
    def get_type(self) -> str:
        if self.type:
            return self.type
        else:
            return self.get_metadata().dict_form.get('FDOCUMENTTYPE').get('text')

    @property
    def get_name(self) -> str:
        if self.name:
            return self.name
        else:
            return self.get_metadata().dict_form.get('FNAME').get('text')

    def get_contents(self, search_mode: str = None) -> list[tuple[Metadata, str | int]] | list[str] | Metadata:
        """
        :return: list of Metadata objects (not Folder/Document/Publication objects), (optional) folder_ids
        'ishfolders': for folders with subfolders, returns the folder and the subfolders in a list
        'ishobjects': list of guids ['xxxx', 'yyyy']
        """
        if search_mode == 'ishfolders':
            xml = self.service.GetSubFoldersByIshFolderRef(token, plFolderRef=self.id)['psOutXMLFolderList']
            ishfolders: list[tuple[Metadata, str | int]] = Unpack.to_metadata(xml, 'ishfolders')
            return ishfolders
        elif search_mode == 'ishobjects':
            xml = self.service.GetContents(token, plFolderRef=self.id)['psOutXMLObjList']
            ishobjects: list[str] = Unpack.to_metadata(xml, 'ishobjects')
            return ishobjects
        elif not search_mode:
            if self.get_type == 'None' or self.get_type == 'ISHNone' or self.get_type == 'VDOCTYPENONE':  # folder with folders
                xml = self.service.GetSubFoldersByIshFolderRef(token, plFolderRef=self.id)['psOutXMLFolderList']
            else:
                xml = self.service.GetContents(token, plFolderRef=self.id)['psOutXMLObjList']
            metadata: Metadata = Unpack.to_metadata(xml)
            return metadata

    def get_subfolder_ids(self) -> list[tuple[Metadata, str | int]]:
        xml = self.service.GetSubFoldersByIshFolderRef(token, plFolderRef=self.id)['psOutXMLFolderList']
        return Unpack.subfolder_ids(xml)

    def locate_object_by_name_start(self, name_start: str) -> tuple[str, str]:
        """
        Returns an object from an object folder (not a folder with folders).
        :param name_start: string
        :return: object name, object guid
        """
        guids: list[str] = self.get_contents('ishobjects')

        def get_obj_name_from_guid(guid_no: str) -> str:
            req_metadata: str = Metadata(('ftitle', '')).pack
            xml = DocumentObject().service.GetMetaData(token, guid_no,
                                                       psXMLRequestedMetaData=req_metadata)['psOutXMLObjList']
            xml = Unpack.wrap(xml)
            obj_metadata: Metadata = Unpack.to_metadata(xml)
            object_name = [field.dict_form.get('FTITLE').get('text')
                           for field in obj_metadata if field is not None][0]
            return object_name

        if len(guids) == 1:
            return get_obj_name_from_guid(guids[0]), guids[0]
        else:
            for guid in guids:
                obj_name = get_obj_name_from_guid(guid)
                if obj_name.startswith(name_start):
                    return obj_name, guid

    def add_publication(self, project_name: str, disc_level: int | str) -> Publication:
        assert self.type == 'ISHPublication' or self.type == 'Publications'
        try:
            pub_name = 'p_' + project_name
            pub = Publication(name=pub_name, folder_id=self.id)
            pub.set_disclosure_level(disc_level)
            return pub
        except exceptions.Fault as e:
            logger.critical('Problem with the publication. Reason: ' + str(e))

    def create_subfolder_structure(self) -> None:
        """
        Creates folder structure for a new project.
        :param subfolder_names_types:
        :return:
        """
        subfolders = {
            'images': 'ISHIllustration',
            'maps': 'ISHMasterDoc',
            'publications': 'ISHPublication',
            'topics': 'ISHModule',
            'variables': 'ISHLibrary'
        }
        for f_name, f_type in subfolders.items():
            try:
                Folder(name=f_name, parent_id=self.id, type=f_type)
            except exceptions.Fault as e:
                logger.error('Failed to create subfolder ' + f_name + '. Reason: ' + str(e))

    def tag_all(self, **kwargs):
        guids: list[str] = self.get_contents('ishobjects')
        for guid in guids:
            obj = DocumentObject(id=guid)
            obj.set_metadata_for_dynamic_delivery(**kwargs)


@debugmethods
@requires_token
class Project:
    inner_folders = {
        ('images', 'media', 'Images'): ('ISHIllustration', 'Image'),
        ('maps', 'Maps', 'b_root_map'): ('ISHMasterDoc', 'Map'),
        ('publications', 'Publications', 'publication', 'a_publication'): ('ISHPublication', 'Publications'),
        ('topics', 'Topics'): ('ISHModule', 'Topic'),
        ('variables', 'Variables'): ('ISHLibrary', 'Library topic')
    }

    def __init__(self, name: str = None, id: str | int = None):
        """
        Project is basically a folder with bells and whistles.
        :param name: project folder name (FNAME value in metadata)
        :param id: project folder id
        """
        logger.debug('Creating project:', locals())
        if not id:
            logger.critical('Please provide the project\'s ID.')
            return
        self.id = id
        self.folder = Folder(id=self.id)
        if name:
            self.name = name
        else:
            self.name = self.folder.get_name
        self.subfolders = self.get_subfolders()  # that actually exist on the server

    def get_subfolders(self) -> dict[str, Folder]:
        subfolder_data: list[str] = self.folder.get_contents('ishfolders')
        subfolders: dict[str, Folder] = {}
        for metadata, folder_id in subfolder_data:
            name: str = metadata.dict_form.get('FNAME').get('text')
            # if in any key there is an item that looks like folder name
            for variants_list in Project.inner_folders.keys():
                if any(name == name_variant for name_variant in variants_list):  # if folder with this name exists
                    folder_obj: Folder = Folder(id=folder_id, metadata=metadata)
                    subfolders[name] = folder_obj
        return subfolders

    def create_subfolder(self, folder_name: str):  # -> dict[str, Folder] | None:
        if folder_name not in self.subfolders.keys():
            # if folder does not exist
            try:
                for variants, params in Project.inner_folders.items():
                    if folder_name in variants:
                        folder_type = params[0]
                        new_folder = Folder(name=folder_name, type=folder_type, parent_id=self.folder.id)
                        self.subfolders[folder_name] = new_folder
                        logger.debug(self.subfolders)
                        # return self.subfolders
            except exceptions.Fault as e:
                logger.critical('Problem with creating folder ' + folder_name +
                                '. Check in the Content Manager if it already exists\n' + str(e))

    def create_publication(self) -> Publication:
        pub_folder: Folder = self.subfolders.get('publications') or self.subfolders.get('Publications')
        pub_guids: list[str] = pub_folder.get_contents('ishobjects')
        if len(pub_guids) == 0:
            disclos_level: str | int = Publication.disclosure_levels.get('HP and Customer Viewable')
            try:
                pub = pub_folder.add_publication(self.name, disclos_level)
                return pub
            except exceptions.Fault:
                logger.critical('Problem with creating publication. ' +
                                'Check in the XMLContent Manager if it already exists')

        elif len(pub_guids) == 1:
            pub = Publication(id=pub_guids[0])
            return pub
        else:
            logger.critical('Too many publications in folder. ' +
                            'Please delete the unneeded publications in the Content Manager')

    def get_publication(self) -> Publication | None:
        pub_folder: Folder = self.subfolders.get('publications') or self.subfolders.get('Publications')
        pub_guids: list[str] = pub_folder.get_contents('ishobjects')
        if len(pub_guids) == 1:
            pub = Publication(id=pub_guids[0])
            return pub
        else:
            logger.error('The project should have only one publication. ' +
                         'Please check the Content Manager for missing/redundant files.')

    def get_or_create_root_map(self) -> Map:
        map_folder: Folder = self.subfolders.get('maps') or self.subfolders.get('Maps') \
                             or self.subfolders.get('b_root_map')
        map_name_and_guid: tuple[str, str] = map_folder.locate_object_by_name_start('rm_')
        if map_name_and_guid:
            map_obj = Map(id=map_name_and_guid[1])
        else:
            map_name = 'rm_' + self.name
            map_obj = Map(name=map_name, folder_id=map_folder.id)
        return map_obj

    def migrate_libvar_from_topic(self) -> LibVariable | None:
        topic_folder: Folder = reduce((lambda x, y: x or y),
                                      (map(self.subfolders.get, ('topics', 'Topics'))))
        var_folder: Folder = reduce((lambda x, y: x or y),
                                    (map(self.subfolders.get, ('variables', 'Variables'))))
        var_guids: list[str] = var_folder.get_contents('ishobjects')
        libvar_sources: tuple[str, str] = topic_folder.locate_object_by_name_start('v_')
        try:
            source_name, source_guid = libvar_sources
            assert len(var_guids) == 0
        except TypeError:
            logger.warning('Either library variable already exists or source topic was not found. ' +
                           'Check the Content Manager')
            source_name, source_guid = None, None
        except AssertionError:
            logger.warning("The libvar {} was already migrated".format(var_guids[0]))
            return

        try:
            var_obj = LibVariable(name=source_name, folder_id=var_folder.id, topic_guid=source_guid)
            return var_obj
        except TypeError:
            logger.warning('Library variable data not found in topic folder')

    def complete_migration(self) -> None:
        logger.info("Starting migration...")
        # check what folders exist already
        # get root folder content and check it against name variants
        for variants in Project.inner_folders.keys():
            # if folder with any of the name variants does not exist
            if all(variant not in self.subfolders.keys() for variant in variants):
                self.create_subfolder(variants[0])
        pub: Publication = self.create_publication()
        root_map: Map = self.get_or_create_root_map()
        logger.info('Root map: ' + str(root_map) + ', adding to publication...')
        pub.add_map(root_map)
        logger.info('Searching for library variable...')
        libvar: LibVariable = self.migrate_libvar_from_topic()
        try:
            if libvar.id:
                logger.info('Found ' + str(libvar) + ', adding to publication...')
                pub.add_resource(libvar)
        except AttributeError:
            logger.info('Library variable not found, continuing...')
        logger.info('Migration completed.')

    def create_folder_structure(self) -> dict[str, Folder]:
        for folder_name in Project.inner_folders.keys():
            self.create_subfolder(folder_name[0])
        return self.subfolders

    def check_for_titles_and_shortdescs(self):
        warnings = []
        topic_folder = self.subfolders.get('topics') or self.subfolders.get('Topics')
        if not topic_folder:
            not_exist = 'topics folder does not exist in project ' + self.name + '- skipping'
            warnings.append(not_exist)
            logger.warning(not_exist)
            return
        topic_guids: list[str] = topic_folder.get_contents('ishobjects')
        logger.debug(topic_guids)
        for topic_guid in topic_guids:
            logger.info('Checking ' + topic_guid + ' for titles and descriptions...')
            topic = Topic(id=topic_guid)
            topic_contents = XMLContent(root=topic.get_decoded_content_as_tree())
            apply_filter = (topic_contents.outputclass is not None and topic_contents.outputclass not in (
                'frontcover', 'backcover', 'legalinformation', 'lpcontext'))
            if apply_filter and (topic_contents.title_missing() or topic_contents.shortdesc_missing()):
                topic_name = topic.get_metadata(Metadata(('ftitle', ''))).dict_form.get('FTITLE').get('text')
                if topic_contents.title_missing():
                    report = 'Title missing:\n' + topic_name + '\n'
                    warnings.append(report)
                if topic_contents.shortdesc_missing():
                    report = 'Shortdesc missing:\n' + topic_name + '\n'
                    warnings.append(report)
        if len(warnings) > 0:
            status_file = Path.joinpath(Path.home(), self.name + '_titles_shortdescs.txt')
            msg = 'Project ' + self.name + ' not ready for Dynamic Delivery.' + \
                  '\n\n' + 'Status written to file ' + str(status_file) + \
                  '\nProblematic topics:\n\n'
            for warning in warnings:
                msg = msg + warning + '\n'
            with open(status_file, 'w') as f:
                f.write(msg)
        else:
            msg = 'Congratulations! All the titles and short descriptions are in place.'
        logger.info(msg)
        return msg


@debugmethods
class SearchRepository:

    @staticmethod
    def get_location(part_type) -> Folder:
        id = ''
        match part_type:
            case 'dfe':
                id = 7406676
            case '3':
                id = 6726982
            case '4':
                id = 6726981
            case '5':
                id = 6726980
            case '6':
                id = 7406751
            case 'common in presses':
                id = 7308650
        if part_type:
            return Folder(id=id)

    @staticmethod
    def scan_helper(part_number: int | str,
                    folder: Folder,
                    depth: int,
                    max_depth: int = 2) \
            -> tuple[str, str | int]:
        folder_data = folder.get_subfolder_ids()
        depth += 1
        for metadata, id in folder_data:
            name = metadata.dict_form.get('FNAME').get('text')
            logger.info('Searching in ' + name + ' (' + id + ')')
            if part_number in name:
                return name, id
            else:
                if depth > max_depth:
                    continue
                result = SearchRepository.scan_helper(part_number,
                                                      Folder(id=id), depth, max_depth)
                if result:
                    return result

    @staticmethod
    def scan_folder(part_number: str | int,
                    folder: Folder,
                    start_depth: int,
                    max_depth: int = 2) -> \
            tuple[str | None, str | int | None]:
        """
        Returns name and GUID of the project folder (folder type = folder with folders).
        """
        logger.info('Searching...')
        result = SearchRepository.scan_helper(part_number, folder, start_depth, max_depth)
        if result:
            logger.info('Found ' + str(result) + '.')
            return result
        else:
            logger.info('Not found. Try a different scope')


@check_token
def check_multiple_projects_for_titles_and_shortdescs(partno_list: list[str]):
    warnings = []
    not_ready = []
    for part_no in partno_list:
        something_is_missing = False
        proj_name, folder_id = SearchRepository.scan_folder(part_number=part_no,
                                                            folder=Folder(id=Constants.INDIGO_TOP_FOLDER.value),
                                                            start_depth=0, max_depth=5)
        proj = Project(proj_name, folder_id)
        topic_folder = proj.subfolders.get('topics')
        if not topic_folder:
            warnings.append('topics folder does not exist in project ' + proj_name + '- skipping')
            continue
        topic_guids: list[str] = topic_folder.get_contents('ishobjects')
        logger.debug(topic_guids)
        for topic_guid in topic_guids:
            topic = Topic(id=topic_guid)
            topic_contents = XMLContent(root=topic.get_decoded_content_as_tree())
            if (topic_contents.title_missing() or topic_contents.shortdesc_missing()) \
                    and topic_contents.outputclass != 'frontcover' and topic_contents.outputclass != 'backcover':
                something_is_missing = True
                topic_name = topic.get_metadata(Metadata(('ftitle', ''))).dict_form.get('FTITLE').get('text')
                if topic_contents.title_missing():
                    report = 'Title missing:\n' + topic_name + '\nin project: ' + proj_name
                    warnings.append(report)
                if topic_contents.shortdesc_missing():
                    report = 'Shortdesc missing:\n' + topic_name + '\nin project: ' + proj_name
                    warnings.append(report)
        if something_is_missing:
            not_ready.append((proj_name, folder_id))
    if len(not_ready) > 0:
        logger.info('Projects not ready for Dynamic Delivery:')
        for p in not_ready:
            logger.info(p)
        logger.info('\n------------------------------------\n')
        logger.info('Problematic topics:\n')
        for warning in warnings:
            logger.info(warning + '\n')
