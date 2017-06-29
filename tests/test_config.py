from OPSI.Config impor FILE_ADMIN_GROUP

import pytest


@pytest.mark.parametrize("value", [FILE_ADMIN_GROUP, ])
def testValueIsSet(value):
    assert value is not None
    assert value

