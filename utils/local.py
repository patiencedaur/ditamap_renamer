from copy import deepcopy
import os
from utils.mary_xml import XMLContent, TextElement
from lxml import etree
import re
from utils.constants import Constants
from shutil import copy2
from utils.mary_debug import logger

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
    if not os.path.exists(old_path):
        logger.warning('No file to rename:', old_path)
        return
    if os.path.exists(new_path):
        logger.warning('New path already exists:', new_path)
        return
    if old_path == new_path:
        logger.error('Old path equal to new path:', old_path)
    else:
        os.rename(old_path, new_path)
        logger.info('renamed', old_path, 'to', new_path)


def file_delete(path: str) -> None:
    if not os.path.exists(path):
        logger.error('No file to delete:', path)
        return
    os.remove(path)


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
            logger.error('Path', self.path, 'does not exist')
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
                logger.debug('No XML declaration in header: ' + str(self))
                return

    def write(self, *args, **kwargs) -> None:
        """
        Call this after all manipulations with the tree.
        """
        self.content.tree.write(self.path, xml_declaration=True, encoding='utf-8', doctype=self.content.doctype, *args,
                                **kwargs)
        # self.write_header()

    def write_header(self):
        with open(self.path, 'r+') as f:
            file_contents = f.read()
            f.seek(0, 0)
            f.write(self.content.header + file_contents)


class LocalMap(LocalProjectFile):

    def __init__(self, file_path):
        super().__init__(file_path)
        self.source = self.check_project_folder_content()
        match self.source:
            case 'cheetah':
                self.image_folder = self.folder
            case 'word':
                self.image_folder = os.path.join(self.folder, 'media')
        self.images = self.get_images()
        self.ditamap = self
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

    def check_project_folder_content(self):
        content_types = {}
        for fl in os.listdir(self.folder):
            ext = fl.split('.')[-1]
            if ext not in content_types.keys():
                content_types[ext] = [fl]
            else:
                content_types[ext].append(fl)
        if '3sish' in content_types.keys():
            if len(content_types['dita']) != len(content_types['3sish']):
                logger.critical('Some DITA topics are missing their ISH files, or vice versa.',
                      'Please check the contents of the folder:', self.folder)
            else:
                logger.info('This project is derived from a Cheetah file')
                return 'cheetah'
        else:
            logger.info('This project is derived from a Word file')
            return 'word'

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
            logger.critical('Cannot create LocalProjectFile from path %s. Aborting.' % topic_path)
        topic_content = XMLContent(etree.parse(topic_path).getroot())

        oc: str = topic_content.root.attrib.get('outputclass')
        children = topicref.findall('topicref')
        if oc is None:
            if len(children) > 0:
                oc = 'context'
            else:
                oc = topic_content.detect_type()
        if oc in self.oc_object_types.keys():
            topic = eval(self.oc_object_types[oc])
            if oc == 'context' or oc == 'lpcontext':
                topic.children = [self.get_topic_from_topicref(child) for child in children]
        else:
            topic = LocalTopic(topic_path, self)
        topic.content.set_outputclass(oc)
        topic.update_doctype_in_map()

        try:
            topic.cast()
        except:
            logger.warning('Cannot cast', topic, 'to', topic.__class__)

        if self.source == 'cheetah':
            topic_path: str = os.path.join(self.folder, topicref.attrib.get('href'))
            ish_path = topic_path.replace('.dita', '.3sish')
            topic.ish = LocalISHFile(ish_path, self)
        return topic

    def get_topics(self) -> list['LocalTopic']:
        topics = []
        for topicref in self.content.root.iter('topicref'):
            logger.info('Initializing ' + topicref.attrib.get('href') + '...')
            topic = self.get_topic_from_topicref(topicref)
            topics.append(topic)
        return topics

    def refresh(self) -> tuple[set['Image'], list['LocalTopic']]:
        return self.get_images(), self.get_topics()

    def rename_topics(self) -> int:
        """
        Rename files in map folder according to their titles and the style guide.
        Tracks repeating topic titles.
        """
        renamed_files_counter = 0
        topic_title_repetitions: dict[str, int] = {}
        for topic in self.topics:
            if topic.content.root.tag in doctypes:
                title_text = topic.content.title_tag.text
                if title_text in topic_title_repetitions:
                    topic_title_repetitions[title_text] += 1
                else:
                    topic_title_repetitions[title_text] = 1
                num_rep = topic_title_repetitions[title_text]
                topic.update_name(num_rep)
                renamed_files_counter += 1
        logger.debug('Repeated topic titles:', {k: v for k, v in topic_title_repetitions.items() if v > 0})
        return renamed_files_counter

    def update_topicref(self, old, new):
        for topicref in self.content.root.iter('topicref'):
            if topicref.attrib.get('href') == old:
                if old == new:
                    logger.info('Skipped in map: %s, nothing to rename' % old)
                    continue
                topicref.set('href', new)
        self.write()

    def mass_edit(self) -> list[str]:
        """
        Mass edit short descriptions for typical documents. Returns a list of processed files.
        """
        shortdescs: dict[str, str] = {
            'Revision history and confidentiality notice':
                'This chapter contains a table of revisions, printing instructions, '
                'and a notice of document confidentiality.',
            'Revision history': 'Below is the history of the document revisions and a list of authors.',
            'Printing instructions': 'Follow these recommendations to achieve the best print quality.'
        }

        processed_files: list[str] = []
        for topic in self.topics:
            content = topic.content
            if isinstance(topic, LocalReferenceInformationTopic):
                content.process_docdetails()
            if content.title_tag.text not in shortdescs.keys() or not content.shortdesc_missing():
                continue
            shortdesc: str = shortdescs[content.title_tag.text]
            content.set_shortdesc(shortdesc)
            processed_files.append(topic.name)
            if content.title_tag.text == 'Printing instructions':
                content.add_nbsp_after_table()
            topic.write()
        return processed_files

    def get_problematic_files(self):
        pfiles = [t for t in self.topics if
                  t.content.shortdesc_missing() or t.content.title_missing()
                  or t.content.has_draft_comments]
        return sorted(pfiles)

    def edit_image_names(self, image_prefix: str) -> None:
        # there can be two images with different paths but identical titles
        # one image can be reference in multiple topics
        # count repeating titles and get image to topic map for purposes of renaming
        titles: dict[str, int] = {}
        image_uses_in_topic: dict[Image, list[LocalTopic]] = {}
        for topic in self.topics:
            for image in topic.images:
                if not image.title:
                    pass
                elif image.title in titles:
                    titles[image.title] += 1
                    image.temp_title = image.title + ' ' + str(titles[image.title])
                else:
                    titles[image.title] = 1
                    image.temp_title = image.title
                topics = image_uses_in_topic.setdefault(image, [])
                topics.append(topic)
        # give image files new names
        for img, topics in image_uses_in_topic.items():
            new_name: str = img.generate_name(image_prefix)
            current_path: str = os.path.join(self.image_folder, img.href)
            new_path: str = os.path.join(self.image_folder, new_name)
            if not os.path.exists(current_path) or os.path.exists(new_path):
                logger.error('Current path does not exist or new path exists')
            file_rename(current_path, new_path)
            # rename_path hrefs in topics
            for topic in topics:
                for fig in topic.content.root.iter('fig'):
                    for img_tag in fig.iter('image'):
                        if img_tag.attrib.get('href') == img.href:
                            logger.info('Renaming', img.href, 'to', new_name)
                            img_tag.set('href', new_name)
                topic.write()

    def create_root_concept(self, title='How-to Guide'):
        template_path = '../templates/root_concept.dita'
        concept_filename = self.basename + '.dita'
        concept_path = os.path.join(self.folder, concept_filename)
        copy2(template_path, concept_path)
        rconcept = LocalConceptTopic(concept_path, self)

        self.topics.append(rconcept)

        root_concept_element = deepcopy(self.content.root)
        ttl = root_concept_element.find('title')
        root_concept_element.remove(ttl)
        root_concept_element.tag = 'topicref'
        root_concept_element.set('href', concept_filename)
        self.content.root.clear()
        ttl.text = title
        self.content.root.insert(0, ttl)
        self.content.root.insert(1, root_concept_element)
        self.write()

    def add_topic_groups(self):
        self.content.add_topic_groups()
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
        self.ish = None

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
                topic_image_tag = fig.find('image')
                if topic_image_tag is None:
                    continue
                image_href_in_topic = topic_image_tag.attrib.get('href')
                if fig.findall('alt') is None:
                    topic_image_tag.append(TextElement('alt', '\u00A0'))
                if not image_href_in_topic:
                    continue
                if image_href_in_topic == ditamap_href or image_href_in_topic.split('/')[-1] == ditamap_href:
                    if topic_image_title is not None and topic_image_title.text is not None:
                        ditamap_image.title = topic_image_title.text.strip()
                        fig.find('alt').text = ditamap_image.title
                    topic_images.append(ditamap_image)
        return set(topic_images)

    def add_alt_texts_to_images(self):
        for image in self.images:
            for fig in self.content.root.iter('fig'):
                if fig.find('image').attrib.get('href') == image.href and fig.find('alt') is None:
                    fig.append(etree.Element('alt', image.title))

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

    def create_new_name(self, num_rep):
        """
        Creates a filename that complies with the style guide, based on the document title.
        Takes into account repeating titles of different topics.
        """
        new_name = re.sub(r'[\s\W]', '_',
                          self.content.title_tag.text).replace('___',
                                                               '_').replace('__',
                                                                            '_').replace('_the_', '_')
        new_name = re.sub(r'\W+', '', new_name)
        if new_name.endswith('_'):
            new_name = new_name[:-1]
        if new_name[1] == '_':
            new_name = new_name[2:]

        if self.content.outputclass in Constants.outputclasses.value.keys():
            prefix = Constants.outputclasses.value.get(self.content.outputclass)[0]
            new_name = prefix + new_name

        if num_rep > 1:
            new_name = new_name + '_' + str(num_rep)

        return new_name

    def rename_path(self, old_path, new_name):
        """
        Renames file in system.
        """
        self.name = new_name + self.ext
        self.path = os.path.join(self.folder, self.name)
        if os.path.exists(self.path):
            logger.warning('New path already exists:', self.path)
        else:
            file_rename(old_path, self.path)

    def update_name(self, num_rep):
        """
        Updates file names and links to them in all the documents.
        Takes into account repeating titles of different topics.
        """
        if isinstance(self, LocalLegalInformationTopic):
            self.add_title_and_shortdesc()

        old_topic = LocalTopic(self.path, self.ditamap)
        if self.content.title_missing():
            logger.info('Skipped: %s, nothing to rename (title missing)' % old_topic.name)
            return

        logger.info('Updating name:', old_topic)
        new_name = self.create_new_name(num_rep)
        if old_topic.name == new_name:
            logger.info('Skipped: %s, already renamed' % old_topic.name)
            return

        self.name = new_name
        self.rename_path(old_topic.path, new_name)
        # Update links to this file throughout the folder
        self.content.update_local_links(old_topic.name, new_name)
        self.write()
        self.ditamap.update_topicref(old_topic.name, self.name)
        if self.ish is not None:
            self.ish.rename_with_path(self.ish.path, new_name)

    def assign_type_from_prefix(self):
        prefix = self.name[0:2]
        available_prefixes = {v[0]: k for k, v in Constants.outputclasses.value.items()
                              if k != 'lpcontext'}
        if prefix in available_prefixes.keys():
            self.content.root.set('outputclass', available_prefixes[prefix])
            self.content.outputclass = available_prefixes[prefix]
            self.update_doctype_in_map()

            if prefix == 'c_' or prefix == 'e_':
                self.content.convert_to_concept()
            elif prefix == 'r_':
                self.content.convert_to_reference()
            elif prefix == 't_':
                self.content.convert_to_task()
            self.write(doctype=Constants.outputclasses.value.get(self.content.outputclass)[2])

    def update_doctype_in_map(self):
        for topicref in self.ditamap.content.root.iter('topicref'):
            if topicref.attrib.get('href') == self.name:
                topicref.set('type', Constants.outputclasses.value.get(self.content.outputclass)[1])
        self.ditamap.write()

    def format_docdetails(self):
        """
        Only for Word-derived trees.
        """
        self.content.move_title_shortdesc_text_from_p()
        self.write()

    def cast(self):
        self.content.convert_to_concept()
        self.write()


class LocalReferenceInformationTopic(LocalTopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)

    def __repr__(self):
        return '<LocalTopic - RefInfo: ' + self.name + '>'

    def cast(self):
        self.content.convert_to_reference()
        self.write()


class LocalLegalInformationTopic(LocalTopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)

    def __repr__(self):
        return '<LocalTopic - LegalInfo: ' + self.name + '>'

    def add_title_and_shortdesc(self):
        self.content.add_legal_title_and_shortdesc()
        self.write()

    def cast(self):
        self.content.convert_to_reference()
        self.write()


class LocalConceptTopic(LocalTopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)
        self.children = []

    def __repr__(self):
        return '<LocalTopic - Concept: ' + self.name + '>'

    def cast(self):
        self.content.convert_to_concept()
        self.write()


class LocalTaskTopic(LocalTopic):

    def __init__(self, file_path, ditamap):
        super().__init__(file_path, ditamap)

    def __str__(self):
        return '<LocalTopic - Task: ' + self.name + '>'

    def cast(self):
        self.content.convert_to_task()
        self.write()


class LocalISHFile(LocalProjectFile):
    """
    Can use XMLContent functions for getting FTITLE and FMODULETYPE.
    """

    def __init__(self, file_path, ditamap):
        super().__init__(file_path)
        self.ditamap = ditamap
        self.check_ishobject()

    def __repr__(self):
        return '<ISHFile: ' + self.name + '>'

    def check_ishobject(self):
        if self.content.root.tag != 'ishobject':
            logger.critical('Malformed ISH file, no ishobject tag:', self.path)

    def rename_with_path(self, old_path, new_name):
        self.content.fattribute('FTITLE', 'set', new_name)
        self.name = new_name + self.ext
        self.path = os.path.join(self.folder, self.name)
        file_rename(old_path, self.path)
        self.write()


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
