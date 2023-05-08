from threading import Thread


"""
Long-running threaded functions
"""


class ThreadedLocalMapFactory(Thread):
    def __init__(self, file_path, q):
        super().__init__(daemon=True)
        self.q = q
        self.file_path = file_path

    def run(self):
        from marytreat.core.local import LocalMap
        mp = LocalMap(self.file_path)
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

    def __init__(self, proj, q):
        super().__init__(daemon=True)
        self.project = proj
        self.q = q

    def run(self):
        message = self.project.check_for_titles_and_shortdescs()
        self.q.put(message)


class ThreadedMigrationCompletion(Thread):
    def __init__(self, proj, q):
        super().__init__(daemon=True)
        self.project = proj
        self.q = q

    def run(self):
        self.project.complete_migration()
        self.q.put('Migration completed')
