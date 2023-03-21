from lxml import etree
import sys
from constants import Constants


class IshField:
    f = Constants.ISHFIELDS.value

    def __init__(self, name: str, text: str = '', operator: str = 'equal') -> None:
        self.name = name.upper()
        self.text = text
        self.operator = operator
        self.validate_name()
        self.validate_operator()

        self.ishtype: str = IshField.f.get(self.name).get('ishtype')
        self.level: str = IshField.f.get(self.name).get('level').lower()
        self.datatype: str = IshField.f.get(self.name).get('datatype')
        self.datasource: str | list = IshField.f.get(self.name).get('datasource')
        self.is_element: bool = IshField.f.get(self.name).get('is_element')

    def validate_name(self):
        try:
            assert self.name in IshField.f.keys()
        except AssertionError:
            print('Disallowed name: ' + self.name + '. Only names defined in IshFields.f are allowed.')
            sys.exit()

    def validate_operator(self):
        try:
            assert self.operator in ['equal', 'notequal', 'in', 'notin', 'like',
                                     'greaterthan', 'lessthan', 'greaterthanorequal',
                                     'lessthanorequal', 'between', 'empty', 'notempty']
        except AssertionError:
            print('Disallowed operator: ' + self.operator + '. Only names defined in IshFields.f are allowed.')
            sys.exit()

    def __repr__(self) -> str:
        return self.dict_form.__repr__()

    @property
    def get_attrib(self) -> dict[str, str]:
        attrib = {
            'text': self.text,
            'ishtype': self.ishtype,
            'level': self.level
        }
        if self.is_element:
            attrib['ishvaluetype'] = 'element'
        elif self.datatype == 'ISHLov':
            attrib['ishvaluetype'] = 'value'
        return attrib

    @property
    def xml_form(self) -> str:
        """
        :return: string <ishfield.../ishfield>
        """
        ishvt: str = ' ishvaluetype="element"' if self.is_element is not None else ''
        ishoper: str = ' ishoperator="' + self.operator + '"' if self.operator != 'equal' else ''

        return '<ishfield name="' + str(self.name) + '" level="' + str(self.level.lower()) + '"' + \
            ishvt + ishoper + '>' + str(self.text) + '</ishfield>'

    @property
    def dict_form(self) -> dict[str, dict]:
        self.name: str
        dict_form: dict[str, dict] = {self.name: self.get_attrib}
        return dict_form

    @property
    def tree_form(self) -> etree.Element:
        if self.is_element:
            root = etree.Element('ishfield', name=self.name, level=self.level, ishvaluetype='element')
        else:
            root = etree.Element('ishfield', name=self.name, level=self.level)
        if self.text:
            root.text = self.text
        return root
