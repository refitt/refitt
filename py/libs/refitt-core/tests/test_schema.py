# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for schema core module."""


# external libs
import pytest

# internal libs
from refitt.core.schema import ListSchema, DictSchema, SchemaError, Size


class TestListSchema:
    """Unit tests for ListSchema."""

    @staticmethod
    def test_any() -> None:
        schema = ListSchema.any()
        assert schema.ensure([1, 2, 3, 'apple']) == [1, 2, 3, 'apple']
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure(42)
        response, = exc_info.value.args
        assert response == 'Expected list, found int(42)'

    @staticmethod
    def test_any_sized() -> None:
        schema = ListSchema.any(size=4)
        assert schema.ensure([1, 2, 3, 'apple']) == [1, 2, 3, 'apple']
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure([1, 2, 3, 4, 5])
        response, = exc_info.value.args
        assert response == 'Expected length 4, found length 5'

    @staticmethod
    def test_int_sized() -> None:
        schema = ListSchema.of(int, size=5)
        assert schema.ensure([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure([1, 2, 3, 4, 'apple'])
        response, = exc_info.value.args
        assert response == 'Expected all members to be type int, found str(\'apple\') at position 4'
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure([1, 2, 3, 4, 5, 6])
        response, = exc_info.value.args
        assert response == 'Expected length 5, found length 6'

    @staticmethod
    def test_nested() -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        assert schema.ensure(data) == data

    @staticmethod
    def test_nested_raises_on_wrong_member_type() -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure([1, 2, 3])
        response, = exc_info.value.args
        assert response == 'Expected list, found int(1), for member at position 0'

    @staticmethod
    def test_nested_raises_on_wrong_member_type2() -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure([['a', 'b', 'c'], ['d', 'e', 'f'], ['g', 'h', 'i']])
        response, = exc_info.value.args
        assert response == ('Expected all members to be type float, found str(\'a\') at position 0, ' 
                            'for member at position 0')

    @staticmethod
    def test_nested_raises_on_wrong_member_size() -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure([[1, 2, 3], [4, 5, 6], [7, 8]])
        response, = exc_info.value.args
        assert response == 'Expected length 3, found length 2, for member at position 2'

    @staticmethod
    def test_nested_raises_on_wrong_size() -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
        response, = exc_info.value.args
        assert response == 'Expected length 3, found length 4'

    @staticmethod
    def test_nested_equal_member_size() -> None:
        """Use Size.ALL_EQUAL within member to require all are the same length."""
        schema = ListSchema.of(ListSchema.of(float, size=Size.ALL_EQUAL))
        data = [[1, 2, 3], [4, 5, 6]]
        assert schema.ensure(data) == data
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, ]])
        response, = exc_info.value.args
        assert response == 'Expected members of equal size, found size=1 at position 3 but size=3 at position 0'


class TestDictSchema:
    """Unit tests for DictSchema."""

    @staticmethod
    def test_any() -> None:
        schema = DictSchema.any()
        assert schema.ensure({'a': 1, 'b': True}) == {'a': 1, 'b': True}

    @staticmethod
    def test_any_raises_on_non_str_keys() -> None:
        schema = DictSchema.any()
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure({1: 'a', 2: 'b'})  # noqa: wrong type
        response, = exc_info.value.args
        assert response == 'Expected all keys to be type str, found int(1) at position 0'

    @staticmethod
    def test_any_raises_on_non_dict() -> None:
        schema = DictSchema.any()
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure(['a', 'b', 'c'])
        response, = exc_info.value.args
        assert response == 'Expected DictSchema.any(), found list([\'a\', \'b\', \'c\'])'

    @staticmethod
    def test_any_raises_on_wrong_size() -> None:
        schema = DictSchema.any(size=3)
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 2})
        response, = exc_info.value.args
        assert response == 'Expected length 3, found length 2'

    @staticmethod
    def test_member_type() -> None:
        schema = DictSchema.of(float)
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 'banana'})
        response, = exc_info.value.args
        assert response == ('Expected all members to be type float, found str(\'banana\') '
                            'at position 1 for member \'b\'')

    @staticmethod
    def test_explicit_keys_missing() -> None:
        schema = DictSchema.of(float, keys=['a', 'b', 'c'])
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 2})
        response, = exc_info.value.args
        assert response == 'Missing key \'c\''

    @staticmethod
    def test_explicit_keys_unexpected() -> None:
        schema = DictSchema.of(float, keys=['a', 'b', 'c'])
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 2, 'c': 3, 'd': 4})
        response, = exc_info.value.args
        assert response == 'Unexpected key \'d\''

    @staticmethod
    def test_explicit_keys_with_types() -> None:
        schema = DictSchema.of({'a': float, 'b': str})
        with pytest.raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 2})
        response, = exc_info.value.args
        assert response == 'Expected type str for member \'b\', found int(2) at position 1'
