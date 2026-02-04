# Master Plan: Porting tofu to pytofu

## Project Context
- **Roles:** Zig & Python Architect (AI), Expert in Network Messaging Systems (AI), Lead Implementer (Author).
- **Repository Root:** `/home/g41797/dev/root/github.com/g41797/pytofu`
- **Porting Directory:** `/home/g41797/dev/root/github.com/g41797/pytofu/porting`

## Project Goal
To implement a high-performance, message-driven execution engine in Python (pytofu) that is architecturally consistent and wire-compatible with the Zig tofu messaging system.

## Core Architectural Strategy: The Hybrid Model
- **Reactor Thread:** A dedicated thread running an `asyncio` event loop for non-blocking I/O, message framing, and routing.
- **Application Threads:** Multiple threads using a synchronous, thread-safe API to interact with the engine (e.g., `post()`, `waitReceive()`).
- **Communication:** Inter-thread communication via thread-safe queues and signaling between `asyncio` and `threading`.

## Roadmap

### Phase 1: Core Data Structures (Current)
- [ ] `opcode.py`: Define operation codes (10 values).
- [ ] `status.py`: Define `AmpeStatus` and `AmpeError`.
- [ ] `message.py`: Implement `BinaryHeader`, `TextHeaders`, and the `Message` container.
- [ ] `address.py`: Implement TCP and UDS address parsing/formatting.

### Phase 2: Internal Utilities
- [ ] `appendable.py`: Resizable byte buffer (`bytearray` wrapper).
- [ ] `mailbox.py`: Thread-safe blocking queue with interrupts and timeouts.
- [ ] `notifier.py`: Inter-thread signaling mechanism.

### Phase 3: Engine and Channels
- [ ] `pool.py`: Message pool management.
- [ ] `reactor.py`: The `asyncio` event loop and socket handler.
- [ ] `channels.py`: `ChannelGroup`, `post()`, and `waitReceive()` implementation.

### Phase 4: Verification and Examples
- [ ] Unit tests mirroring Zig `message_tests.zig`, `Pool_tests.zig`, etc.
- [ ] Integration tests mirroring `reactor_tests.zig` (Echo, Reconnect).
- [ ] Examples mirroring Zig recipes.

## Project Layout
```
pytofu/
├── src/tofu/
│   ├── __init__.py         # Public API
│   ├── message.py          # Message, BinaryHeader, TextHeaders
│   ├── status.py           # AmpeStatus, AmpeError
│   ├── address.py          # Address types
│   ├── opcode.py           # OpCode enum
│   ├── engine.py           # Ampe interface
│   ├── pool.py             # Message pool
│   ├── reactor.py          # Reactor implementation
│   ├── channels.py         # ChannelGroup
│   └── _internal/          # Internal utilities (mailbox, notifier, etc.)
├── tests/                  # Mirroring Zig tests
├── examples/               # Mirroring Zig recipes
└── porting/                # Porting documentation (this folder)
```

## Naming Convention
- Project: `pytofu` (all lowercase)
- Source: `tofu` (all lowercase)
- Python modules: Standard Python snake_case.
- Classes: PascalCase.
