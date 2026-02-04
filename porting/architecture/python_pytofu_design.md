# Python pytofu Design Specification

This document details the design choices for the Python implementation of the tofu messaging system.

## 1. Concurrency Model: The Hybrid Approach

To match the performance and architectural semantics of Zig **tofu**, **pytofu** uses a hybrid model:

### 1.1 The Reactor Thread
- **Event Loop:** Uses `asyncio` for high-performance non-blocking I/O.
- **Responsibility:** Managing sockets, framing messages, and routing them to application queues.
- **Independence:** The `asyncio` loop runs in its own dedicated thread, separate from the main application thread.

### 1.2 Application Threads
- **Synchronous API:** Applications use standard blocking calls like `waitReceive(timeout)`. This is more natural for many Python use cases and matches the original Zig API.
- **Thread Safety:** All public APIs are thread-safe.

### 1.3 Inter-Thread Communication (ITC)
- **App → Reactor:** Messages are submitted to the reactor using `asyncio.run_coroutine_threadsafe()`.
- **Reactor → App:** Messages are delivered to application threads via `queue.Queue` (or a custom `Mailbox` class).

## 2. Key Python Idioms and Patterns

### 2.1 Core Types
- **Opcodes and Statuses:** Implemented as `IntEnum` for performance and clarity.
- **Data Structures:** Use `dataclasses` with `__slots__` for memory efficiency.
- **Binary Packing:** Use the `struct` module for wire-format compatibility.

### 2.2 Memory Management
- **Object Pooling:** A custom `Pool` class will manage a free-list of `Message` objects to reduce GC pressure.
- **Buffers:** `bytearray` will be used for mutable byte buffers (Appendable).

### 2.3 Error Handling
- **Exceptions:** Use custom exception classes (e.g., `AmpeError`) for unexpected or fatal errors.
- **Status Codes:** Protocol-level errors will be handled via status codes in the message header, mirroring the Zig implementation.

## 3. Module Mapping (Zig → Python)

| Zig Source | Python Module | Key Class |
| :--- | :--- | :--- |
| `message.zig` | `tofu.message` | `Message`, `BinaryHeader` |
| `status.zig` | `tofu.status` | `AmpeStatus` |
| `address.zig` | `tofu.address` | `Address` |
| `ampe.zig` | `tofu.engine` | `Ampe` |
| `chnls.zig` | `tofu.channels` | `ChannelGroup` |
| `mailbox.zig` | `tofu._internal.mailbox` | `Mailbox` |
