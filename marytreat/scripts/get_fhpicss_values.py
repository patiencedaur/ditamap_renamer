import sys
import os

sys.path.append(os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)))))

from marytreat.core.tridionclient import Tag


fhpicss = Tag('fhpicustomersupportstories')
fhpicss.save_possible_values_to_file()
