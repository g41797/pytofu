# Specification: opcode.py

## 1. Objective
Define the `OpCode` enumeration containing all 10 operation codes from the **tofu** protocol.

## 2. Specification
The `opcode.py` file must define an `IntEnum` named `OpCode` with values matching the Zig source (`message.zig`).

```python
from enum import IntEnum

class OpCode(IntEnum):
    """Message operation codes matching Zig tofu."""

    REQUEST = 0
    RESPONSE = 1
    SIGNAL = 2
    HELLO_REQUEST = 3
    HELLO_RESPONSE = 4
    BYE_REQUEST = 5
    BYE_RESPONSE = 6
    BYE_SIGNAL = 7
    WELCOME_REQUEST = 8
    WELCOME_RESPONSE = 9
```
