from enum import Enum
from secrets import username, password, hpi_hostname, f


class Constants(Enum):

    USERNAME = username
    PASSWORD = password
    HOSTNAME = hpi_hostname
    INDIGO_TOP_FOLDER = 8093282
    SCITEX_TOP_FOLDER = 7793322
    ISHFIELDS = f
    UNKNOWN = None

    def __add__(self, other):
        return str(self) + str(other)

    def __str__(self):
        return str(self.value)
