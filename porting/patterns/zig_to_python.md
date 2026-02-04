# Porting Zig Idioms to Python: A Pattern Guide

This document outlines common patterns and best practices for translating core Zig idioms and concepts into their Python equivalents, specifically for the `pytofu` project.

## 1. Tagged Unions
- **Zig Concept**: `union(enum) { Foo: FooType, Bar: BarType }`
- **Python Idiom**: Use `dataclasses` or classes combined with `typing.Union` and `isinstance()` checks.

## 2. Errors and Error Handling
- **Zig Concept**: Error sets (`error{Foo, Bar}`) and explicit propagation.
- **Python Idiom**: Custom exception classes inheriting from `Exception` and `try...except` blocks.

## 3. Interfaces (Duck Typing / ABCs)
- **Zig Concept**: Structs with function pointers or implicit interfaces.
- **Python Idiom**: Duck typing or `abc.ABC` (Abstract Base Classes) for explicit compliance.

## 4. Structs
- **Zig Concept**: `struct` for aggregate data types.
- **Python Idiom**: `dataclasses.dataclass` with `__slots__` for efficiency. Use the `struct` module for binary packing.

## 5. Dynamic Byte Buffers (Appendable)
- **Zig Concept**: `Appendable` custom growable buffer.
- **Python Idiom**: `bytearray` wrapped in a custom class to provide Zig-like methods (`append`, `shrink`, `copy`).

## 6. Thread-Safe Blocking Queues (MailBox)
- **Zig Concept**: `MailBox` with interrupt and timeout.
- **Python Idiom**: A custom class wrapping `collections.deque` and using `threading.Lock` and `threading.Condition` to mimic Zig's `interrupt()` and `close()` behavior.

## 7. Temporary Files (temp.zig)
- **Zig Concept**: Manual `TempDir` and `TempFile` management.
- **Python Idiom**: Use the built-in `tempfile` module with context managers (`with` statements).
