# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for TNS interfaces."""


# type annotations
from __future__ import annotations
from typing import Union

# standard libs
import os
from io import BytesIO
import functools

# external libs
import pytest
from pandas import DataFrame

# internal libs
from refitt.core import base64
from refitt.database.model import Object
from refitt.data.tns import TNSConfig, TNSQueryManager, TNSCatalogManager, TNSCatalog
from tests.unit.test_data.test_tns import (MockTNSInterface, MockTNSCatalog,
                                           FAKE_TNS_ZTF_ID, FAKE_TNS_IAU_NAME, FAKE_TNS_TYPE_NAME,
                                           FAKE_TNS_REDSHIFT, FAKE_TNS_OBJECT_DATA, FAKE_TNS_CATALOG_DATA)


@pytest.mark.integration
class TestTNSCatalog:
    """Integration tests for TNSCatalog."""

    @functools.cached_property
    def data(self) -> DataFrame:
        """Load dataframe only once."""
        return TNSCatalog.from_zip(BytesIO(base64.decode(FAKE_TNS_CATALOG_DATA))).data

    def test_to_local(self) -> None:
        """Write data to local file system."""
        os.makedirs(TNSCatalog.DEFAULT_CACHE_DIR, exist_ok=True)
        TNSCatalog(self.data).to_local(TNSCatalog.DEFAULT_CACHE_PATH)
        assert os.path.isfile(TNSCatalog.DEFAULT_CACHE_PATH)
        assert TNSCatalog.from_local(TNSCatalog.DEFAULT_CACHE_PATH).data.equals(self.data)
        TNSCatalog.remove_cache()
        assert not os.path.exists(TNSCatalog.DEFAULT_CACHE_PATH)

    # NOTE: this test queries an external API and is not quick and occupies ~50MB.
    @pytest.mark.skip(reason='External API call with heavy payload')
    def test_from_web(self) -> None:
        """Query external TNS service for catalog."""
        TNSCatalog.remove_cache()
        assert not os.path.exists(TNSCatalog.DEFAULT_CACHE_PATH)
        first = TNSCatalog.from_web(cache=True)
        assert os.path.isfile(TNSCatalog.DEFAULT_CACHE_PATH)
        assert len(first.data) == len(TNSCatalog.from_web(cache=True).data)
        TNSCatalog.remove_cache()
        assert not os.path.exists(TNSCatalog.DEFAULT_CACHE_PATH)


class MockTNSQueryManager(TNSQueryManager):
    """A TNSQueryManager with a mocked interface for queries."""

    def __init__(self) -> None:
        super().__init__(MockTNSInterface())

    @classmethod
    def from_config(cls, config: Union[dict, TNSConfig] = None) -> MockTNSQueryManager:
        return cls()


@pytest.mark.integration
class TestTNSQueryManager:
    """Integration tests for TNSManager."""

    def test_update_object(self) -> None:
        """Calling update object updates the database."""
        Object.add({'aliases': {'ztf': FAKE_TNS_ZTF_ID}, 'type_id': 1, 'ra': 42, 'dec': 82})
        MockTNSQueryManager().update_object(FAKE_TNS_ZTF_ID)
        new = Object.from_alias(ztf=FAKE_TNS_ZTF_ID)
        assert new.aliases['iau'] == FAKE_TNS_IAU_NAME
        assert new.redshift == FAKE_TNS_REDSHIFT
        assert new.type.name == FAKE_TNS_TYPE_NAME
        assert new.data['tns'] == FAKE_TNS_OBJECT_DATA['data']['reply']
        assert len(new.data['history']) == 1
        Object.delete(new.id)


class MockTNSCatalogManager(TNSCatalogManager):
    """A TNSCatalogManager with a mocked interface for queries."""

    def __init__(self) -> None:
        super().__init__(MockTNSInterface())

    @classmethod
    def from_config(cls, config: Union[dict, TNSConfig] = None) -> MockTNSCatalogManager:
        return cls()

    @functools.cached_property
    def catalog(self) -> MockTNSCatalog:
        """Mock TNSCatalog uses fake data."""
        catalog = MockTNSCatalog.from_web(cache=False)  # NOTE: mock doesn't actually query the API
        catalog.data.loc[catalog.data.name == '2021adwz', 'internal_names'] += f', {FAKE_TNS_ZTF_ID}'
        catalog.data.loc[catalog.data.name == '2021adwz', 'redshift'] = FAKE_TNS_REDSHIFT
        return catalog


@pytest.mark.integration
class TestTNSCatalogManager:
    """Integration tests for TNSManager."""

    def test_update_object(self) -> None:
        """Calling update object updates the database."""
        manager = MockTNSCatalogManager()
        record = manager.catalog.get(FAKE_TNS_ZTF_ID)
        Object.add({'aliases': {'ztf': FAKE_TNS_ZTF_ID}, 'type_id': 1, 'ra': record.ra, 'dec': record.declination})
        manager.update_object(FAKE_TNS_ZTF_ID)
        new = Object.from_alias(ztf=FAKE_TNS_ZTF_ID)
        assert new.aliases['iau'] == record.name
        assert new.redshift == record.redshift
        assert new.type.name == 'Unknown'
        assert new.data['tns'] == record.to_json()
        assert len(new.data['history']) == 1  # NOTE: the redshift has changed (see MockTNSCatalogManager.catalog).
        Object.delete(new.id)
