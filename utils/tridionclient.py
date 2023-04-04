import base64
import datetime
import random
import re
import sys

from lxml import etree
from requests import Session
from zeep import Client, Transport, exceptions

from utils.ishfields import IshField
from utils.constants import Constants

"""
A Python client for SDL Tridion Docs. Created for HP Indigo by Dia Daur.
"""


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
                print(self.__init__.__doc__)
                sys.exit()

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


class Tag:
    hostname = Constants.HOSTNAME + 'MetadataBinding25.asmx?wsdl'
    service = Client(hostname, service_name='MetadataBinding25', port_name='MetadataBinding25Soap').service

    def __init__(self, name: str) -> None:
        self.name = name
        self.level = IshField.f.get(name.upper()).get('level').lower()

    def save_possible_values_to_file(self) -> None:
        xml = Tag.service.RetrieveTagStructure(Auth.token,
                                               psFieldName=self.name.upper(),
                                               psFieldLevel=self.level)['psXMLFieldTags']
        # with open('tag.xml', 'w', encoding='utf-8') as f:
        #     f.write(xml)
        root = Unpack.to_tree(xml)
        filename = self.name + '-' + datetime.date.today().isoformat() + '.csv'
        with open(filename, 'w', encoding='utf-8') as dest:
            for tag in root.iter('tag'):
                selectable = tag.find('selectable').text
                if selectable == 'false':
                    continue
                key = tag.find('label').text
                value = tag.attrib.get('id')
                dest.write(str(key).rstrip() + ',' + '\t"' + str(value).rstrip() + '"\n')


class LOV:
    hostname = Constants.HOSTNAME + 'ListOfValues25.asmx?wsdl'
    service = Client(hostname, service_name='ListOfValues25', port_name='ListOfValues25Soap').service

    @staticmethod
    def get_value_tree(dname):
        xml = LOV.service.RetrieveValues(psAuthContext=Auth.token,
                                         pasFilterLovIds=dname.upper(),
                                         peActivityFilter='None',
                                         )['psOutXMLLovValueList']
        return Unpack.to_tree(xml)


class Auth:
    auth = Client(Constants.HOSTNAME + 'Application25.asmx?wsdl',
                  service_name='Application25',
                  port_name='Application25Soap',
                  transport=Transport(session=Session())).service
    # client = Client(hostname + 'Application25.asmx?wsdl', wsse=UsernameToken(username, password))
    response = auth.Login('InfoShareAuthor', Constants.USERNAME, Constants.PASSWORD)
    token = response['psOutAuthContext']
    print('Login token:', token)

    @staticmethod
    def get_dusername():
        tree = LOV.get_value_tree('username')
        for ishlovvalue in tree.iter('ishlovvalue'):
            label = ishlovvalue.find('label')
            if label.text == Constants.USERNAME.value:
                return ishlovvalue.attrib.get('ishref')


class DocumentObject:
    hostname = Constants.HOSTNAME + 'DocumentObj25.asmx?wsdl'
    service = Client(hostname, service_name='DocumentObj25', port_name='DocumentObj25Soap').service

    def __init__(self, name: str = None, folder_id: int | str = None, id: str = None) -> None:
        if name and folder_id and not id:
            self.name = name
            self.folder_id = folder_id
        elif id and not name and not folder_id:
            self.id = id

    def __repr__(self) -> str:
        return '<' + self.id + '>'

    def set_metadata(self, metadata: Metadata) -> None:
        DocumentObject.service.SetMetadata(Auth.token, self.id, psVersion=1, psLanguage='en-US',
                                           psXMLMetadata=metadata.pack)
        print('Set metadata:', metadata, 'for object:', self)

    def get_metadata(self, metadata: Metadata) -> Metadata:
        request: str = metadata.pack
        xml = DocumentObject.service.GetMetaData(Auth.token, self.id, psVersion=1, psXMLRequestedMetaData=request)[
            'psOutXMLObjList']
        return Unpack.to_metadata(xml)

    def get_folder(self) -> int | str:
        meta: dict = DocumentObject.service.FolderLocation(Auth.token, self.id, peOutBaseFolder='Data')
        folder_id = meta['palOutFolderRefs']['long'][-1]
        return folder_id

    def set_metadata_for_dynamic_delivery(self, product: int | str = None, css: int | str = None):
        print('Setting metadata:', locals(), 'for', self)
        if product:
            set_product: Metadata = Metadata(('fhpiproduct', product))
            self.set_metadata(set_product)

        if css:
            set_css: Metadata = Metadata(('fhpicustomersupportstories', css))
            self.set_metadata(set_css)

        worldwide = '205101142445494286415257'
        set_region: Metadata = Metadata(('fhpiregion', worldwide))
        self.set_metadata(set_region)

        print('Filled mandatory metadata for', self)

    def get_current_dynamic_delivery_metadata(self) -> tuple[str | int, str | int, str | int]:
        mandatory_metadata: Metadata = Metadata(('fhpiproduct', ''), ('fhpicustomersupportstories', ''),
                                                ('fhpiregion', ''))
        get_meta: Metadata = self.get_metadata(mandatory_metadata)
        fhpiproduct: dict[str, str] = get_meta.dict_form.get('FHPIPRODUCT')
        fhpicss: dict[str, str] = get_meta.dict_form.get('FHPICUSTOMERSUPPORTSTORIES')
        fhpiregion: dict[str, str] = get_meta.dict_form.get('FHPIREGION')
        return fhpiproduct.get('text'), fhpicss.get('text'), fhpiregion.get('text')

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
        content = DocumentObject.service.GetObject(Auth.token, self.id, psVersion=1,
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
            DocumentObject.service.Delete(Auth.token, psLogicalId=self.id)
        except exceptions.Fault:
            print('Failed to delete object. Possible reasons:')
            print('- Object is referenced by another object')
            print('- Object is a root map')
            print('- One of the languages is used in a released publication output')
            print('- One of the languages is released, and you are no Administrator')
            print('- One of the languages is checked out, and you are no Administrator')


class PDFObject(DocumentObject):

    def __init__(self, name: str = None, folder_id: int | str = None, id: str = None):
        super().__init__(name, folder_id, id)
        self.type = 'ISHTemplate'
        if name and folder_id and not id:
            self.id = self.create()

    def create(self):
        folder_type = 'ISHTemplate'
        with open('../templates/pdf_template.pdf', 'rb') as template:
            pbdata = template.read()
        author = Auth.get_dusername()
        request: str = Metadata(
            IshField('ftitle', self.name),
            IshField('fstatus', 'VSTATUSDRAFT'),
            IshField('fauthor', author),
        ).pack

        response = DocumentObject.service.Create(Auth.token, self.folder_id, folder_type, psVersion='new',
                                                 psLanguage='en-US',
                                                 psXMLMetadata=request, psEdt='EDTPDF', pbData=pbdata)
        id = response['psLogicalId']
        return id
    
    def fill_initial_metadata(self):
        initial_metadata = Metadata(
            IshField('FHPITOPICTITLE', self.name),
            IshField('FHPIDISCLOSURELEVEL', '287477763180518087286275037723076'),
            IshField('FHPIPRODUCT', '18576095'),
            IshField('FHPIREGION', '205101142445494286415257'),
        )
        self.set_metadata(initial_metadata)
        

class Map(DocumentObject):

    def __init__(self, name: str = None, folder_id: str = None, id: str = None):
        """
        Usage:
        my_new_map = Map(name='My Awesome Map', folder_id='GUID-parent-folder-id')
        my_existing_map = Map(id='GUID-9876')
        """
        super().__init__(name, folder_id, id)
        self.type = 'ISHMasterDoc'
        if name and folder_id and not id:
            self.id = self.create()

    def create(self) -> str:
        folder_type = 'ISHMasterDoc'
        boilerplate = '<?xml version="1.0" encoding="utf-8"?>\n' + \
                      '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd"[]><map />'
        pbdata: bytes = bytes(boilerplate, 'utf-8')
        author = Auth.get_dusername()
        request: str = Metadata(
            IshField('ftitle', self.name),
            IshField('fstatus', 'VSTATUSDRAFT'),
            IshField('fauthor', author),
            # IshField('fmastertype', 'Troubleshooting')
        ).pack
        response = DocumentObject.service.Create(Auth.token, self.folder_id, folder_type, psVersion='new',
                                                 psLanguage='en-US',
                                                 psXMLMetadata=request, psEdt='EDTXML', pbData=pbdata)
        id = response['psLogicalId']
        return id


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

        response = DocumentObject.service.Create(Auth.token, plFolderRef=self.folder_id,
                                                 psIshType=self.type, psLanguage='en-US',
                                                 psVersion='new', psXMLMetadata=request,
                                                 psEdt='EDTXML', pbData=pbdata)['psLogicalId']
        return response


class Topic(DocumentObject):

    def __init__(self, name: str = None, folder_id: int | str = None, id: str = None) -> None:
        super().__init__(name, folder_id, id)


class Publication:
    hostname = Constants.HOSTNAME + 'PublicationOutput25.asmx?wsdl'
    service = Client(hostname, service_name='PublicationOutput25', port_name='PublicationOutput25Soap').service

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
        pub_response = Publication.service.Create(Auth.token, self.folder_id, psVersion='new',
                                                  psXMLMetadata=meta)
        return pub_response['psLogicalId']

    def get_hpi_pdf_metadata(self, metadata: Metadata) -> Metadata:
        xml = Publication.service.GetMetaData(Auth.token, self.id, psVersion=1,
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
        xml = Publication.service.GetMetaData(Auth.token, self.id, psVersion=1, psXMLRequestedMetaData=meta)[
            'psOutXMLObjList']
        return Unpack.to_metadata(xml)

    def set_metadata(self, metadata: Metadata) -> None:
        Publication.service.SetMetadata(Auth.token, self.id, psVersion=1, psXMLMetadata=metadata.pack)

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
            print('Error: Use a disclosure level specified in the values of the' +
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
        Publication.service.SetMetadata(Auth.token, self.id, psVersion=1, psXMLMetadata=meta)

    def has_map(self):
        pass

    def set_hpi_pdf_metadata(self):
        # Requires a created HPI PDF output
        meta = Metadata(
            ('fhpipresentationtarget', 'screen'),
            ('fhpipagecountoptimized', 'yes'),
            ('fhpichapterpagestart', 'next.page'),
            ('fhpinumberchapters', 'yes'),
            ('fhpisecondarycolor', 'blue.hp.2925c')
        ).pack
        Publication.service.SetMetadata(Auth.token, self.id, psVersion=1, psXMLMetadata=meta,
                                        psOutputFormat='HPI PDF', psLanguageCombination='en-US')

    def publish_portals(self):
        meta = Metadata(('fhpipublishtoportals', 'yes')).pack
        # required_meta = Metadata(('fishoutputformatref', 'HPI PDF')).pack
        Publication.service.SetMetadata(Auth.token, self.id, psVersion=1, psXMLMetadata=meta,
                                        # psXMLRequiredCurrentMetadata=required_meta,
                                        psOutputFormat='HPI PDF', psLanguageCombination='en-US')


class Folder:
    hostname = Constants.HOSTNAME + 'Folder25.asmx?wsdl'
    service = Client(hostname, service_name='Folder25', port_name='Folder25Soap').service

    def __init__(self, name: str = None, type: str = None, parent_id: int | str = None,
                 id: int | str = None, metadata: Metadata = Metadata([])):
        """
        Usage:
        new_folder = Folder(name='My New Folder', type='ISHPublication', parent_id='444444')
        existing_folder = Folder(id='55555')
        folder_from_metadata = Folder(metadata=my_metadata)
        """
        self.id = id
        self.name = name
        self.type = type
        self.parent_id = parent_id
        self.metadata = metadata

        if name and type and parent_id and not id:
            new_folder_response = Folder.service.Create(Auth.token, self.parent_id, self.type, self.name,
                                                        plOutNewFolderRef=str(random.randrange(2 ^ 32)))
            self.id = new_folder_response['plOutNewFolderRef']
            print('Created folder:', self.id, self.name)
        if metadata:
            self.name = self.metadata.dict_form.get('FNAME').get('text')
            self.type = self.metadata.dict_form.get('FDOCUMENTTYPE').get('text')

    def __repr__(self):
        return 'Folder: (' + str(self.id) + ') ' + str(self.name)

    def get_location(self) -> list[str | int]:
        response = Folder.service.FolderLocation(Auth.token, plFolderRef=self.id, peOutBaseFolder='Data')
        folder_location = response['palOutFolderRefs']['long']
        location = [str(item) for item in folder_location]
        return location

    def get_metadata(self, search_mode: str = None):
        """
        :return: Metadata object
        """
        print('Getting metadata...')
        meta: str = Metadata(('fname', ''), ('fishfolderpath', ''), ('fdocumenttype', '')).pack
        xml = Folder.service.GetMetaDataByIshFolderRef(Auth.token, plFolderRef=self.id,
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
            xml = Folder.service.GetSubFoldersByIshFolderRef(Auth.token, plFolderRef=self.id)['psOutXMLFolderList']
            ishfolders: list[tuple[Metadata, str | int]] = Unpack.to_metadata(xml, 'ishfolders')
            return ishfolders
        elif search_mode == 'ishobjects':
            xml = Folder.service.GetContents(Auth.token, plFolderRef=self.id)['psOutXMLObjList']
            ishobjects: list[str] = Unpack.to_metadata(xml, 'ishobjects')
            return ishobjects
        elif not search_mode:
            if self.get_type == 'None' or self.get_type == 'ISHNone':  # folder with folders
                xml = Folder.service.GetSubFoldersByIshFolderRef(Auth.token, plFolderRef=self.id)['psOutXMLFolderList']
            else:
                xml = Folder.service.GetContents(Auth.token, plFolderRef=self.id)['psOutXMLObjList']
            metadata: Metadata = Unpack.to_metadata(xml)
            return metadata

    def get_subfolder_ids(self) -> list[tuple[Metadata, str | int]]:
        xml = Folder.service.GetSubFoldersByIshFolderRef(Auth.token, plFolderRef=self.id)['psOutXMLFolderList']
        return Unpack.subfolder_ids(xml)

    def locate_object_by_name_start(self, name_start: str) -> tuple[str, str]:
        """
        Returns an object from an object folder (not a folder with folders).
        :param name_start: string
        :return: object name, object guid
        """
        guids: list[str] = self.get_contents('ishobjects')

        def get_obj_name_from_guid(guid: str) -> str:
            req_metadata: str = Metadata(('ftitle', '')).pack
            xml = DocumentObject.service.GetMetaData(Auth.token, guid,
                                                     psXMLRequestedMetaData=req_metadata)['psOutXMLObjList']
            xml = Unpack.wrap(xml)
            obj_metadata: Metadata = Unpack.to_metadata(xml)
            obj_name = [field.dict_form.get('FTITLE').get('text') for field in obj_metadata if field is not None][0]
            return obj_name

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
            print('Problem with the publication. Reason:')
            print(e)
            exit()

    def mass_create_subfolders(self, subfolder_name_list: list[str], subfolder_type) -> None:
        for subfolder_name in subfolder_name_list:
            try:
                Folder(name=subfolder_name, parent_id=self.id, type=subfolder_type)
            except exceptions.Fault as e:
                print('Subfolder ', subfolder_name, 'not created. Reason:', e)

    def tag_all(self, **kwargs):
        guids: list[str] = self.get_contents('ishobjects')
        for guid in guids:
            obj = DocumentObject(id=guid)
            obj.set_metadata_for_dynamic_delivery(**kwargs)


class Project:
    folder_names = {'images': ('ISHIllustration', 'Image'),
                    'maps': ('ISHMasterDoc', 'Map'),
                    'publications': ('ISHPublication', 'Publications'),
                    'topics': ('ISHModule', 'Topic'),
                    'variables': ('ISHLibrary', 'Library topic')}

    def __init__(self, name: str = None, id: str | int = None):
        print('Creating project:', locals())
        if id:
            self.id = id
            self.folder = Folder(id=self.id)
            self.name = self.get_name()
        elif not name and not id:
            part_no = input('Enter part number as in the project title: ')
            self.name, self.id = SearchRepository().by_part_number(part_no)
            self.folder = Folder(id=self.id)
        self.subfolders = self.get_subfolders()  # that actually exist on the server

    def get_name(self) -> str:
        return self.folder.get_name

    def get_subfolders(self) -> dict[str, Folder]:
        subfolder_data: list[str] = self.folder.get_contents('ishfolders')
        subfolders: dict[str, Folder] = {}
        for metadata, folder_id in subfolder_data:
            name: str = metadata.dict_form.get('FNAME').get('text')
            if any(k in name for k in Project.folder_names.keys()):  # if folder with similar name exists
                folder_obj: Folder = Folder(id=folder_id, metadata=metadata)
                subfolders[name] = folder_obj
        return subfolders

    def create_subfolder(self, folder_name: str) -> dict[str, Folder] | None:
        folder_type: str = Project.folder_names.get(folder_name)[0]
        if folder_name not in self.subfolders.keys():  # if folder does not exist
            try:
                new_folder = Folder(name=folder_name, type=folder_type, parent_id=self.folder.id)
                self.subfolders[folder_name] = new_folder
                print(self.subfolders)
                return self.subfolders
            except exceptions.Fault as e:
                print(
                    'Problem with creating folder \'{}\'. Check in the Content Manager if it already exists'.format(
                        folder_name))
                print(e)
                sys.exit()

    def create_publication(self) -> Publication:
        pub_folder: Folder = self.subfolders.get('publications')
        pub_guids: list[str] = pub_folder.get_contents('ishobjects')
        if len(pub_guids) == 0:
            disclos_level: str | int = Publication.disclosure_levels.get('HP and Customer Viewable')
            try:
                pub: Publication = pub_folder.add_publication(self.name, disclos_level)
            except exceptions.Fault:
                print('Problem with creating publication. Check in the XMLContent Manager if it already exists')
                exit()
        elif len(pub_guids) == 1:
            pub = Publication(id=pub_guids[0])
        else:
            print('Too many publications in folder. Please delete the unneeded publications in the XMLContent Manager')
            sys.exit()
        return pub

    def get_publication(self) -> Publication | None:
        pub_folder: Folder = self.subfolders.get('publications')
        pub_guids: list[str] = pub_folder.get_contents('ishobjects')
        if len(pub_guids) == 1:
            pub = Publication(id=pub_guids[0])
            return pub
        else:
            print('There should be only one publication. ' +
                  'Please check the XMLContent Manager for missing/redundant files.')

    def get_root_map(self) -> Map:
        map_folder: Folder = self.subfolders.get('maps')
        map_name_and_guid: tuple[str, str] = map_folder.locate_object_by_name_start('rm_')
        if map_name_and_guid:
            map_obj = Map(id=map_name_and_guid[1])
        else:
            map_name = 'rm_' + self.name
            map_obj = Map(name=map_name, folder_id=map_folder.id)
        return map_obj

    def migrate_libvar_from_topic(self) -> LibVariable | None:
        topic_folder: Folder = self.subfolders.get('topics')
        var_folder: Folder = self.subfolders.get('variables')
        var_guids: list[str] = var_folder.get_contents('ishobjects')
        libvar_sources: tuple[str, str] = topic_folder.locate_object_by_name_start('v_')
        try:
            source_name, source_guid = libvar_sources
            assert len(var_guids) == 0
        except TypeError:
            print('Either library variable already exists or source topic was not found. Check the ontent Manager')
            source_name, source_guid = None, None

        try:
            var_obj = LibVariable(name=source_name, folder_id=var_folder.id, topic_guid=source_guid)
            return var_obj
        except TypeError:
            print('Library variable data not found in topic folder')


    def complete_cheetah_migration(self) -> None:
        for folder_name in Project.folder_names.keys():
            self.create_subfolder(folder_name)
        pub: Publication = self.create_publication()
        root_map: Map = self.get_root_map()
        print('Root map:', root_map, 'adding to publication...')
        pub.add_map(root_map)
        print('Searching for library variable...')
        libvar: LibVariable = self.migrate_libvar_from_topic()
        try:
            if libvar.id:
                print('Found', libvar, 'adding to publication...')
                pub.add_resource(libvar)
        except AttributeError:
            print('Library variable not found, continuing...')
        print('Migration completed.')

    def create_folder_structure(self) -> dict[str, Folder]:
        for folder_name in Project.folder_names.keys():
            self.create_subfolder(folder_name)
        return self.subfolders


class SearchRepository:
    htg = (7406745, 7308656)
    pim = (7406774)
    service_docs = (7406746, 7406775)
    site_prep = (7406750, 7406776)
    ug = (7406751, 7406779)

    dfe_inst = (7406744)
    dfe_htg = (7406745)
    dfe_service_docs = (7406746)
    dfe_site_prep = (7406750)
    dfe_ug = (7406751)

    def get_location(self) -> Folder:
        part_type = self.get_press_or_dfe()
        match part_type:
            case 'press':
                return self.get_press_series()
            case 'dfe':
                return Folder(id=7406676)

    def get_press_or_dfe(self):
        return input('\'press\' or \'dfe\'? ')

    def get_press_series(self) -> Folder:
        series = self.get_series_number()
        id = ''
        match series:
            case '3':
                id = 6726982
            case '4':
                id = 6726981
            case '5':
                id = 6726980
            case '6':
                id = 7406751
            case 'common':
                id = 7308650
        if series:
            return Folder(id=id)

    def get_series_number(self):
        return input('Enter series number or \'common\': ')

    def scan_helper(self,
                    part_number: int | str,
                    folder: Folder,
                    depth: int,
                    max_depth: int = 2)\
            -> tuple[str, str | int]:
        folder_data = folder.get_subfolder_ids()
        depth += 1
        for metadata, id in folder_data:
            name = metadata.dict_form.get('FNAME').get('text')
            print('Searching in', name, '(' + id + ')')
            if part_number in name:
                return name, id
            else:
                if depth > max_depth:
                    continue
                result = self.scan_helper(part_number, Folder(id=id), depth, max_depth)
                if result:
                    return result

    def scan_folder(self,
                    part_number: str | int,
                    folder: Folder,
                    depth: int,
                    max_depth: int = 2) -> \
            tuple[str | None, str | int | None]:
        print('Searching...')
        result = self.scan_helper(part_number, folder, depth, max_depth)
        if result:
            print('Found', str(result) + '.')
            return result
        else:
            print('Not found. Try a different scope')
            exit()


    def by_part_number(self, part_number: int | str) -> tuple[str | int | None, Folder | None]:
        return self.scan_folder(part_number, self.get_location(), 0)


def check_projects_for_titles_and_shortdescs(partno_list: list[str]):
    from utils.mary_xml import XMLContent
    warnings = []
    not_ready = []
    for part_no in partno_list:
        something_is_missing = False
        proj_name, folder_id = SearchRepository().scan_folder(part_number=part_no,
                                                       folder=Folder(id=Constants.INDIGO_TOP_FOLDER.value),
                                                       depth=0, max_depth=5)
        proj = Project(proj_name, folder_id)
        topic_folder = proj.subfolders.get('topics')
        if not topic_folder:
            warnings.append('topics folder does not exist in project ' + proj_name + '- skipping')
            continue
        topic_guids: list[str] = topic_folder.get_contents('ishobjects')
        print(topic_guids)
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
        print('Projects not ready for Dynamic Delivery:')
        for p in not_ready:
            print(p)
        print()
        print('------------------------------------')
        print()
        print('Problematic topics:')
        print()
        for warning in warnings:
            print(warning)
            print()


if __name__ == '__main__':
    project = Project()
    if project:
        project.complete_cheetah_migration()

    # check_projects_for_titles_and_shortdescs(['CA394-28940'])

    # LOV.get_value_tree('FHPISUPPRESSTITLEPAGE')

    # product = Tag('fhpicustomersupportstories')
    # product.save_possible_values_to_file()

    # pub_to_query = Publication(id='GUID-34D23F5B-F404-48FE-8EF5-3E41CC70DE2F')
    # print(pub_to_query.get_hpi_pdf_metadata(Metadata(('fhpisecondarycolor', ''))))
    # ditamap = Map(id='GUID-E45F673D-C1FA-4C88-96CA-5A4EABF8169A')
    # decoded_tree = ditamap.get_decoded_content_as_tree()
    #
    # from local_transform import *
