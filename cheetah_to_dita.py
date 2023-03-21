from mary_debug import debugmethods
from local import *

'''
This script helps to convert DITA files in Cheetah-to-DITA projects for SDL Tridion Docs.
It automates boring tasks like renaming files or adding shortdescs.
Created for HP Indigo by Dia Daur
'''

@debugmethods
class LocalMapFromCheetah(LocalMap):

    oc_object_types: dict[str, str] = {
        'referenceinformation': 'ReferenceInformationTopicFromCheetah(topic_path, self)',
        'procedure': 'TaskTopicFromCheetah(topic_path, self)',
        'legalinformation': 'LegalInformationTopicFromCheetah(topic_path, self)',
        'context': 'ConceptTopicFromCheetah(topic_path, self)',
        'lpcontext': 'ConceptTopicFromCheetah(topic_path, self)',
        'explanation': 'TopicFromCheetah(topic_path, self)'
    }

    def __init__(self, file_path: str) -> None:
        """
        Get list of topicrefs and their ish counterparts.
        """
        super().__init__(file_path)
        self.image_folder = self.folder
        self.images = self.get_images()
        self.pairs, self.topics, self.ishfiles = self.get_structure()

    def __str__(self) -> str:
        return '<LocalMapFromCheetah: ' + self.name + '>'

    def __repr__(self):
        return '<LocalMapFromCheetah: ' + self.name + '>'

    def __contains__(self, item) -> bool:
        if item in self.topics or item in self.ishfiles:
            return True
        return False

    def refresh(self) -> tuple[set['Image'], set['Pair'], set['TopicFromCheetah'], set['LocalISHFile']]:
        images = self.get_images()
        pairs, topics, ishfiles = self.get_structure()
        return images, pairs, topics, ishfiles

    def get_topic_from_topicref(self, topicref: etree.Element):
        topic_path: str = os.path.join(self.folder, topicref.attrib.get('href'))
        if not os.path.exists(topic_path):
            print('Cannot create LocalProjectFile from path %s. Aborting.' % topic_path)
        oc: str = etree.parse(topic_path).getroot().attrib.get('outputclass')
        if oc in self.oc_object_types.keys():
            topic = eval(LocalMapFromCheetah.oc_object_types[oc])
            if oc == 'context':
                children = topicref.findall('topicref')
                if len(children) > 0:
                    topic.children = [self.get_topic_from_topicref(child) for child in children]
        else:
            topic = LocalTopic(topic_path, self)
        return topic

    def get_pair_from_topicref(self, topicref: etree.Element) -> tuple['Pair', 'TopicFromCheetah', 'LocalISHFile']:
        topic = self.get_topic_from_topicref(topicref)
        topic_path: str = os.path.join(self.folder, topicref.attrib.get('href'))
        ish_path = topic_path.replace('.dita', '.3sish')
        ish = LocalISHFile(ish_path, self)
        pair = Pair(topic, ish)
        return pair, topic, ish

    def get_structure(self) -> tuple[set['Pair'], set['TopicFromCheetah'], set['LocalISHFile']]:
        pairs, topics, ishfiles = [], [], []
        for topicref in self.content.root.iter('topicref'):
            print('Initializing', topicref.attrib.get('href'), '...')
            pair, topic, ish = self.get_pair_from_topicref(topicref)
            pairs.append(pair)
            topics.append(topic)
            ishfiles.append(ish)
        return set(pairs), set(topics), set(ishfiles)

    def rename_pairs(self) -> int:
        """
        Rename files in map folder according to their titles and the style guide.
        Tracks repeating topic titles.
        """
        renamed_files_counter = 0
        topic_title_repetitions: dict[str, int] = {}
        for pair in self.pairs:
            if pair.dita.content.root.tag in doctypes:
                t = pair.dita.content.title_tag.text
                if t in topic_title_repetitions:
                    topic_title_repetitions[t] += 1
                else:
                    topic_title_repetitions[t] = 1
                num_rep = topic_title_repetitions[t]
                pair.update_name(num_rep)
                renamed_files_counter += 1
        print('Repeated topic titles:', {k: v for k, v in topic_title_repetitions.items() if v > 0})
        return renamed_files_counter

    def mass_edit(self) -> list[str]:
        """
        Mass edit short descriptions for typical documents. Returns a list of processed files.
        """
        shortdescs: dict[str, str] = {
            'Revision history and confidentiality notice': 'This chapter contains a table of revisions, printing instructions, and a notice of document confidentiality.',
            'Revision history': 'Below is the history of the document revisions and a list of authors.',
            'Printing instructions': 'Follow these recommendations to achieve the best print quality.'
        }

        processed_files: list[str] = []
        for topic in self.topics:
            content = topic.content
            if isinstance(topic, ReferenceInformationTopicFromCheetah):
                content.process_docdetails()
            if content.title_tag.text not in shortdescs.keys() or not content.shortdesc_missing():
                continue
            shortdesc: str = shortdescs[content.title]
            content.set_shortdesc(shortdesc)
            processed_files.append(topic.name)
            if content.title == 'Printing instructions':
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
        image_uses_in_topic: dict[Image, list[TopicFromCheetah]] = {}
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
            current_path: str = os.path.join(self.folder, img.href)
            new_path: str = os.path.join(self.folder, new_name)
            file_rename(current_path, new_path)
            # rename_in_pair hrefs in topics
            for topic in topics:
                for fig in topic.content.root.iter('fig'):
                    for img_tag in fig.iter('image'):
                        if img_tag.attrib.get('href') == img.href:
                            print('Renaming', img.href, 'to', new_name)
                            img_tag.set('href', new_name)
                topic.write()


@debugmethods
class TopicFromCheetah(LocalTopic):
    """
    Get DITA outputclass, title, and shortdesc.
    """
    def __init__(self, file_path: str, ditamap: LocalMapFromCheetah) -> None:
        super().__init__(file_path, ditamap)

    def __repr__(self):
        return '<TopicFromCheetah: ' + self.name + '>'

    def update_old_links_to_self(self, old):
        """
        Update links to this topic in the entire folder.
        """
        # Compare self.name to name found in links
        for pair in self.ditamap.pairs:
            topic = pair.dita
            topic.content.update_local_links(old, self.name)
            topic.write()

@debugmethods
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
            print('Malformed ISH file, no ishobject tag:', self.path)

    def rename_in_pair(self, old_path, new_name):
        self.content.fattribute('FTITLE', 'set', new_name)
        self.name = new_name + self.ext
        self.path = os.path.join(self.folder, self.name)
        self.write()
        file_delete(old_path)


@debugmethods
class ReferenceInformationTopicFromCheetah(LocalReferenceInformationTopic, TopicFromCheetah):
    def __init__(self, file_path, ditamap):
        LocalReferenceInformationTopic.__init__(self, file_path, ditamap)
        TopicFromCheetah.__init__(self, file_path, ditamap)

    def __repr__(self):
        return '<TopicFromCheetah - RefInfo: ' + self.name + '>'


@debugmethods
class LegalInformationTopicFromCheetah(LocalLegalInformationTopic, TopicFromCheetah):
    def __init__(self, file_path, ditamap):
        LocalLegalInformationTopic.__init__(self, file_path, ditamap)
        TopicFromCheetah.__init__(self, file_path, ditamap)

    def __repr__(self):
        return '<TopicFromCheetah - Legal Information: ' + self.name + '>'


@debugmethods
class ConceptTopicFromCheetah(LocalConceptTopic, TopicFromCheetah):
    def __init__(self, file_path, ditamap):
        LocalConceptTopic.__init__(self, file_path, ditamap)
        TopicFromCheetah.__init__(self, file_path, ditamap)

    def __repr__(self):
        return '<TopicFromCheetah - Concept: ' + self.name + '>'


@debugmethods
class TaskTopicFromCheetah(LocalTaskTopic, TopicFromCheetah):
    def __init__(self, file_path, ditamap):
        LocalTaskTopic.__init__(self, file_path, ditamap)
        TopicFromCheetah.__init__(self, file_path, ditamap)

    def __repr__(self):
        return '<TopicFromCheetah - Task: ' + self.name + '>'


@debugmethods
class Pair:

    def __init__(self, dita_obj: TopicFromCheetah, ish_obj: LocalISHFile):
        self.dita = dita_obj
        self.ish = ish_obj
        self.name = dita_obj.basename
        self.folder = dita_obj.folder
        self.ditamap = self.dita.ditamap

    def __repr__(self):
        return self.name + ' <.dita, .ish>'

    def __contains__(self, item):
        if isinstance(item, LocalProjectFile):
            return True if item == self.dita or item == self.ish else False

    def create_new_name(self, num_rep):
        """
        Creates a filename that complies with the style guide, based on the document title.
        Takes into account repeating titles of different topics.
        """
        new_name = re.sub(r'[\s\W]', '_',
                        self.dita.content.title_tag.text).replace('___',
                                                                  '_').replace('__',
                                                                               '_').replace('_the_', '_')
        new_name = re.sub(r'\W+', '', new_name)
        if new_name.endswith('_'):
            new_name = new_name[:-1]
        if new_name[1] == '_':
            new_name = new_name[2:]

        if self.dita.content.outputclass in outputclasses.keys():
            prefix = outputclasses.get(self.dita.content.outputclass)
            new_name = prefix + new_name

        if num_rep > 1:
            new_name = new_name + '_' + str(num_rep)

        return new_name

    def update_name(self, num_rep):
        """
        Updates pair file names and links to them in all the documents.
        Takes into account repeating titles of different topics.
        """
        old_pair = Pair(TopicFromCheetah(self.dita.path, self.ditamap), LocalISHFile(self.ish.path, self.ditamap))
        print('Updating name:', old_pair)
        print()

        if isinstance(self.dita, LegalInformationTopicFromCheetah):
            self.dita.add_title_and_shortdesc()

        if self.dita.content.title_missing():
            print('Skipped: %s, nothing to rename_in_pair (title missing)' % old_pair.name)
        else:
            new_name = self.create_new_name(num_rep)
            if old_pair.name == new_name:
                print('Skipped: %s, already renamed' % old_pair.name)
                return
            self.name = new_name
            self.dita.rename_in_pair(old_pair.dita.path, new_name)
            # Update links to this file throughout the folder
            self.dita.update_old_links_to_self(old_pair.dita.name)
            self.ish.rename_in_pair(old_pair.ish.path, new_name)
            self.ditamap.update_topicref(old_pair.dita.name, self.dita.name)
