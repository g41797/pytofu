# Specification: Project Layout Analysis

The Python project layout is designed to be idiomatic while mirroring the logical structure of the original Zig project.

## 1. Idiomatic Layout
- **`src/` Layout:** Ensures that the package is properly installed and isolated from the source tree during testing.
- **`pyproject.toml`:** Modern metadata and build system configuration.
- **`__init__.py`:** Controls the public API surface area.
- **`_internal/`:** Encapsulates implementation details (e.g., mailboxes, notification logic) that are not part of the public API.

## 2. Logical Partitioning
- **`message.py`:** Contains the primary data containers (`Message`, `BinaryHeader`, `TextHeaders`).
- **`opcode.py` & `status.py`:** Isolated enums to prevent circular dependencies and provide stable constants.
- **`address.py`:** Dedicated logic for network address parsing and formatting.
- **`engine.py` & `reactor.py`:** Separates the high-level application interface from the internal event-loop logic.
