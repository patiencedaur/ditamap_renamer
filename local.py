import os
from lxml import etree
from mary_xml import XMLContent
import re

outputclasses: dict[str, str] = {
    # Document outputclass, indicated as an attribute of the first content tag.
    # Example: <task id=... outputclass="procedure">
    'context': 'c_',
    'lpcontext': 'c_',
    'explanation': 'e_',
    'procedure': 't_',
    'referenceinformation': 'r_',
    'legalinformation': 'e_'}

prefixes: dict[str, str] = {
    # A prefix is an identifying letter that gets prepended to the filename, according to the style guide.
    'explanation': 'e_',
    'referenceinformation': 'r_',
    'context': 'c_',
    'procedure': 't_',
    'legalinformation': 'e_'
}

# Document type, indicated in the first content tag. Example: <task id=... outputclass="procedure">
doctypes: list[str] = ['concept', 'task', 'reference']


def file_rename(old_path: str, new_path: str) -> None:
    if os.path.exists(old_path):
        if old_path == new_path:
            print('Error, old path equal to new path:', old_path)
        else:
            os.rename(old_path, new_path)
    else:
        print('Error, no file to rename_in_pair:', old_path)


def file_delete(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)
    else:
        print('Error, no file to delete:', path)


class LocalProjectFile:

    def __init__(self, file_path: str) -> None:
        """
        Based on file path, retrieve the containing folder and parse the file in advance.
        """
        self.path = file_path
        self.folder, self.name = os.path.split(self.path)
        self.basename, self.ext = os.path.splitext(self.name)

        self.ditamap: LocalMap | None = None  # is assigned during map initialization

        root = etree.parse(self.path).getroot()
        header = self.get_xml_file_header()
        if header:
            self.content = XMLContent(root, header)
        else:
            self.content = XMLContent(root)

    def __repr__(self) -> str:
        return '<LocalProjectFile: ' + self.name + self.ext + '>'

    def __eq__(self, other) -> bool:
        return self.path == other.path

    def __ge__(self, other) -> bool:
        return self.path >= other.path

    def __gt__(self, other) -> bool:
        return self.path > other.path

    def __le__(self, other) -> bool:
        return self.path <= other.path

    def __lt__(self, other) -> bool:
        return self.path < other.path

    def __ne__(self, other) -> bool:
        return self.path != other.path

    def __hash__(self) -> int:
        return hash(self.path)

    def __sortkey__(self) -> str:
        return self.path

    def get_xml_file_header(self) -> str | None:
        if not self.path:
            print('Path', self.path, 'does not exist')
            return
        with open(self.path, 'r', encoding='utf-8') as f:
            declaration = r'(<\?xml version="1.0" encoding="UTF-8"\?>\n)(<!DOCTYPE.*?>\n)?'
            first_four_lines = ''
            for i in range(4):  # get the first 4 lines of the file
                first_four_lines += str(next(f))
            # look for xml declaration or xml declaration followed by doctype declaration
            found_declaration = re.findall(declaration, first_four_lines, re.DOTALL)
            if len(found_declaration) > 0:
                header = ''.join(found_declaration[0])
                return header
            else:
                print('XML declaration not found')
                return

    def write(self) -> None:
        """
        Call this after all manipulations with the tree.
        """
        self.content.tree.write(self.path)


class LocalMap(LocalProjectFile):

    def __init(self, file_path):
        super().__init__(self, file_path)
        self.ditamap = self
        self.image_folder = self.folder
        self.images = self.get_images()
        self.topics = self.get_topics()

    def __str__(self) -> str:
        return '<LocalMap: ' + self.name + '>'

    def __repr__(self):
        return '<LocalMap: ' + self.name + '>'

    def __contains__(self, item: LocalProjectFile) -> bool:
        return True if item in self.topics else False

    oc_object_types: dict[str, str] = {
        'referenceinformation': 'LocalReferenceInformationTopic(topic_path, self)',
        'procedure': 'LocalTaskTopic(topic_path, self)',
        'legalinformation': 'LocalLegalInformationTopic(topic_path, self)',
        'context': 'LocalConceptTopic(topic_path, self)',
        'lpcontext': 'LocalConceptTopic(topic_path, self)',
        'explanation': 'LocalTopic(topic_path, self)'
    }

    def get_images(self) -> set['Image']:
        """
        Run this before get_structure, because topic in pairs
        have their own images derived from the map set of images.
        """
        image_list = []
        for file in os.listdir(self.image_folder):
            if file.endswith(('png', 'jpg', 'gif')):
                image_list.append(Image(file, self))
        return set(image_list)

    def get_topic_from_topicref(self, topicref: etree.Element):
        topic_path: str = os.path.join(self.folder, topicref.attrib.get('href'))
        if not os.path.exists(topic_path):
            print('Cannot create LocalProjectFile from path %s. Aborting.' % topic_path)
        oc: str = etree.parse(topic_path).getroot().attrib.get('outputclass')
        if oc in self.oc_object_types.keys():
            topic = eval(LocalMap.oc_object_types[oc])
            if oc == 'context':
                children = topicref.findall('topicref')
                if len(children) > 0:
                    topic.children = [self.get_topic_from_topicref(child) for child in children]
        else:
            topic = LocalTopic(topic_path, self)
        return topic

    def get_topics(self):
        topics = []
        for topicref in self.content.root.iter('topicref'):
            print('Initializing', topicref.attrib.get('href'), '...')
            topic = self.get_topic_from_topicref(topicref)
            topics.append(topic)
        return topics

    def refresh(self):
        self.get_topics()
        self.get_images()

    def update_topicref(self, old, new):
        for topicref in self.content.root.iter('topicref'):
            if topicref.attrib.get('href') == old:
                if old == new:
                    print('Skipped in map: %s, nothing to rename_in_pair' % old)
                    continue
                topicref.set('href', new)
        self.write()


class LocalTopic(LocalProjectFile):
    """
    Get DITA outputclass, title, and shortdesc.
    """

    def __init__(self, file_path: str, ditamap) -> None:
        super().__init__(file_path)
        self.ditamap = ditamap
        if self.content.shortdesc_tag is None:
            self.content.insert_shortdesc_tag()
        self.images = self.get_images()
        self.children = []

    def __repr__(self):
        return '<LocalTopic: ' + self.name + '>'

    def __contains__(self, item):
        contains = False
        if isinstance(item, Image) and item in self.images:
            contains = True
        if isinstance(item, str) and item in self.content.local_links:
            contains = True
        if isinstance(self, LocalConceptTopic) and isinstance(item, LocalTopic) and item in self.children:
            contains = True
        return contains

    def get_images(self):
        topic_images = []
        for ditamap_image in self.ditamap.images:
            ditamap_href = ditamap_image.href
            for fig in self.content.root.iter('fig'):
                topic_image_title = fig.find('title')
                if topic_image_title is None:
                    topic_image_title = etree.SubElement(fig, 'title')
                    topic_image_title.text = '\u00A0'
                if fig.find('image').attrib.get('href') == ditamap_href:
                    if topic_image_title.text:
                        ditamap_image.title = topic_image_title.text.strip()
                    topic_images.append(ditamap_image)
        return set(topic_images)

    def set_title(self, new_title):
        # New title is a string
        self.content.set_title(new_title)
        self.write()

    def set_shortdesc(self, new_shortdesc):
        # New shortdesc is a string
        self.content.set_shortdesc(new_shortdesc)
        self.write()

    def get_draft_comments(self):
        draft_comments = []
        for dc in self.content.root.iter('draft-comment'):
            draft_comments.append((dc, self.content.parent_map[dc]))
        return draft_comments

    def insert_shortdesc_tag(self):
        self.content.insert_shortdesc_tag()
        self.write()

    def rename_in_pair(self, old_path, new_name):
        self.name = new_name + self.ext
        self.path = os.path.join(self.folder, self.name)
        if os.path.exists(self.path):
            print('New path already exists:', self.path)
        else:
            file_rename(old_path, self.path)


class LocalReferenceInformationTopic(LocalTopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        assert self.content.outputclass == 'referenceinformation'

    def __repr__(self):
        return '<LocalTopic - RefInfo: ' + self.name + '>'


class LocalLegalInformationTopic(LocalTopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        assert self.content.outputclass == 'legalinformation'

    def __repr__(self):
        return '<LocalTopic - LegalInfo: ' + self.name + '>'

    def add_title_and_shortdesc(self):
        self.content.add_legal_title_and_shortdesc()
        self.write()


class LocalConceptTopic(LocalTopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        assert self.content.outputclass == 'context' or self.content.outputclass == 'lpcontext'
        self.children = []

    def __repr__(self):
        return '<LocalTopic - Concept: ' + self.name + '>'


class LocalTaskTopic(LocalTopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        assert self.content.outputclass == 'procedure'

    def __str__(self):
        return '<LocalTopic - Task: ' + self.name + '>'


class Image:

    def __init__(self, href, ditamap):
        self.href: str = href
        self.ditamap: LocalMap | None = ditamap
        self.title = None
        self.temp_title = None
        self.ext = '.' + self.href.rsplit('.', 1)[1]

    def __repr__(self):
        r = '<Image ' + self.href
        if self.title:
            r = r + ': ' + str(self.title)
        r += '>'
        return r

    def generate_name(self, prefix):
        if self.temp_title is not None:
            # name the image based on its title
            name = '_'.join(self.temp_title.split(' '))
        else:
            name = self.href.rsplit('.', 1)[0]
        name = 'img_' + prefix + '_' + re.sub(r'\W+', '', name) + self.ext
        return name

# TODO: insert &nbsp between auxiliary tables
# TODO: "commit" and "roll back" operations like renaming. maybe even reversing?
