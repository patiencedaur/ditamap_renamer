from enum import Enum
from base64 import b64decode
import os


class Constants(Enum):
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           b64decode('c2VjcmV0LnB5').decode('utf-8'))) as f:
        HOSTNAME, USERNAME, PASSWORD = b64decode(f.readline()).decode('utf-8').split('\n')
    INDIGO_TOP_FOLDER = 6721145
    SCITEX_TOP_FOLDER = 7793322
    UNKNOWN = None

    PADDING = {'padx': 10, 'pady': 10}

    outputclasses: dict[str, str] = {
        # 1. Document outputclass, indicated as an attribute of the first content tag.
        # Example: <task id=... outputclass="procedure">
        # 2. Prefix that should be prepended to the file name.
        # 3. Doctype - determines the header and is indicated in the map next to the topicref.
        # Example: <task id=... outputclass="procedure">
        # 4. File header
        'context': (
            'c_', 'concept', '<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">'
        ),
        'lpcontext': (
            'c_', 'concept', '<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">'
        ),
        'explanation': (
            'e_', 'concept', '<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">'
        ),
        'procedure': (
            't_', 'task', '<!DOCTYPE task PUBLIC "-//OASIS//DTD DITA General Task//EN" "generalTask.dtd">'
        ),
        'referenceinformation': (
            'r_', 'reference', '<!DOCTYPE reference PUBLIC "-//OASIS//DTD DITA Reference//EN" "reference.dtd">'
        ),
        'legalinformation': (
            'r_', 'reference', '<!DOCTYPE reference PUBLIC "-//OASIS//DTD DITA Reference//EN" "reference.dtd">'
        ),
        'frontcover': (
            'r_', 'reference', '<!DOCTYPE reference PUBLIC "-//OASIS//DTD DITA Reference//EN" "reference.dtd">'
        ),
        'backcover': (
            'r_', 'reference', '<!DOCTYPE reference PUBLIC "-//OASIS//DTD DITA Reference//EN" "reference.dtd">'
        )
    }

    def __add__(self, other):
        return str(self) + str(other)

    def __str__(self):
        return str(self.value)

    ISHFIELDS = {
        'FNAME': {
            'ishtype': 'ISHFolder',
            'level': 'None',
            'datatype': 'String',
            'datasource': '',
            'is_element': False,
        },
        'FISHFOLDERPATH': {
            'ishtype': 'ISHFolder',
            'level': 'None',
            'datatype': 'ISHType',
            'datasource': '',
            'is_element': False,
        },
        'FDOCUMENTTYPE': {
            'ishtype': 'ISHFolder',
            'level': 'None',
            'datatype': 'ISHLov',
            'datasource': 'ISHFolder',
            'is_element': False,
        },
        'FHPICUSTOMERSUPPORTSTORIES': {
            'ishtype': 'ISHModule',
            'level': 'Logical',
            'datatype': 'ISHMetadataBinding',
            'datasource': 'HPITaxonomyMiddleWare4CustSupStor',
            'is_element': True,
        },
        'FHPIPRODUCT': {
            'ishtype': ['ISHModule', 'ISHMasterDoc'],
            'level': 'Logical',
            'datatype': 'ISHMetadataBinding',
            'datasource': 'HPITaxonomyMiddleWare4Product',
            'is_element': True,
        },
        'FHPIREGION': {
            'ishtype': 'ISHModule',
            'level': 'Logical',
            'datatype': 'ISHMetadataBinding',
            'datasource': 'TaxonomyMiddlewareHPIConnector4Region',
            'is_element': True,
        },
        'FHPITECHNICALLEVEL': {
            'ishtype': 'ISHModule',
            'level': 'Logical',
            'datatype': 'ISHLov',
            'datasource': 'DHPITECHNICALLEVEL',
            'is_element': False,
        },
        'FTITLE': {
            'ishtype': 'ISHModule',
            'level': 'Logical',
            'datatype': 'String',
            'datasource': '',
            'is_element': False,
        },
        'FUSERGROUP': {
            'ishtype': 'ISHModule',
            'level': 'Logical',
            'datatype': 'ISHType',
            'datasource': 'ISHUserGroup',
            'is_element': False,
        },
        'FMODULETYPE': {
            'ishtype': 'ISHModule',
            'level': 'Logical',
            'datatype': 'ISHLov',
            'datasource': 'DMODULETYPE',
            'is_element': False,
        },
        'VERSION': {
            'ishtype': 'ISHModule',
            'level': 'Version',
            'datatype': 'String',
            'datasource': '',
            'is_element': False,
        },
        'FHPIPUBLISHONEVERSION': {
            'ishtype': 'ISHPublication',
            'level': 'Logical',
            'datatype': 'ISHLov',
            'datasource': 'BOOLEAN',
            'is_element': False,
        },
        'FHPIDISCLOSURELEVEL': {
            'ishtype': 'ISHPublication',
            'level': 'Version',
            'datatype': 'ISHMetadataBinding',
            'datasource': 'HPITaxonomyMiddleWare4DisclosureDate',
            'is_element': True,
        },
        'FISHMASTERREF': {
            'ishtype': 'ISHPublication',
            'level': 'Version',
            'datatype': 'ISHType',
            'datasource': 'ISHMasterDoc',
            'is_element': False,
        },
        'FISHPUBSOURCELANGUAGES': {
            'ishtype': 'ISHPublication',
            'level': 'Version',
            'datatype': 'ISHLov',
            'datasource': 'DLANGUAGE',
            'is_element': False,
        },
        'FISHREQUIREDRESOLUTIONS': {
            'ishtype': 'ISHPublication',
            'level': 'Version',
            'datatype': 'ISHLov',
            'datasource': 'DRESOLUTION',
            'is_element': False,
        },
        'FAUTHOR': {
            'ishtype': 'ISHUser',
            'level': 'Lng',
            'datatype': 'ISHType',
            'datasource': 'ISHUser',
            'is_element': False,
        },
        'FISHRESOURCES': {
            'ishtype': 'ISHPublication',
            'level': 'Version',
            'datatype': 'ISHType',
            'datasource': ['ISHModule', 'ISHMasterDoc', 'ISHLibrary'],
            'is_element': False,  # variable guid
        },
        'FSTATUS': {
            'ishtype': ['ISHModule', 'ISHMasterDoc', 'ISHLibrary'],
            'level': 'Lng',
            'datatype': 'ISHLov',
            'datasource': 'DSTATUS',
            'is_element': True,
        },
        'CREATED-ON': {
            'ishtype': 'ISHFolder',
            'level': 'None',
            'datatype': 'DateTime',
            'datasource': '',
            'is_element': False,
        },
        'MODIFIED-ON': {
            'ishtype': 'ISHFolder',
            'level': 'None',
            'datatype': 'DateTime',
            'datasource': '',
            'is_element': False,
        },
        'FISHQUERY': {
            'ishtype': 'ISHFolder',
            'level': 'None',
            'datatype': 'LongText',
            'datasource': '',
            'is_element': False,
        },
        'READ-ACCESS': {
            'ishtype': 'ISHFolder',
            'level': 'None',
            'datatype': 'ISHLov',
            'datasource': 'DUSERGROUP',
            'is_element': True,
        },
        'FMASTERTYPE': {
            'ishtype': 'ISHMasterDoc',
            'level': 'Logical',
            'datatype': 'ISHLov',
            'datasource': 'DMASTERTYPE',
            'is_element': False,
        },
        'FLIBRARYTYPE': {  # value='VLIBRARYTYPEVARIABLESOURCE'
            'ishtype': 'ISHLibrary',
            'level': 'Logical',
            'datatype': 'ISHLov',
            'datasource': 'DLIBRARYTYPE',
            'is_element': True,
        },
        # HPI PDF
        'FHPISEARCHABLE': {  # value='yes'
            'ishtype': ['ISHModule', 'ISHMasterDoc'],
            'level': 'Logical',
            'datatype': 'ISHLov',
            'datasource': 'BOOLEAN',
            'is_element': False,
        },
        'FISHOUTPUTFORMATREF': {  # value='HPI PDF' / 'VOUTPUTFORMATHPPDF'
            'ishtype': 'ISHPublication',
            'level': 'Lng',
            'datatype': 'ISHType',
            'datasource': 'ISHOutputFormat',
            'is_element': False,
        },
        'FHPIPUBLISHTOPORTALS': {  # PortalPDF: value='yes'
            'ishtype': 'ISHPublication',
            'level': 'Lng',
            'datatype': 'ISHLov',
            'datasource': 'DHPIPUBLISHTOPORTALS',
            'is_element': False,
        },
        'FHPIPRESENTATIONTARGET': {  # value='screen'
            'ishtype': 'ISHPublication',
            'level': 'Lng',
            'datatype': 'ISHLov',
            'datasource': 'DHPIPRESENTATIONTARGET',
            'is_element': False,
        },
        'FHPIPAGECOUNTOPTIMIZED': {  # value='yes'
            'ishtype': 'ISHPublication',
            'level': 'Lng',
            'datatype': 'ISHLov',
            'datasource': 'DHPIPAGECOUNTOPTIMIZED',
            'is_element': False,
        },
        'FHPICHAPTERPAGESTART': {  # value='next.page'
            'ishtype': 'ISHPublication',
            'level': 'Lng',
            'datatype': 'ISHLov',
            'datasource': 'DHPICHAPTERPAGESTART',
            'is_element': False,
        },
        'FHPINUMBERCHAPTERS': {  # value='yes'
            'ishtype': 'ISHPublication',
            'level': 'Lng',
            'datatype': 'ISHLov',
            'datasource': 'DHPINUMBERCHAPTERS',
            'is_element': False,
        },
        'FHPISECONDARYCOLOR': {  # value = 'blue.hp.2172c'
            'ishtype': 'ISHPublication',
            'level': 'Lng',
            'datatype': 'ISHLov',
            'datasource': 'DHPISECONDARYCOLOR',
            'is_element': False,
        },
        'FHPISUPPRESSTITLEPAGE': {  # value = 'yes'
            'ishtype': 'ISHPublication',
            'level': 'Lng',
            'datatype': 'ISHLov',
            'datasource': 'DHPISUPPRESSTITLEPAGE',
            'is_element': False,
        },
        'FHPITOPICTITLE': {
            'ishtype': 'ISHModule',
            'level': 'Lng',
            'datatype': 'String',
            'datasource': '',
            'is_element': False,
        },
        'FHPITEMPLATETYPE': {
            'ishtype': 'ISHTemplate',
            'level': 'Logical',
            'datatype': 'ISHLov',
            'datasource': 'DHPITEMPLATETYPE',
            'is_element': False
        },
        'FHPIHARDWARECOMPONENTS': {
            'ishtype': 'ISHModule',
            'level': 'Logical',
            'datatype': 'ISHMetadataBinding',
            'datasource': 'HPITaxonomyMiddleWare4HardwareComponents',
            'is_element': True
        }
    }
