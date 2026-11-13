"""A small stand-in for ``dataclasses`` on the hook path.

Every tool call starts a new Python process, so import time is paid on every
call. ``@dataclasses.dataclass`` compiles generated source with ``exec`` for each
class, and importing ``dataclasses`` loads ``inspect``: about 25 ms per call for
the record classes the hook needs. This module gives the same behavior for what
those classes use, with no runtime code generation:

* ``@dataclass`` and ``@dataclass(frozen=True)``: an ``__init__`` taking fields
  positionally or by keyword, defaults, ``field(default_factory=...)``,
  ``__post_init__``, ``__repr__``, ``__eq__``, ``__match_args__``. Frozen
  classes are hashable and raise ``dataclasses.FrozenInstanceError`` on
  assignment; mutable ones are unhashable.
* ``replace`` and ``asdict`` for these classes.

Anything else (inheritance between records, ``ClassVar``, other ``field``
options, other decorator options) is refused with ``TypeError`` instead of being
half supported. Code off the hook path keeps using ``dataclasses``.
"""

from __future__ import annotations

TYPE_CHECKING = False
if TYPE_CHECKING:  # typing costs about 2 ms to import on every hook call
    from typing import Any

_MISSING: Any = object()
_FIELDS = "__record_fields__"


class _Field:
    __slots__ = ("default", "default_factory")

    def __init__(self, default: Any, default_factory: Any) -> None:
        self.default = default
        self.default_factory = default_factory


def field(*, default: Any = _MISSING, default_factory: Any = _MISSING) -> Any:
    if default is not _MISSING and default_factory is not _MISSING:
        raise ValueError("cannot specify both default and default_factory")
    return _Field(default, default_factory)


def dataclass(cls: Any = None, /, *, frozen: bool = False) -> Any:
    def wrap(target: type) -> type:
        return _process(target, frozen)

    return wrap if cls is None else wrap(cls)


def is_record(obj: object) -> bool:
    kind = obj if isinstance(obj, type) else type(obj)
    return _FIELDS in kind.__dict__


def _annotations(cls: type) -> dict[str, Any]:
    if "__annotations__" in cls.__dict__:
        return dict(cls.__dict__["__annotations__"])
    try:
        return dict(cls.__annotations__)
    except Exception as exc:  # noqa: BLE001
        raise TypeError(f"{cls.__qualname__}: annotations could not be read") from exc


def _process(cls: type, frozen: bool) -> type:
    if any(_FIELDS in base.__dict__ for base in cls.__mro__[1:]):
        raise TypeError(f"{cls.__qualname__}: records cannot inherit from records")
    names: list[str] = []
    defaults: dict[str, Any] = {}
    factories: dict[str, Any] = {}
    for name, annotation in _annotations(cls).items():
        text = annotation if isinstance(annotation, str) else repr(annotation)
        if "ClassVar" in text or "InitVar" in text:
            raise TypeError(f"{cls.__qualname__}.{name}: ClassVar and InitVar are not supported")
        value = cls.__dict__.get(name, _MISSING)
        if isinstance(value, _Field):
            if value.default_factory is not _MISSING:
                factories[name] = value.default_factory
                delattr(cls, name)
            elif value.default is not _MISSING:
                defaults[name] = value.default
                setattr(cls, name, value.default)
            else:
                delattr(cls, name)
                if defaults or factories:
                    raise TypeError(f"non-default argument {name!r} follows default argument")
        elif value is not _MISSING:
            if isinstance(value, (list, dict, set)):
                raise ValueError(f"mutable default {type(value)} for field {name} is not allowed: use default_factory")
            defaults[name] = value
        elif defaults or factories:
            raise TypeError(f"non-default argument {name!r} follows default argument")
        names.append(name)

    fields = tuple(names)
    known = frozenset(fields)
    qualname = cls.__qualname__
    post_init = cls.__dict__.get("__post_init__")
    setter = object.__setattr__

    def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
        if len(args) > len(fields):
            raise TypeError(
                f"{qualname}.__init__() takes {len(fields) + 1} positional arguments but {len(args) + 1} were given"
            )
        values = dict(zip(fields, args))
        for key, value in kwargs.items():
            if key not in known:
                raise TypeError(f"{qualname}.__init__() got an unexpected keyword argument {key!r}")
            if key in values:
                raise TypeError(f"{qualname}.__init__() got multiple values for argument {key!r}")
            values[key] = value
        for name in fields:
            if name in values:
                value = values[name]
            elif name in defaults:
                value = defaults[name]
            elif name in factories:
                value = factories[name]()
            else:
                raise TypeError(f"{qualname}.__init__() missing 1 required argument: {name!r}")
            setter(self, name, value)
        if post_init is not None:
            post_init(self)

    def __repr__(self: Any) -> str:
        inner = ", ".join(f"{name}={getattr(self, name)!r}" for name in fields)
        return f"{type(self).__qualname__}({inner})"

    def __eq__(self: Any, other: object) -> Any:
        if other.__class__ is self.__class__:
            return tuple(getattr(self, name) for name in fields) == tuple(getattr(other, name) for name in fields)
        return NotImplemented

    generated: dict[str, Any] = {"__init__": __init__, "__repr__": __repr__, "__eq__": __eq__}
    explicit_hash = cls.__dict__.get("__hash__") is not None
    if frozen:

        def __hash__(self: Any) -> int:
            return hash(tuple(getattr(self, name) for name in fields))

        def __setattr__(self: Any, name: str, value: Any) -> None:
            from dataclasses import FrozenInstanceError

            raise FrozenInstanceError(f"cannot assign to field {name!r}")

        def __delattr__(self: Any, name: str) -> None:
            from dataclasses import FrozenInstanceError

            raise FrozenInstanceError(f"cannot delete field {name!r}")

        for name in ("__setattr__", "__delattr__"):
            if name in cls.__dict__:
                raise TypeError(f"Cannot overwrite attribute {name} in class {qualname}")
        generated["__setattr__"] = __setattr__
        generated["__delattr__"] = __delattr__
        if not explicit_hash:
            generated["__hash__"] = __hash__
    for name, function in generated.items():
        if name in cls.__dict__ and name not in ("__setattr__", "__delattr__", "__hash__"):
            continue
        function.__qualname__ = f"{qualname}.{name}"
        setattr(cls, name, function)
    if not frozen and not explicit_hash:
        # A mutable record that compares by value cannot be hashed, as with dataclasses.
        cls.__hash__ = None  # type: ignore[assignment]
    cls.__match_args__ = fields  # type: ignore[attr-defined]
    setattr(cls, _FIELDS, fields)
    return cls


def _fields_of(obj: object) -> tuple[str, ...]:
    fields = type(obj).__dict__.get(_FIELDS)
    if fields is None:
        raise TypeError(f"{type(obj).__qualname__} is not a record instance")
    return fields


def replace(obj: Any, /, **changes: Any) -> Any:
    fields = _fields_of(obj)
    for key in changes:
        if key not in fields:
            raise TypeError(f"{type(obj).__qualname__}.__init__() got an unexpected keyword argument {key!r}")
    return type(obj)(**{name: changes[name] if name in changes else getattr(obj, name) for name in fields})


def asdict(obj: Any) -> dict[str, Any]:
    _fields_of(obj)
    return _as_plain(obj)


def _as_plain(value: Any) -> Any:
    fields = type(value).__dict__.get(_FIELDS)
    if fields is not None:
        return {name: _as_plain(getattr(value, name)) for name in fields}
    if isinstance(value, tuple) and hasattr(value, "_fields"):
        return type(value)(*[_as_plain(item) for item in value])
    if isinstance(value, (list, tuple)):
        return type(value)(_as_plain(item) for item in value)
    if isinstance(value, dict):
        return type(value)((_as_plain(key), _as_plain(item)) for key, item in value.items())
    if value is None or isinstance(value, (str, int, float, bool, bytes)):
        return value
    import copy

    return copy.deepcopy(value)


__all__ = ["asdict", "dataclass", "field", "is_record", "replace"]
