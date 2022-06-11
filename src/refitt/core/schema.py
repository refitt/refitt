# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Define and enforce JSON schema against provided data."""


# type annotations
from __future__ import annotations
from typing import Union, Optional, TypeVar, Type, List, Dict

# standard libs
from abc import ABC
from enum import Enum

# public interface
__all__ = ['SchemaError', 'SchemaDefinitionError', 'ListSchema', 'DictSchema', 'Size', ]


class SchemaError(Exception):
    """Raised on schema validation error."""


class SchemaDefinitionError(Exception):
    """A malformed definition of the schema itself."""


# Allowable non-container types
V = TypeVar('V', bool, int, float, str)
Value_T = Union[V, List['Value_T'], Dict[str, 'Value_T']]
Schema_T = Union[Type[V], 'ListSchema', 'DictSchema']


class Schema(ABC):
    """Generic base class for all schema types."""


class Size(Enum):
    """Special sizing indicator to signal requirements."""
    ALL_EQUAL = 0


SizeType = Union[int, Size]


class ListSchema(Schema):
    """
    List schema with specified or unspecified member type and size.

    Examples:

        Allow any list if nothing specified.
        >>> schema = ListSchema.any()
        >>> schema.ensure([1, 2, 3, 'apple'])
        [1, 2, 3, 'apple']

        The input will ensure at least a list, however.
        >>> schema = ListSchema.any()
        >>> schema.ensure({'a': 1, 'b': 2})  # noqa
        Traceback (most recent call last):
        schema.SchemaError: Expected list, found dict({'a': 1, 'b': 2})

        Require a particular length by specifying a `size`.
        >>> schema = ListSchema.any(size=4)
        >>> schema.ensure([1, 2, 3, 4, 5])
        Traceback (most recent call last):
        schema.SchemaError: Expected length 4, found length 5

        Require a specified type with the `.of` method.
        >>> schema = ListSchema.of(int, size=5)
        >>> schema.ensure([1, 2, 3, 4, 5])
        [1, 2, 3, 4, 5]

        Specifying `float` will allow an `int` but not the reverse.
        >>> schema = ListSchema.of(float, size=5)
        >>> schema.ensure([1, 2, 3, 4, 'apple'])
        Traceback (most recent call last):
        schema.SchemaError: Expected all members to be type float, found str('apple') at position 4

        A ListSchema can be nested.
        >>> schema = ListSchema.of(ListSchema.of(float, size=3), size=3)
        >>> schema.ensure([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        Nested ListSchema members can have categorical size requirements.
        >>> schema = ListSchema.of(ListSchema.of(float, size=Size.ALL_EQUAL))
        >>> schema.ensure([[1, 2], [3, 4], [5, ]])
        Traceback (most recent call last):
        schema.SchemaError: Expected all members to have equal size, found size=1 at position 2 (expected size=2)
    """

    __size: Optional[SizeType] = None
    __member_type: Optional[Schema_T] = None

    def __init__(self, member_type: Schema_T = None, size: int = None) -> None:
        """Directly initialize list with `member_type`."""
        self.member_type = member_type
        self.size = size

    @property
    def member_type(self) -> Optional[Schema_T]:
        return self.__member_type

    @member_type.setter
    def member_type(self, some_type: Optional[Schema_T]) -> None:
        if some_type is None or some_type in V.__constraints__ or isinstance(some_type, (ListSchema, DictSchema)):
            self.__member_type = some_type
        else:
            given = some_type if not hasattr(some_type, '__name__') else some_type.__name__
            raise SchemaDefinitionError(f'Unsupported member type \'{given}\'')

    @property
    def size(self) -> Optional[SizeType]:
        return self.__size

    @size.setter
    def size(self, value: Optional[SizeType]) -> None:
        if value is None or isinstance(value, (int, Size)):
            self.__size = value
        else:
            raise TypeError(f'ListSchema.size expects integer or {type(Size)}')

    @classmethod
    def any(cls, size: SizeType = None) -> ListSchema:
        """Allow any member type."""
        return cls(size=size)

    @classmethod
    def of(cls, member_type: Schema_T, size: SizeType = None) -> ListSchema:
        """Strict member type enforcement."""
        return cls(member_type=member_type, size=size)

    @classmethod
    def infer(cls, data: Value_T) -> ListSchema:
        """Infer schema from example `data`."""
        raise NotImplementedError()

    def ensure(self, value: Value_T) -> Value_T:
        """Returns `value` not in violation of specified schema."""
        self.__check_type(value)
        self.__check_size(value)
        self.__check_member_types(value)
        return value

    def __check_member_types(self, value: Value_T) -> None:
        if self.member_type is not None:
            if self.member_type is float:
                self.__check_float(value)
            elif self.member_type in V.__constraints__:
                self.__check_generic(value)
            else:
                self.__check_container(value)

    def __check_container(self, value: Value_T) -> None:
        for i, member in enumerate(value):
            try:
                self.member_type.ensure(member)
            except SchemaError as error:
                raise SchemaError(f'{error}, for member at position {i}') from error

    def __check_generic(self, value: Value_T) -> None:
        for i, member in enumerate(value):
            if type(member) is not self.member_type:  # NOTE: we don't want to allow `isinstance(True, int)`
                raise SchemaError(f'Expected all members to be type {self.member_type.__name__}, '
                                  f'found {member.__class__.__name__}({repr(member)}) at position {i}')

    def __check_float(self, value: Value_T) -> None:
        for i, member in enumerate(value):
            if type(member) not in (float, int,):
                raise SchemaError(f'Expected all members to be type {self.member_type.__name__}, '
                                  f'found {member.__class__.__name__}({repr(member)}) at position {i}')

    def __check_size(self, value: Value_T) -> None:
        if isinstance(self.size, int) and len(value) != self.size:
            raise SchemaError(f'Expected length {self.size}, found length {len(value)}')
        if hasattr(self.member_type, 'size') and isinstance(self.member_type.size, Size):
            if self.member_type.size is Size.ALL_EQUAL:
                if not hasattr(value[0], '__len__'):
                    raise SchemaError(f'Expected sized members, found {type(value[0])}({value[0]}) '
                                      f'at position 0')
                s0 = len(value[0])
                for i, member in enumerate(value):
                    si = len(member)
                    if si != s0:
                        raise SchemaError(f'Expected members of equal size, found size={si} at position {i} '
                                          f'but size={s0} at position 0')

    @staticmethod
    def __check_type(value: list) -> None:
        """Verify `value` is a list."""
        if not isinstance(value, list):
            raise SchemaError(f'Expected list, found {value.__class__.__name__}({value})')

    def __repr__(self) -> str:
        if self.member_type is None:
            return 'ListSchema.any()' if self.size is None else f'ListSchema.any(size={self.size})'
        if self.size is None:
            if isinstance(self.member_type, (ListSchema, DictSchema)):
                return f'ListSchema.of({repr(self.member_type)})'
            else:
                return f'ListSchema.of({self.member_type.__name__})'
        else:
            if isinstance(self.member_type, (ListSchema, DictSchema)):
                return f'ListSchema.of({repr(self.member_type)}, size={self.size})'
            else:
                return f'ListSchema.of({self.member_type.__name__}, size={self.size})'


# the schema type or associated keys with schema type values
Dict_Schema_T = Union[Schema_T, Dict[str, Schema_T]]


class DictSchema(Schema):
    """
    Dictionary schema with specified or unspecified member types (optionally with required keys).

    Examples:

        Allow any dictionary with any member types.
        >>> schema = DictSchema.any()
        >>> schema.ensure({'a': 1, 'b': 3.14, 'c': 'apple'})
        {'a': 1, 'b': 3.14, 'c': 'apple'}

        Require a particular size.
        >>> schema = DictSchema.any(size=3)
        >>> schema.ensure({'a': 1, 'b': 2})
        Traceback (most recent call last):
        schema.SchemaError: Expected length 3, found length 2

        Require a particular member type.
        >>> schema = DictSchema.of(float, size=3)
        >>> schema.ensure({'a': 1, 'b': 2, 'c': 3})
        {'a': 1, 'b': 2, 'c': 3}

        Require a particular member type with explicit keys.
        >>> schema = DictSchema.of(float, keys=['a', 'b', 'c'])
        >>> schema.ensure({'a': 1, 'b': 2})
        Traceback (most recent call last):
        schema.SchemaError: Missing key 'c'

        Require explicit types for specific keys.
        >>> schema = DictSchema.of({'a': float, 'b': str})
        >>> schema.ensure({'a': 1, 'b': 2})
        Traceback (most recent call last):
        schema.SchemaError: Expected type str for member 'b', found int(2) at position 1

        Nest schema within themselves.
        >>> schema = DictSchema.of(ListSchema.of(float, size=3), keys=['a', 'b', 'c'])
        >>> schema.ensure({'a': [1, 2, 3], 'b': [4, 5, 6], 'c': [7, 8, 9]})
        {'a': [1, 2, 3], 'b': [4, 5, 6], 'c': [7, 8, 9]}
    """

    __size: Optional[SizeType] = None
    __member_type: Optional[Dict_Schema_T] = None

    def __init__(self, member_type: Dict_Schema_T = None, size: SizeType = None) -> None:
        """Directly initialize list with `member_type`."""
        self.member_type = member_type
        self.size = size

    @property
    def member_type(self) -> Optional[Dict_Schema_T]:
        return self.__member_type

    @member_type.setter
    def member_type(self, some_type: Optional[Dict_Schema_T]) -> None:
        if some_type is None or some_type in V.__constraints__ or isinstance(some_type, (ListSchema, DictSchema)):
            self.__member_type = some_type
        elif isinstance(some_type, dict):
            for i, (key, value) in enumerate(some_type.items()):
                if not isinstance(key, str):
                    raise SchemaDefinitionError(f'Expected string keys, found {key.__class__.__name__}({key}) '
                                                f'at position {i}')
                if (value is not None and value not in V.__constraints__ and
                        not isinstance(value, (ListSchema, DictSchema))):
                    given = value if not hasattr(value, '__name__') else value.__name__
                    raise SchemaDefinitionError(f'Unsupported member type \'{given}\' for \'{key}\' '
                                                f'at position {i}')
            else:
                self.__member_type = some_type
        else:
            given = some_type if not hasattr(some_type, '__name__') else some_type.__name__
            raise TypeError(f'Unsupported member type \'{given}\'')

    @property
    def size(self) -> Optional[SizeType]:
        return self.__size

    @size.setter
    def size(self, value: Optional[SizeType]) -> None:
        if value is None:
            self.__size = None
        elif isinstance(value, (int, Size)):
            if isinstance(self.member_type, dict):
                raise SchemaDefinitionError(f'Cannot specify size if keys given')
            self.__size = value
        else:
            raise SchemaDefinitionError(f'Size must be an integer, given {value.__class__.__name__}({value})')

    @classmethod
    def any(cls, size: SizeType = None) -> DictSchema:
        """Allow any keys and member types, optionally require `size`."""
        return cls(size=size)

    @classmethod
    def of(cls, member_type: Dict_Schema_T, keys: List[str] = None, size: SizeType = None) -> DictSchema:
        """
        Specify required member types, optionally with keys. A `size` is only allowed if not
        specifying keys.
        """
        if isinstance(member_type, dict):
            if keys is not None:
                raise SchemaDefinitionError('Cannot specify \'keys\' for explicit dictionary')
            if size is not None:
                raise SchemaDefinitionError('Cannot specify \'size\' for explicit dictionary')
            else:
                return cls(member_type=member_type)
        else:
            if keys is not None:
                if size is not None:
                    raise SchemaDefinitionError('Cannot specify \'size\' for explicit \'keys\'')
                return cls(member_type={key: member_type for key in keys})
            else:
                return cls(member_type=member_type, size=size)

    def ensure(self, value: Value_T) -> dict:
        """Returns `value` not in violation of specified schema."""
        self.__check_type(value)
        if isinstance(self.member_type, dict):
            self.__check_dict(value)
        else:
            self.__check_any(value)
        return value

    def __check_any(self, value: Value_T) -> None:
        """Ensure valid types for `value` for singular `member_type`."""
        if self.size is not None and len(value) != self.size:
            raise SchemaError(f'Expected length {self.size}, found length {len(value)}')
        for i, key in enumerate(value.keys()):
            if not isinstance(key, str):
                raise SchemaError(f'Expected all keys to be type str, '
                                  f'found {key.__class__.__name__}({repr(key)}) at position {i}')
        if self.member_type is None:
            return  # anything goes
        if self.member_type is float:
            for i, (key, member) in enumerate(value.items()):
                if type(member) not in (float, int):
                    raise SchemaError(f'Expected all members to be type {self.member_type.__name__}, '
                                      f'found {member.__class__.__name__}({repr(member)}) at position {i} '
                                      f'for member \'{key}\'')
        elif self.member_type in V.__constraints__:
            for i, (key, member) in enumerate(value.items()):
                if type(member) is not self.member_type:  # NOTE: we don't want to allow `isinstance(True, int)`
                    raise SchemaError(f'Expected all members to be type {self.member_type.__name__}, '
                                      f'found {member.__class__.__name__}({repr(member)}) at position {i} '
                                      f'for member \'{key}\'')
        elif type(self.member_type) in (ListSchema, DictSchema):
            for i, (key, member) in enumerate(value.items()):
                try:
                    self.member_type.ensure(member)
                except SchemaError as error:
                    raise SchemaError(f'{error}, for member \'{key}\'') from error

    def __check_dict(self, value: Value_T) -> None:
        """Ensure `value` types for dictionary of expected keys in `member_type`."""
        for i, (key, member) in enumerate(self.member_type.items()):
            if key not in value:
                raise SchemaError(f'Missing key \'{key}\'')
        for i, (key, member) in enumerate(value.items()):
            if key not in self.member_type:
                raise SchemaError(f'Unexpected key \'{key}\'')
        for i, (key, member) in enumerate(value.items()):
            member_type = self.member_type[key]
            if member_type is float:
                if type(member) not in (float, int):
                    raise SchemaError(f'Expected type {member_type.__name__} for member \'{key}\', '
                                      f'found {member.__class__.__name__}({repr(member)}) at position {i}')
            elif member_type in V.__constraints__:
                if type(member) is not member_type:  # NOTE: we don't want to allow `isinstance(True, int)`
                    raise SchemaError(f'Expected type {member_type.__name__} for member \'{key}\', '
                                      f'found {member.__class__.__name__}({repr(member)}) at position {i}')
            elif type(member_type) in (ListSchema, DictSchema):
                try:
                    member_type.ensure(member)
                except SchemaError as error:
                    raise SchemaError(f'{error}, for member \'{key}\'') from error

    def __check_type(self, value: Value_T) -> None:
        """Ensure the passed `value` is at least of type `dict`."""
        if not isinstance(value, dict):
            raise SchemaError(f'Expected {self}, found {value.__class__.__name__}({value})')

    def __repr__(self) -> str:
        if self.member_type is None:
            return 'DictSchema.any()' if self.size is None else f'DictSchema.any(size={self.size})'
        if self.size is None:
            if isinstance(self.member_type, (ListSchema, DictSchema, dict)):
                return f'DictSchema.of({repr(self.member_type)})'
            else:
                return f'DictSchema.of({self.member_type.__name__})'
        else:
            if isinstance(self.member_type, (ListSchema, DictSchema, dict)):
                return f'DictSchema.of({repr(self.member_type)}, size={self.size})'
            else:
                return f'DictSchema.of({self.member_type.__name__}, size={self.size})'
