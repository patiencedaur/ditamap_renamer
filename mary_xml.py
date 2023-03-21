from lxml import etree
from mary_debug import debugmethods


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

outputclasses: dict[str, str] = {
    # Document outputclass, indicated as an attribute of the first content tag.
    # Example: <task id=... outputclass="procedure">
    'context': 'c_',
    'lpcontext': 'c_',
    'explanation': 'e_',
    'procedure': 't_',
    'referenceinformation': 'r_',
    'legalinformation': 'e_'}


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

        self.outputclass = self.root.attrib.get('outputclass')
        self.title_tag = self.root.find('title')
        self.shortdesc_tag = self.root.find('shortdesc')
        self.local_links = self.root.findall('.//xref[@scope="local"]')

    def set_header(self, new_header):
        self.header = new_header

    @property
    def has_draft_comments(self):
        return True if len(self.draft_comments) > 0 else False

    def add_nbsp_after_table(self) -> etree.Element:
        """
        Finds the first section and appends a blank paragraph at its end.
        Adds this tag to the file: <#160;> </#160;>
        """
        section = self.root.find('section')
        if section:
            p = etree.SubElement(section, 'p')
            p.text = '\u00A0'
        return self.root

    def title_missing(self):
        if self.title_tag is None or self.title_tag.text is None or 'MISSING TITLE' in self.title_tag.text:
            return True
        return False

    def shortdesc_missing(self):
        if self.shortdesc_tag is None or self.shortdesc_tag.text is None \
                or 'SHORT DESCRIPTION' in self.shortdesc_tag.text:
            return True
        return False

    @property
    def draft_comments(self):
        draft_comments = []
        for dc in self.root.iter('draft-comment'):
            if dc is not None:
                draft_comments.append((dc, self.parent_map[dc]))
        return draft_comments

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
        parent_tag = self.parent_map[self.title_tag]
        if len(parent_tag.findall('shortdesc')) < 1:
            self.shortdesc_tag = TextElement('shortdesc', 'SHORT DESCRIPTION')
            parent_tag.insert(1, self.shortdesc_tag)

    def update_local_links(self, old_name: str, new_name: str) -> None:
        if len(self.local_links) == 0:
            print('No local links')
            return
        for link in self.local_links:
            link_href = link.attrib.get('href')
            if old_name in link_href:
                print("'" + self.title_tag.text + "'", 'has old link to', new_name, '(%s)' % link_href)
                new_name = link_href.replace(old_name, new_name)
                print('Updated link href:', new_name, '\n')
                link.set('href', new_name)

    def fattribute(self, attr_name, mode, new_value=None) -> str | None:  # for ishfiles only
        ishfields = self.root.find('ishfields')
        if not ishfields:
            print(self, 'is not an ISH file. Unable to get attribute', attr_name)
            return
        for ishfield in ishfields.findall('ishfield'):
            if ishfield.attrib.get('name') == attr_name:
                if mode == 'get':
                    return ishfield.text
                elif mode == 'set' and new_value:
                    ishfield.text = new_value
                else:
                    print('Usage: content.fattribute(attr_name, mode=\'get\'/\'set\',',
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
                        x.remove(redundant_p)
                        return
