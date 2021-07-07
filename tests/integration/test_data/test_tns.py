# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for TNS interfaces."""


# type annotations
from __future__ import annotations
from typing import Union

# external libs
import pytest

# internal libs
from refitt.data.tns import TNSConfig, TNSManager
from refitt.database.model import Object
from tests.unit.test_data.test_tns import (MockTNSInterface, FAKE_TNS_ZTF_ID, FAKE_TNS_IAU_NAME, FAKE_TNS_TYPE_NAME,
                                           FAKE_TNS_REDSHIFT, FAKE_TNS_OBJECT_DATA)


class MockTNSManager(TNSManager):
    """A TNSManager with a mocked interface for queries."""

    def __init__(self) -> None:
        super().__init__(MockTNSInterface())

    @classmethod
    def from_config(cls, config: Union[dict, TNSConfig] = None) -> MockTNSManager:
        return cls()


@pytest.mark.integration
class TestTNSManager:
    """Integration tests for TNSManager."""

    def test_update_object(self) -> None:
        """Calling update object updates the database."""
        Object.add({'aliases': {'ztf': FAKE_TNS_ZTF_ID}, 'type_id': 1, 'ra': 42, 'dec': 82})
        MockTNSManager().update_object(FAKE_TNS_ZTF_ID)
        new = Object.from_alias(ztf=FAKE_TNS_ZTF_ID)
        assert new.aliases['iau'] == FAKE_TNS_IAU_NAME
        assert new.redshift == FAKE_TNS_REDSHIFT
        assert new.type.name == FAKE_TNS_TYPE_NAME
        assert new.data['tns'] == FAKE_TNS_OBJECT_DATA['data']['reply']
        assert len(new.data['history']) == 1
        Object.delete(new.id)
