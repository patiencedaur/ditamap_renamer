from threading import Thread
from marytreat.core.mary_debug import logger
from zeep.exceptions import Fault
from marytreat.core import process_word


"""
Long-running threaded functions
"""


class ThreadedLocalMapFactory(Thread):
    def __init__(self, file_path, process_word_flag, q):
        super().__init__(daemon=True)
        self.q = q
        self.file_path = file_path
        self.process_word_flag = process_word_flag

    def run(self):
        from marytreat.core.local import LocalMap
        mp = LocalMap(self.file_path)
        if mp.source == 'word' and self.process_word_flag.get() != 0:
            logger.info('Processing map derived from a Word file')
            mp.cast_topics_from_word()
            process_word.after_conversion(mp.folder)
        self.q.put(mp)


class ThreadedLocalTopicRenamer(Thread):

    def __init__(self, ditamap_obj, q):
        super().__init__(daemon=True)
        self.q = q
        self.ditamap = ditamap_obj

    def run(self):
        number_renamed_topics = self.ditamap.rename_topics()
        self.q.put(number_renamed_topics)


class ThreadedRepositorySearch(Thread):

    def __init__(self, part_no, folder, q):
        super().__init__(daemon=True)
        self.q = q
        self.part_no = part_no
        self.folder = folder

    def run(self):
        from marytreat.core.tridionclient import SearchRepository
        result = SearchRepository.scan_folder(self.part_no, self.folder, 0)
        self.q.put(result)


class ThreadedTitleAndDescriptionChecker(Thread):

    def __init__(self, mp, q):
        super().__init__(daemon=True)
        self.mp = mp
        self.q = q

    def run(self):
        from marytreat.core.tridionclient import Folder, Project
        map_fldr_id = self.mp.get_parent_folder_id()
        proj_id = Folder(id=map_fldr_id).get_location()[-2]  # parent folder of the map folder
        message = Project(id=proj_id).check_for_titles_and_shortdescs()
        self.q.put(message)


class ThreadedMigrationCompletion(Thread):
    def __init__(self, proj, q):
        super().__init__(daemon=True)
        self.project = proj
        self.q = q

    def run(self):
        self.project.complete_migration()
        self.q.put('Migration completed')


class ThreadedTagDownload(Thread):

    def __init__(self, tags: list['Tag'], q):
        super().__init__(daemon=True)
        self.tags = tags
        self.q = q

    def run(self):
        from marytreat.core.tridionclient import Tag
        csv_results = []
        for tag in self.tags:
            tag_value_file = tag.save_possible_values_to_file()
            csv_results.append(tag_value_file)
        self.q.put(csv_results)


class ThreadedSubmapGenerator(Thread):

    def __init__(self, topic: 'Topic', root_map: 'Map', q):
        super().__init__(daemon=True)
        self.topic = topic
        self.root_map = root_map
        self.q = q

    def run(self):
        from marytreat.core.tridionclient import Topic
        sbmp = self.topic.wrap_in_submap(self.root_map)
        self.q.put(sbmp)


class ThreadedMetadataDuplicator(Thread):

    def __init__(self, source: str, destination: str, q,
                 copy_product=0, copy_css=0):
        super().__init__(daemon=True)
        self.source_id = source
        self.destination_id = destination
        self.q = q
        self.copy_params = copy_product, copy_css

    def run(self):
        from marytreat.core.tridionclient import DocumentObject
        source = DocumentObject(id=self.source_id)
        destination = DocumentObject(id=self.destination_id)
        try:
            fhpiproduct, fhpicss, _ = source.get_current_dynamic_delivery_metadata()
            match self.copy_params:
                case (1, 0):
                    destination.set_metadata_for_dynamic_delivery(product=fhpiproduct)
                case (0, 1):
                    destination.set_metadata_for_dynamic_delivery(css=fhpicss)
                case (1, 1):
                    destination.set_metadata_for_dynamic_delivery(product=fhpiproduct, css=fhpicss)
            self.q.put((source, destination))
        except Fault as f:
            logger.error(f.message)
