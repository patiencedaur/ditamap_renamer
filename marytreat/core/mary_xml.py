from copy import deepcopy
from re import search

from lxml import etree

from marytreat.core.constants import Constants
from marytreat.core.mary_debug import logger, debugmethods


def TextElement(tag: str, text: str, *args, **kwargs) -> etree.Element:
    element = etree.Element(tag, *args, **kwargs)
    element.text = text
    return element


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
       Appends a blank paragraph at the end of the first section.
        Adds this tag to the file: <#160;> </#160;>
        """
        section = yield self.root.iter('section')
        if section is None:
            return
        empty_paragraphs = [p for p in self.root.iter('p') if p.text == '\u00A0']
        if len(empty_paragraphs) > 0:
            return
        p = TextElement('p', '\u00A0')
        section.append(p)

    def title_missing(self):
        if self.title_tag is None or \
                (self.title_tag is not None and self.title_tag.text is None) or \
                (self.title_tag.text is not None and 'MISSING TITLE' in self.title_tag.text):
            return True
        return False

    def shortdesc_missing(self):
        if self.shortdesc_tag is None or \
                (self.shortdesc_tag is not None and
                 self.shortdesc_tag.text is not None and 'SHORT DESCRIPTION' in self.shortdesc_tag.text):
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
        print(self.title_tag.text, self.local_links, old_name, new_name)
        for link in self.local_links:
            link_href = link.attrib.get('href')
            if old_name in link_href:
                logger.info("'" + self.title_tag.text + "'" +
                            ' has old link to ' + new_name + ' (%s)' % link_href)
                new_name = link_href.replace(old_name, new_name)
                logger.info('Updated link href: ' + new_name + '\n')
                link.set('href', new_name)

    def fattribute(self, attr_name, mode, new_value=None) -> str | None:  # for ishfiles only
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
        # identify docdetails topic
        list_vars = list(self.root.iter('ph'))
        cond_docdetails = len(list_vars) > 0 and list_vars[0].attrib.get('varref') == 'DocTitle'
        if cond_docdetails and self.shortdesc_missing:
            # add short description
            self.set_shortdesc('Document details')
            self.add_nbsp_after_table()

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
                    self.convert_tag_to_step(li)
        else:  # process p's instead of ordered lists
            for p in filter(lambda x: self.is_list_item(x), self.root.iter('p')):
                # remove the numbers at the start
                numeration = search('^\d+\. ', p.text).group(0)
                p.text.replace(numeration, '')
                self.convert_tag_to_step(p)
            self.wrap_steps()

    def convert_tag_to_step(self, tag: etree.Element):
        tag.tag = 'step'
        cmd = TextElement('cmd', tag.text)
        tag.clear()
        tag.insert(0, cmd)

    def is_list_item(self, p):
        if search('^\d+\. ', p.text):
            return True
        return False

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
            if self.is_list_item(p):
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
            logger.debug(future_title.text, future_shortdesc.text)
            self.set_title(future_title.text)
            self.set_shortdesc(future_shortdesc.text)
            for i in range(2):
                body.remove(p_tags[i])
        except IndexError:
            return

    def detect_type(self):
        if self.is_mostly_list():
            return 'procedure'
        else:
            if self.has_table():
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
    # def wrap_element(self, element: etree.Element, wrapper_tag: str):
    #     wrapper = deepcopy(element)
    #     wrapper.tag = wrapper_tag
    #     wrapper.clear()
    #     wrapper.append(element)
    #     return wrapper

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
