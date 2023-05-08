import _initialize
from marytreat.core.tridionclient import DocumentObject
from zeep.exceptions import Fault


guid = 'GUID-62444AD9-8A73-4645-8861-5A1014F32DF1'

src_obj = DocumentObject(id=guid)
try:
    fhpiproduct, _, _ = src_obj.get_current_dynamic_delivery_metadata()
except Fault:
    raise

prod_titles = [
    '10000', '100K', '12000', '15K', '20000', '200K',
    '25K', '30000', '35K', '50000', '5600', '5900',
    '5r', '6900', '6K', '6K Secure', '6r', '7000',
    '7500', '7600', '7800', '7900', '7eco', '7K', '7r',
    '8000', '8K', 'V12', 'W7250', 'WS6000', 'WS6600',
    'WS6800', 'WS6800p'
]

for prod_title, prod_value in zip(prod_titles, fhpiproduct.split(', ')):
    print(prod_title, prod_value)
