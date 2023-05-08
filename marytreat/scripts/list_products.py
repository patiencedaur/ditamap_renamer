import _initialize
from marytreat.core.tridionclient import DocumentObject
from zeep.exceptions import Fault
from _validator import get_guid


guid = get_guid('Enter object to display product data from: ')

src_obj = DocumentObject(id=guid)
try:
    fhpiproduct, _, _ = src_obj.get_current_dynamic_delivery_metadata()
    for i, prod_value in enumerate(fhpiproduct.split(', ')):
        print(i, prod_value)
except Fault:
    raise
