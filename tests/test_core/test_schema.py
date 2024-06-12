# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for schema core module."""


# external libs
from pytest import mark, raises

# internal libs
from refitt.core.schema import ListSchema, DictSchema, SchemaError, Size


class TestListSchema:
    """Unit tests for ListSchema."""

    @mark.unit
    def test_any(self) -> None:
        schema = ListSchema.any()
        assert schema.ensure([1, 2, 3, 'apple']) == [1, 2, 3, 'apple']
        with raises(SchemaError) as exc_info:
            schema.ensure(42)
        response, = exc_info.value.args
        assert response == 'Expected list, found int(42)'

    @mark.unit
    def test_any_sized(self) -> None:
        schema = ListSchema.any(size=4)
        assert schema.ensure([1, 2, 3, 'apple']) == [1, 2, 3, 'apple']
        with raises(SchemaError) as exc_info:
            schema.ensure([1, 2, 3, 4, 5])
        response, = exc_info.value.args
        assert response == 'Expected length 4, found length 5'

    @mark.unit
    def test_int_sized(self) -> None:
        schema = ListSchema.of(int, size=5)
        assert schema.ensure([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]
        with raises(SchemaError) as exc_info:
            schema.ensure([1, 2, 3, 4, 'apple'])
        response, = exc_info.value.args
        assert response == 'Expected all members to be type int, found str(\'apple\') at position 4'
        with raises(SchemaError) as exc_info:
            schema.ensure([1, 2, 3, 4, 5, 6])
        response, = exc_info.value.args
        assert response == 'Expected length 5, found length 6'

    @mark.unit
    def test_nested(self) -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        assert schema.ensure(data) == data

    @mark.unit
    def test_nested_raises_on_wrong_member_type(self) -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        with raises(SchemaError) as exc_info:
            schema.ensure([1, 2, 3])
        response, = exc_info.value.args
        assert response == 'Expected list, found int(1), for member at position 0'

    @mark.unit
    def test_nested_raises_on_wrong_member_type2(self) -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        with raises(SchemaError) as exc_info:
            schema.ensure([['a', 'b', 'c'], ['d', 'e', 'f'], ['g', 'h', 'i']])
        response, = exc_info.value.args
        assert response == ('Expected all members to be type float, found str(\'a\') at position 0, ' 
                            'for member at position 0')

    @mark.unit
    def test_nested_raises_on_wrong_member_size(self) -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        with raises(SchemaError) as exc_info:
            schema.ensure([[1, 2, 3], [4, 5, 6], [7, 8]])
        response, = exc_info.value.args
        assert response == 'Expected length 3, found length 2, for member at position 2'

    @mark.unit
    def test_nested_raises_on_wrong_size(self) -> None:
        schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        with raises(SchemaError) as exc_info:
            schema.ensure([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
        response, = exc_info.value.args
        assert response == 'Expected length 3, found length 4'

    @mark.unit
    def test_nested_equal_member_size(self) -> None:
        """Use Size.ALL_EQUAL within member to require all are the same length."""
        schema = ListSchema.of(ListSchema.of(float, size=Size.ALL_EQUAL))
        data = [[1, 2, 3], [4, 5, 6]]
        assert schema.ensure(data) == data
        with raises(SchemaError) as exc_info:
            schema.ensure([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, ]])
        response, = exc_info.value.args
        assert response == 'Expected members of equal size, found size=1 at position 3 but size=3 at position 0'


class TestDictSchema:
    """Unit tests for DictSchema."""

    @mark.unit
    def test_any(self) -> None:
        schema = DictSchema.any()
        assert schema.ensure({'a': 1, 'b': True}) == {'a': 1, 'b': True}

    @mark.unit
    def test_any_raises_on_non_str_keys(self) -> None:
        schema = DictSchema.any()
        with raises(SchemaError) as exc_info:
            schema.ensure({1: 'a', 2: 'b'})  # noqa: wrong type
        response, = exc_info.value.args
        assert response == 'Expected all keys to be type str, found int(1) at position 0'

    @mark.unit
    def test_any_raises_on_non_dict(self) -> None:
        schema = DictSchema.any()
        with raises(SchemaError) as exc_info:
            schema.ensure(['a', 'b', 'c'])
        response, = exc_info.value.args
        assert response == 'Expected DictSchema.any(), found list([\'a\', \'b\', \'c\'])'

    @mark.unit
    def test_any_raises_on_wrong_size(self) -> None:
        schema = DictSchema.any(size=3)
        with raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 2})
        response, = exc_info.value.args
        assert response == 'Expected length 3, found length 2'

    @mark.unit
    def test_member_type(self) -> None:
        schema = DictSchema.of(float)
        with raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 'banana'})
        response, = exc_info.value.args
        assert response == ('Expected all members to be type float, found str(\'banana\') '
                            'at position 1 for member \'b\'')

    @mark.unit
    def test_explicit_keys_missing(self) -> None:
        schema = DictSchema.of(float, keys=['a', 'b', 'c'])
        with raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 2})
        response, = exc_info.value.args
        assert response == 'Missing key \'c\''

    @mark.unit
    def test_explicit_keys_unexpected(self) -> None:
        schema = DictSchema.of(float, keys=['a', 'b', 'c'])
        with raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 2, 'c': 3, 'd': 4})
        response, = exc_info.value.args
        assert response == 'Unexpected key \'d\''

    @mark.unit
    def test_explicit_keys_with_types(self) -> None:
        schema = DictSchema.of({'a': float, 'b': str})
        with raises(SchemaError) as exc_info:
            schema.ensure({'a': 1, 'b': 2})
        response, = exc_info.value.args
        assert response == 'Expected type str for member \'b\', found int(2) at position 1'
