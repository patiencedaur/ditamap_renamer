from copy import deepcopy
from re import search

from lxml import etree

from marytreat.core.constants import Constants
from marytreat.core.mary_debug import logger, debugmethods


def TextElement(tag: str, text: str, *args, **kwargs) -> etree.Element:
    element = etree.Element(tag, *args, **kwargs)
    element.text = text
    return element


def convert_tag_to_step(tag: etree.Element):
    tag.tag = 'step'
    cmd = TextElement('cmd', tag.text)
    tag.clear()
    tag.insert(0, cmd)


def is_list_item(p: etree.Element):
    if not p.text:
        return False
    if search('^\d+\. ', p.text) or search('^\u2751', p.text):
        return True
    return False


def convert_to_simpletable(tbl: etree.Element):
    tbl.tag = 'simpletable'
    widths = [colspec.attrib.get('colwidth') for colspec in tbl.findall('colspec')]
    if len(widths) > 0:
        tbl.set('relcolwidth', ' '.join(widths))
    for row in tbl.iter('row'):
        row.tag = 'strow'
        for entry in row.iter('entry'):
            entry.tag = 'stentry'
        tbl.append(row)
    tbl.remove(tbl.find('tgroup'))
    # add nbsp after table
    parent = tbl.getparent()
    parent.insert(parent.index(tbl) + 1, TextElement('p', '\u00A0'))


@debugmethods
class XMLContent:

    def __init__(self,
                 root: etree.Element,
                 header: str = '<?xml version="1.0" encoding="UTF-8"?>\n') -> None:
        self.root = root
        self.header = header
        self.tree = etree.ElementTree(element=root)
        self.parent_map: dict[etree.Element, etree.Element] = {c: p for p in self.root.iter() for c in p}
        self.title_tag = self.root.find('title')
        self.shortdesc_tag = self.root.find('shortdesc')
        self.outputclass = self.root.attrib.get('outputclass')
        self.local_links = self.root.findall('.//xref[@scope="local"]')

    def set_header(self, new_header):
        self.header = new_header

    @property
    def doctype(self):
        type_params = Constants.outputclasses.value.get(self.outputclass)
        if type_params:
            return type_params[2]
        if self.root.tag == 'map':
            return '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">'
        if self.root.tag == 'ishobject':
            return None

    @property
    def has_draft_comments(self):
        return True if len(self.draft_comments) > 0 else False

    def add_nbsp_after_table(self) -> etree.Element:
        """
        Appends a blank paragraph after the table.
        """
        tbl = self.root.find('table') or self.root.find('simpletable')
        if tbl is None:
            return
        next_p = tbl.getnext()
        if not next_p or (next_p.tag == 'p' and next_p.text == '\u00A0'):
            return
        parent = tbl.getparent()
        tbl_index = parent.index(tbl)
        parent.insert(tbl_index + 1, TextElement('p', '\u00A0'))

    def title_missing(self):
        if self.title_tag is None:
            return True
        if len(self.title_tag) > 0:  # contains another tag
            actual_title_text = ' '.join(list(self.title_tag.itertext()))
        else:
            actual_title_text = self.title_tag.text
        if not actual_title_text or 'MISSING TITLE' in actual_title_text:
            return True
        return False

    def shortdesc_missing(self):
        if self.shortdesc_tag is None:
            return True
        if len(self.shortdesc_tag) > 0:  # contains another tag
            return False
        actual_shortdesc = self.shortdesc_tag.text or ' '.join(list(self.shortdesc_tag.itertext()))
        if not actual_shortdesc or 'SHORT DESCRIPTION' in actual_shortdesc:
            return True
        return False

    @property
    def draft_comments(self):
        draft_comments = []
        for dc in self.root.iter('draft-comment'):
            if dc is not None:
                draft_comments.append((dc, self.parent_map[dc]))
        return draft_comments

    def set_outputclass(self, oc):
        self.root.set('outputclass', oc)
        self.outputclass = oc

    def set_title(self, new_title: str):
        self.title_tag.text = new_title

    def set_shortdesc(self, new_shortdesc: str):
        if self.shortdesc_tag is None:
            self.insert_shortdesc_tag()
        self.shortdesc_tag.text = new_shortdesc

    def insert_shortdesc_tag(self):
        """
        Adds the <shortdesc> tag to files where this part is completely missing.
        """
        if self.outputclass == 'frontcover' or self.outputclass == 'backcover':
            return
        parent_tag = self.parent_map[self.title_tag]
        if len(parent_tag.findall('shortdesc')) < 1:
            self.shortdesc_tag = TextElement('shortdesc', 'SHORT DESCRIPTION')
            parent_tag.insert(1, self.shortdesc_tag)

    def update_local_links(self, old_name: str, new_name: str) -> None:
        """
        Update links to a local DITA document in this file.
        :param old_name: old name of the DITA document (ex. r_2_1_1.dita)
        :param new_name: new name of the DITA document (ex. r_Printing_instructions.dita)
        :return:
        """
        if len(self.local_links) == 0:
            return
        logger.debug('Title: ' + str(self.title_tag.text))
        logger.debug('Links: ' + str([l.attrib.get('href') for l in self.local_links]))
        logger.debug('Renaming links from ' + old_name + ' to ' + new_name)
        for link in self.local_links:
            link_href = link.attrib.get('href')
            if old_name in link_href:
                logger.info("'" + str(self.title_tag.text) + "'" +
                            ' has old link to ' + new_name + ' (%s)' % link_href)
                new_name = link_href.replace(old_name, new_name)
                logger.info('Updated link href: ' + new_name + '\n')
                link.set('href', new_name)

    def fattribute(self, attr_name, mode, new_value=None):  # for ishfiles only
        ishfields = self.root.find('ishfields')
        if ishfields is None:
            logger.error(self, 'is not an ISH file. Unable to get attribute', attr_name)
            return
        for ishfield in ishfields.findall('ishfield'):
            if ishfield.attrib.get('name') == attr_name:
                if mode == 'get':
                    return ishfield.text
                elif mode == 'set' and new_value:
                    ishfield.text = new_value
                else:
                    logger.error('Usage: content.fattribute(attr_name, mode=\'get\'/\'set\',',
                                  'new_value=\'myvalue\') #  set value if mode=\'set\'.',
                                  'This method can set fname or fmoduletype')

    def process_docdetails(self):
        """
        Identify docdetails topic, add shortdesc, convert CALS table to simpletable.
        """
        # identify docdetails topic
        list_vars = list(self.root.iter('ph'))
        cond_docdetails = len(list_vars) > 0 and list_vars[0].attrib.get('varref') == 'DocTitle'
        if not cond_docdetails:
            return
        if self.shortdesc_missing:
            self.set_shortdesc('Document details')
        for table_tag in self.root.iter('table'):
            convert_to_simpletable(table_tag)  # also adds nbsp after table

    def add_legal_title_and_shortdesc(self):
        self.set_title('Legal information')
        self.insert_shortdesc_tag()
        for first_level in self.root:
            for x in first_level:
                if 'outputclass' in x.attrib.keys() and x.attrib['outputclass'] == 'copyright':
                    redundant_p = x[0]
                    if "Copyright" in redundant_p.text:
                        self.set_shortdesc(redundant_p.text)
                        return

    def rename_tag(self, tag_name, new_name):
        if tag_name != self.root.tag:
            elems = self.root.findall(tag_name)
            for elem in elems:
                elem.tag = new_name
        else:
            self.root.tag = new_name

    def convert_to_concept(self):
        concept_header = '<?xml version="1.0" encoding="UTF-8"?>'
        self.set_header(concept_header)
        self.rename_tag('topic', 'concept')
        self.rename_tag('body', 'conbody')

    def convert_to_reference(self):
        ref_header = '<?xml version="1.0" encoding="UTF-8"?>'
        self.set_header(ref_header)
        self.rename_tag('topic', 'reference')
        self.rename_tag('body', 'refbody')
        if self.root.findall('section') is None:
            refbody = self.root.find('refbody')
            section = deepcopy(refbody)
            section.tag = 'section'
            refbody.clear()
            refbody.insert(0, section)
        self.add_nbsp_after_table()

    def convert_to_task(self):
        task_header = '<?xml version="1.0" encoding="UTF-8"?>'
        self.set_header(task_header)
        self.rename_tag('topic', 'task')
        self.rename_tag('body', 'taskbody')
        self.convert_lists_to_steps()

    def convert_lists_to_steps(self):
        # if there are no ol's,
        # then get all p's that look like list items, that is:
        # starts with a number followed by a dot
        ols = self.root.findall('ol')
        if len(ols) > 0:
            for ol in ols:
                ol.tag = 'steps'
                for li in ol.iter('li'):
                    convert_tag_to_step(li)
        else:  # process p's instead of ordered lists
            for p in filter(lambda x: is_list_item(x), self.root.iter('p')):
                # remove the numbers at the start
                numeration = search('^\d+\. ', p.text).group(0)
                p.text.replace(numeration, '')
                checkboxes = search('^\u2751 ', p.text).group(0)
                p.text.replace(checkboxes, '')
                convert_tag_to_step(p)
            self.wrap_steps()

    def wrap_steps(self):
        assert self.outputclass == 'procedure'
        taskbody = self.root.findall('taskbody')[0]
        if len(taskbody.findall('step')) == 0:
            return
        steps = deepcopy(taskbody)
        steps.tag = 'steps'
        taskbody.clear()
        taskbody.append(steps)

    def is_mostly_list(self):
        ol = self.root.find('ol')
        if ol is not None:
            return True
        for p in self.root.iter('p'):
            if is_list_item(p):
                return True
        return False

    def has_table(self):
        tables = [t.tag for t in self.root.iter('table')] + [st.tag for st in self.root.iter('simpletable')]
        if len(tables) > 0:
            return True
        return False

    def move_title_shortdesc_text_from_p(self):
        try:
            body = self.tree.xpath('refbody|body')[0]
            p_tags = body.findall('p')
            future_title = p_tags[0]
            future_shortdesc = p_tags[1].find('b')
            logger.debug('Future title: ' + future_title.text)
            logger.debug('Future shortdesc: ' + future_shortdesc.text)
            self.set_title(future_title.text)
            self.set_shortdesc(future_shortdesc.text)
            for i in range(2):
                body.remove(p_tags[i])
        except IndexError:
            return

    def detect_type(self):
        if self.is_mostly_list():
            return 'procedure'
        elif self.has_table():
            return 'referenceinformation'
        else:
            return 'explanation'

    def wrap_images_in_fig(self):
        if len(self.root.findall('fig')) > 0:
            return
        for image in self.root.iter('image'):
            img_tag = deepcopy(image)
            image.tag = 'fig'
            image.clear()
            image.append(img_tag)

    def images_to_png(self):
        for image in self.root.iter('image'):
            href = image.attrib.get('href')
            href_and_ext = href.split('.')
            if href_and_ext[-1] != 'png':
                href_png = '.'.join((href_and_ext[0], 'png'))
                logger.debug(href_png)
                image.set('href', href_png)

    def add_topic_groups(self):
        if self.root.findall('topicgroup'):
            return
        body_group = etree.Element('topicgroup', {
            'collection-type': 'sequence',
            'outputclass': 'body'
        })
        appendix_group = etree.Element('topicgroup', {
            'collection-type': 'sequence',
            'outputclass': 'appendices'
        })
        # assuming we already have a root context topic
        self.root[1].insert(2, body_group)
        self.root[1].insert(-2, appendix_group)

    def process_notes(self):
        for el in self.root.iter():
            if not el.text:
                continue
            whitespace_only = list(filter(lambda i: ord(i) == 32 or ord(i) == 10,
                                          [item for item in el.text]))
            if whitespace_only:
                continue
            if 'NOTE:' in el.text:
                el.text.replace('NOTE:', '')
                logger.debug('Found a note!', self.tree.getpath(el))
                if el.tag == 'p':
                    note_content = deepcopy(el)
                    note = el
                else:
                    nearest_p = yield etree.AncestorsIterator(el, 'p')
                    note_content = deepcopy(nearest_p)
                    note = nearest_p
                note.tag = 'note'
                note.clear()
                note.append(note_content)
                logger.debug(self.tree.getpath(note_content))

    def create_shortdesc_from_first_p(self):
        if self.shortdesc_missing():
            body = self.tree.xpath('body|refbody|taskbody|conbody')
            try:
                first_el = body[0][0]
                following_el = body[0][1]
                if first_el.tag == 'p' and first_el.text and not following_el.find('image'):
                    self.shortdesc_tag.text = first_el.text
                    body[0].remove(first_el)
            except IndexError:
                return

    def gen_shortdesc(self):
        """
        Generates a short description: takes the title, changes the gerund to an infinitive,
        and puts it in a general phrase.
        Procedure outputclass only.
        :return: new short description
        """
        from lemminflect import getLemma
        if self.outputclass != 'procedure':
            return
        if not self.title_tag.text:
            return
        title_words = self.title_tag.text.split(' ')
        logger.debug(title_words)
        if title_words[0].endswith('ing'):
            infinitive = getLemma(title_words[0], upos='VERB')[0]
            logger.debug(infinitive)
            title_words[0] = 'To ' + infinitive.lower()
            new_shortdesc = ' '.join(title_words) + ', follow the steps in this section.'
        else:
            new_shortdesc = "Follow the instructions in this section."
        logger.debug(str(self) + ': ' + new_shortdesc)
        return new_shortdesc

    def remove_context(self):
        if self.outputclass != 'procedure':
            return
        taskbody = self.tree.xpath('taskbody')
        try:
            cntxt = taskbody[0].find('context')
            taskbody[0].remove(cntxt)
        except IndexError as e:
            logger.info(e)
            return
