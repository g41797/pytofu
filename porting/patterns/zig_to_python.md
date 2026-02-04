# Porting Zig Idioms to Python: A Pattern Guide

This document outlines common patterns and best practices for translating core Zig idioms and concepts into their Python equivalents, specifically for the `pytofu` project.

**Target Python Version:** 3.14+

## 1. Tagged Unions
- **Zig Concept**: `union(enum) { Foo: FooType, Bar: BarType }`
- **Python Idiom**: Use `dataclasses` with `match`/`case` structural pattern matching (PEP 634).

```python
from dataclasses import dataclass

@dataclass
class Connected:
    address: str

@dataclass
class Disconnected:
    reason: str

@dataclass
class Error:
    code: int

type ConnectionState = Connected | Disconnected | Error

def handle_state(state: ConnectionState) -> str:
    match state:
        case Connected(address=addr):
            return f"Connected to {addr}"
        case Disconnected(reason=reason):
            return f"Disconnected: {reason}"
        case Error(code=code):
            return f"Error code: {code}"
```

## 2. Errors and Error Handling (Overview)
- **Zig Concept**: Error sets (`error{Foo, Bar}`) and explicit propagation via `try`/`catch`.
- **Python Idiom**: pytofu uses a **hybrid approach**:
  - **Internal code**: Returns `Result[T, E]` (errors as values) - see **Section 11**
  - **Public API**: Raises exceptions at boundaries - see **Section 12**

This matches Zig's explicit error handling internally while providing a Pythonic interface externally.

## 3. Interfaces (Protocols)
- **Zig Concept**: Structs with function pointers or implicit interfaces.
- **Python Idiom**: Use `typing.Protocol` (PEP 544) for structural ("duck") typing.

```python
from typing import Protocol

class Sendable(Protocol):
    """Any object with a send() method - no inheritance required."""
    def send(self, data: bytes) -> int: ...

class Closeable(Protocol):
    """Any object with a close() method."""
    def close(self) -> None: ...

# Classes don't need to inherit - just implement the methods
class Socket:
    def send(self, data: bytes) -> int:
        return len(data)

    def close(self) -> None:
        pass

def send_message(channel: Sendable, data: bytes) -> int:
    return channel.send(data)  # Socket works here without inheritance
```

**Why Protocol over ABC?** Protocols provide "static duck typing" - a closer match to Zig's implicit interfaces than ABC's explicit inheritance.

## 4. Structs
- **Zig Concept**: `struct` for aggregate data types.
- **Python Idiom**: `dataclasses.dataclass` with `__slots__` for efficiency. Use the `struct` module for binary packing.

## 5. Dynamic Byte Buffers (Appendable)
- **Zig Concept**: `Appendable` custom growable buffer.
- **Python Idiom**: `bytearray` wrapped in a custom class to provide Zig-like methods (`append`, `shrink`, `copy`).

## 6. Thread-Safe Blocking Queues (MailBox)
- **Zig Concept**: `MailBox` with interrupt and timeout.
- **Python Idiom**: Custom implementation wrapping `collections.deque` with `threading.Lock` and `threading.Condition`.

**Why not `queue.Queue`?** Python's standard `queue.Queue` provides thread-safe blocking with timeouts, but lacks Zig's critical `interrupt()` capability - the ability to wake blocked receivers immediately for shutdown signals. This requires a custom implementation with explicit condition variable signaling.

## 7. Temporary Files (temp.zig)
- **Zig Concept**: Manual `TempDir` and `TempFile` management.
- **Python Idiom**: Use the built-in `tempfile` module with context managers (`with` statements).

## 8. Ownership Transfer and Use-After-Release Prevention (`*?*` Idiom)

### Zig Concept
The `*?*T` (pointer to optional pointer) idiom is a critical safety pattern in tofu for:

1. **Preventing reuse of released objects**: After `put(&msg)`, `msg` becomes `null`
2. **Enforcing ownership transfer**: When a message moves to another thread, the source reference is invalidated
3. **Fail-fast on misuse**: Any attempt to use a transferred/released message without checking causes immediate failure

```zig
// Zig usage pattern
var msg: ?*Message = try ampe.get(.always);
defer ampe.put(&msg);  // After this, msg == null

// Or explicit transfer
ampe.post(&msg);  // On success, msg is set to null - ownership transferred
```

**Key Zig functions using this pattern:**
- `ampe.put(msg: *?*Message)` - returns to pool, sets to null
- `chnls.post(msg: *?*Message)` - posts message, sets to null on success
- `sendToCtx(msg: *?*Message)` - sends to context, sets to null
- `Message.DestroySendMsg(msg: *?*Message)` - destroys if send failed, sets to null

### Python Challenge
Python lacks pointers, so we cannot directly mutate a caller's variable. We need alternative mechanisms to achieve the same safety guarantees:

1. Prevent accidental reuse of released/transferred messages
2. Make ownership transfer explicit and enforceable
3. Fail fast on misuse (not silently corrupt state)

### Python Idiom: MessageHolder (Invalidatable Wrapper)

Use a lightweight wrapper class that holds the message reference and can be explicitly invalidated:

```python
class Holder[T]:
    """
    Wrapper that enforces single-use ownership semantics.
    Mimics Zig's *?*T pattern for preventing use-after-release.
    """
    __slots__ = ('_value',)

    def __init__(self, value: T | None = None):
        self._value: T | None = value

    @property
    def value(self) -> T | None:
        """Read current value (may be None if taken/released)."""
        return self._value

    def is_empty(self) -> bool:
        """Check if holder has been invalidated."""
        return self._value is None

    def take(self) -> T | None:
        """
        Extract the value and invalidate the holder.
        Equivalent to Zig's: val = holder.*; holder.* = null; return val;
        """
        val = self._value
        self._value = None
        return val

    def set(self, value: T | None) -> None:
        """Set a new value (typically used after get from pool)."""
        self._value = value

    def clear(self) -> None:
        """Invalidate without returning value."""
        self._value = None
```

### Usage Patterns

**Pool return (equivalent to `ampe.put(&msg)`):**
```python
class Ampe:
    def put(self, holder: Holder[Message]) -> None:
        """Return message to pool. Invalidates the holder."""
        msg = holder.take()  # Extract and invalidate
        if msg is not None:
            self._pool.put(msg)

# Usage
msg_holder = Holder(ampe.get(AllocationStrategy.ALWAYS))
try:
    # use msg_holder.value
    pass
finally:
    ampe.put(msg_holder)  # After this, msg_holder.value is None
```

**Post with ownership transfer (equivalent to `chnls.post(&msg)`):**
```python
class ChannelGroup:
    def post(self, holder: Holder[Message]) -> BinaryHeader:
        """
        Post message to channel. On success, invalidates holder.
        On failure, holder retains message for cleanup.
        """
        msg = holder.value
        if msg is None:
            raise AmpeError.NULL_MESSAGE

        header = msg.binary_header
        # ... send logic ...

        # Success - take ownership (invalidate source)
        holder.clear()
        return header
```

**Defer-style cleanup using context manager:**
```python
from contextlib import contextmanager

@contextmanager
def borrowed_message(ampe: Ampe, strategy: AllocationStrategy):
    """
    Context manager ensuring message is returned to pool.
    Equivalent to Zig's: var msg = try ampe.get(...); defer ampe.put(&msg);
    """
    holder = Holder(ampe.get(strategy))
    try:
        yield holder
    finally:
        ampe.put(holder)

# Usage
with borrowed_message(ampe, AllocationStrategy.ALWAYS) as holder:
    msg = holder.value
    if msg:
        msg.set_payload(data)
        chnls.post(holder)  # Takes ownership, holder now empty
    # If we exit without posting, message returns to pool
```

### Alternative: Direct Invalidation Protocol

For simpler cases, messages themselves can implement invalidation:

```python
class Message:
    _RELEASED = object()  # Sentinel for released state

    def __init__(self):
        self._owner_token = object()

    def release(self) -> 'Message':
        """Mark as released and return self for chaining."""
        if self._owner_token is Message._RELEASED:
            raise RuntimeError("Message already released")
        self._owner_token = Message._RELEASED
        return self

    def _check_valid(self) -> None:
        if self._owner_token is Message._RELEASED:
            raise RuntimeError("Attempt to use released message")

    def set_payload(self, data: bytes) -> None:
        self._check_valid()
        # ... implementation
```

### Design Rationale

| Zig Pattern | Python Equivalent | Benefit |
|-------------|-------------------|---------|
| `*?*Message` parameter | `Holder[Message]` parameter | Explicit ownership semantics |
| `msg.* = null` after operation | `holder.take()` / `holder.clear()` | Invalidates source reference |
| Null check at start | `holder.is_empty()` / `holder.value is None` | Early failure detection |
| Compiler enforces null check | Runtime check + type hints | IDE support, fail-fast |

### Thread Safety Note

The `Holder` class itself is **not thread-safe** by design - it mirrors Zig's pattern where the `*?*` reference belongs to a single thread. For cross-thread message passing:

1. The sending thread calls `holder.take()` and passes the message
2. The receiving thread creates its own `Holder` for the received message
3. The original holder is now empty - any misuse fails immediately

This pattern ensures that at any point in time, exactly one thread "owns" each message reference.

## 9. Deferred Cleanup (`defer`)

### Zig Concept

Zig's `defer` executes a statement when the current scope exits, **regardless of how** (normal return, early return, or error). Multiple `defer` statements execute in **reverse order** (LIFO). This provides deterministic cleanup without explicit cleanup code at every exit point.

```zig
// Zig defer pattern
pub fn processData(allocator: Allocator) !void {
    var list = try allocator.alloc(u8, 1024);
    defer allocator.free(list);  // Always runs when function exits

    mutex.lock();
    defer mutex.unlock();  // Always unlocks, even on error

    // ... complex logic with multiple return points ...
    if (condition) return error.SomeError;  // defer still runs
    // ... more logic ...
}  // defers execute here: unlock first, then free
```

**Common tofu `defer` patterns:**

| Pattern | Example | Purpose |
|---------|---------|---------|
| Resource cleanup | `defer socket.deinit()` | Close/free resources |
| Mutex unlock | `defer mutex.unlock()` | Thread-safe critical sections |
| Pool return | `defer ampe.put(&msg)` | Return borrowed messages |
| State notification | `defer pool.inform()` | Signal completion |
| Logging | `defer log.debug("exit")` | Trace function boundaries |
| Thread joining | `defer thread.join()` | Wait for thread completion |

### Python Challenge

Python lacks `defer`. Standard approaches have limitations:
- `try/finally` requires nesting for multiple resources
- Context managers (`with`) work well but can lead to deep nesting
- Forgetting cleanup at early returns causes resource leaks

### Python Idiom 1: Context Managers (`with` statement)

The most Pythonic equivalent for single-resource cleanup:

```python
# Equivalent to: defer file.close()
with open("file.txt") as f:
    process(f)
# File automatically closed

# Equivalent to: defer mutex.unlock()
with mutex:
    # Critical section
    pass
# Lock automatically released
```

**For custom resources, implement the context manager protocol:**

```python
class Socket:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False  # Don't suppress exceptions

# Usage
with Socket() as sock:
    sock.send(data)
# Socket closed regardless of how we exit
```

### Python Idiom 2: `contextlib.ExitStack` for Multiple Resources

When you need multiple `defer`-style cleanups (Zig's LIFO behavior):

```python
from contextlib import ExitStack

def process_data():
    with ExitStack() as stack:
        # Equivalent to Zig's multiple defers (LIFO order)
        data = allocate_buffer()
        stack.callback(free_buffer, data)  # Runs last (registered first)

        mutex.lock()
        stack.callback(mutex.unlock)  # Runs second

        conn = open_connection()
        stack.push(conn)  # Uses conn's __exit__ - runs first

        # Complex logic with multiple returns
        if condition:
            return early_result  # All callbacks still run!

        return final_result
    # ExitStack.__exit__ runs all callbacks in reverse order
```

**Important distinction:**
- `stack.push(obj)` - for objects implementing context manager protocol (`__enter__`/`__exit__`)
- `stack.callback(func, *args)` - for raw cleanup functions without context manager support

### Python Idiom 3: `try/finally` for Simple Cases

For straightforward single-resource cleanup without context manager support:

```python
def process_with_lock():
    mutex.lock()
    try:
        # Critical section
        result = do_work()
        return result
    finally:
        mutex.unlock()  # Always runs
```

### Python Idiom 4: Decorator for Repetitive Patterns

For patterns that repeat across many functions:

```python
from functools import wraps

def with_pool_message(func):
    """Decorator ensuring message is returned to pool."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        holder = Holder(self.ampe.get(AllocationStrategy.ALWAYS))
        try:
            return func(self, holder, *args, **kwargs)
        finally:
            self.ampe.put(holder)
    return wrapper

class Handler:
    @with_pool_message
    def process(self, msg_holder, data):
        msg = msg_holder.value
        msg.set_payload(data)
        self.channel.post(msg_holder)  # Takes ownership
```

### Python Idiom 5: `atexit` for Process-Level Cleanup

For cleanup that must happen when the process exits (not scope-level):

```python
import atexit

def init_engine():
    engine = create_engine()
    atexit.register(engine.shutdown)  # Runs at process exit
    return engine
```

### Mapping Zig `defer` to Python

| Zig Pattern | Python Equivalent | When to Use |
|-------------|-------------------|-------------|
| `defer x.deinit()` | `with x:` | Object has `__enter__`/`__exit__` |
| `defer allocator.free(x)` | `stack.callback(free, x)` | Manual allocation |
| `defer mutex.unlock()` | `with mutex:` | Lock objects |
| Multiple `defer` | `ExitStack` | Need LIFO cleanup order |
| `defer log.debug("exit")` | `try/finally` with log | Simple tracing |

### Complete Example: Zig to Python Translation

**Zig:**
```zig
pub fn connectAndSend(pool: *Pool, addr: Address) !void {
    var msg: ?*Message = try pool.get(.always);
    defer pool.put(&msg);

    var socket = try Socket.connect(addr);
    defer socket.close();

    mutex.lock();
    defer mutex.unlock();

    try socket.send(msg.?.body);
}
```

**Python:**
```python
def connect_and_send(pool: Pool, addr: Address) -> None:
    with ExitStack() as stack:
        holder = Holder(pool.get(AllocationStrategy.ALWAYS))
        stack.callback(pool.put, holder)

        socket = Socket.connect(addr)
        stack.push(socket)  # Uses socket's __exit__

        with mutex:
            socket.send(holder.value.body)
```

## 10. Error-Only Cleanup (`errdefer`)

### Zig Concept

Zig's `errdefer` executes **only when the scope exits due to an error**. It does NOT run on normal return. This is critical for:
1. Rolling back partial state changes on failure
2. Cleaning up partially-constructed objects
3. Diagnostic logging only on error paths

```zig
// Zig errdefer pattern - factory function
pub fn create(allocator: Allocator) !*Engine {
    const engine = try allocator.create(Engine);
    errdefer allocator.destroy(engine);  // Only if later steps fail

    engine.pool = try Pool.init(allocator);
    errdefer engine.pool.deinit();  // Only if later steps fail

    engine.notifier = try Notifier.init(allocator);
    errdefer engine.notifier.deinit();  // Only if thread creation fails

    try engine.createThread();  // If this fails, all errdefers run

    return engine;  // Success! No errdefers run
}
```

**Common tofu `errdefer` patterns:**

| Pattern | Example | Purpose |
|---------|---------|---------|
| Partial construction | `errdefer allocator.destroy(obj)` | Cleanup half-built objects |
| State rollback | `errdefer removeChannel(ch)` | Undo state on failure |
| Error diagnostics | `errdefer msg.dumpMeta("error")` | Debug info on failure |
| Resource release | `errdefer socket.close()` | Close resources if init fails |

### Python Challenge

Python has no direct `errdefer` equivalent. The key semantic difference:
- `defer`/`finally` → runs ALWAYS
- `errdefer` → runs ONLY on error

This matters for factory functions where:
- On **success**: caller takes ownership, no cleanup needed
- On **error**: must clean up partially-constructed resources

### Python Idiom 1: Try/Except with Re-raise

The most direct translation, but verbose:

```python
def create_engine(allocator: Allocator) -> Engine:
    engine = allocator.create(Engine)
    try:
        engine.pool = Pool.init(allocator)
        try:
            engine.notifier = Notifier.init(allocator)
            try:
                engine.create_thread()
                return engine  # Success - no cleanup
            except Exception:
                engine.notifier.deinit()
                raise
        except Exception:
            engine.pool.deinit()
            raise
    except Exception:
        allocator.destroy(engine)
        raise
```

**Problem:** Deep nesting, hard to read, error-prone.

### Python Idiom 2: ErrDefer Helper Class

A more elegant solution using a custom cleanup manager:

```python
from typing import Callable

class ErrDefer:
    """
    Mimics Zig's errdefer - cleanup only runs on exception.
    On successful exit (no exception), cleanup is skipped.
    """
    __slots__ = ('_cleanups',)

    def __init__(self):
        self._cleanups: list[tuple[Callable, tuple, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:  # Error occurred
            # Run cleanups in reverse order (LIFO)
            for func, args, kwargs in reversed(self._cleanups):
                try:
                    func(*args, **kwargs)
                except Exception:
                    # Intentionally suppressed: cleanup failures must not
                    # mask the original exception that triggered errdefer.
                    # This matches Zig's behavior where errdefer cleanup
                    # errors don't replace the propagating error.
                    pass
        return False  # Don't suppress the original exception

    def register(self, func: Callable, *args, **kwargs) -> None:
        """Register cleanup to run only on error."""
        self._cleanups.append((func, args, kwargs))

    def success(self) -> None:
        """Mark as successful - clears all registered cleanups."""
        self._cleanups.clear()
```

**Usage - Clean factory pattern:**

```python
def create_engine(allocator: Allocator) -> Engine:
    with ErrDefer() as cleanup:
        engine = allocator.create(Engine)
        cleanup.register(allocator.destroy, engine)

        engine.pool = Pool.init(allocator)
        cleanup.register(engine.pool.deinit)

        engine.notifier = Notifier.init(allocator)
        cleanup.register(engine.notifier.deinit)

        engine.create_thread()  # If this raises, all cleanups run

        cleanup.success()  # Clear cleanups - caller owns engine now
        return engine
```

### Python Idiom 3: Builder Pattern with Rollback

For complex multi-step construction:

```python
class EngineBuilder:
    """Builder that tracks partial construction for rollback."""

    def __init__(self, allocator: Allocator):
        self._allocator = allocator
        self._engine: Optional[Engine] = None
        self._pool_initialized = False
        self._notifier_initialized = False

    def _rollback(self) -> None:
        """Undo all completed steps in reverse order."""
        if self._notifier_initialized:
            self._engine.notifier.deinit()
        if self._pool_initialized:
            self._engine.pool.deinit()
        if self._engine is not None:
            self._allocator.destroy(self._engine)

    def build(self) -> Engine:
        try:
            self._engine = self._allocator.create(Engine)

            self._engine.pool = Pool.init(self._allocator)
            self._pool_initialized = True

            self._engine.notifier = Notifier.init(self._allocator)
            self._notifier_initialized = True

            self._engine.create_thread()

            # Success - return without cleanup
            return self._engine
        except Exception:
            self._rollback()
            raise

# Usage
engine = EngineBuilder(allocator).build()
```

### Python Idiom 4: Error-Conditional Cleanup in Finally

Using a success flag with finally:

```python
def create_engine(allocator: Allocator) -> Engine:
    engine = None
    pool_ok = notifier_ok = False
    success = False

    try:
        engine = allocator.create(Engine)

        engine.pool = Pool.init(allocator)
        pool_ok = True

        engine.notifier = Notifier.init(allocator)
        notifier_ok = True

        engine.create_thread()

        success = True
        return engine
    finally:
        if not success:  # errdefer behavior
            if notifier_ok:
                engine.notifier.deinit()
            if pool_ok:
                engine.pool.deinit()
            if engine is not None:
                allocator.destroy(engine)
```

### Python Idiom 5: Diagnostic errdefer (Logging on Error)

For `errdefer` used purely for diagnostics:

```python
import logging
from contextlib import contextmanager

@contextmanager
def log_on_error(message: str, **context):
    """Log diagnostic info only if an exception occurs."""
    try:
        yield
    except Exception as e:
        logging.error(f"{message}: {context}, error={e}")
        raise

# Usage - equivalent to: errdefer msg.bhdr.dumpMeta("illegal message")
def check_and_prepare(msg: Message) -> None:
    with log_on_error("illegal message", header=msg.binary_header):
        if not msg.binary_header.opcode.is_valid():
            raise AmpeError.INVALID_OPCODE
        # ... more validation
```

### Comparing `defer` vs `errdefer` in Python

| Zig | Python Equivalent | Runs When |
|-----|-------------------|-----------|
| `defer cleanup()` | `try/finally` or `with` | Always |
| `errdefer cleanup()` | `ErrDefer` helper | Only on exception |
| `defer` + `errdefer` | Combine both patterns | Different cleanups for each case |

### Complete Example: Multi-Step Initialization

**Zig:**
```zig
pub fn init(allocator: Allocator) !*Notifier {
    const ntfr = try allocator.create(Notifier);
    errdefer allocator.destroy(ntfr);

    var listSkt = try createUdsListener(allocator);
    defer listSkt.deinit();  // Always close listener

    var senderSkt = try createUdsSocket();
    errdefer senderSkt.deinit();  // Only on error

    const receiver_fd = try posix.accept(listSkt.socket);
    errdefer posix.close(receiver_fd);  // Only on error

    ntfr.* = .{
        .sender = senderSkt,
        .receiver = receiver_fd,
    };
    return ntfr;  // Success - errdefers don't run
}
```

**Python:**
```python
def init_notifier(allocator: Allocator) -> Notifier:
    with ErrDefer() as err_cleanup:
        ntfr = allocator.create(Notifier)
        err_cleanup.register(allocator.destroy, ntfr)

        # Listener always closes (defer behavior)
        with create_uds_listener(allocator) as list_skt:
            sender_skt = create_uds_socket()
            err_cleanup.register(sender_skt.deinit)

            receiver_fd = posix_accept(list_skt.socket)
            err_cleanup.register(posix_close, receiver_fd)

            ntfr.sender = sender_skt
            ntfr.receiver = receiver_fd

        err_cleanup.success()  # Clear errdefers
        return ntfr
```

### Design Rationale

The `ErrDefer` pattern provides:

1. **Explicit error-only semantics**: Unlike `finally`, cleanup only runs on failure
2. **LIFO ordering**: Matches Zig's reverse-order execution
3. **Composability**: Can combine with regular context managers
4. **Clear ownership transfer**: `success()` signals ownership moved to caller
5. **Exception safety**: Cleanup exceptions don't mask the original error

## 11. Error Union Types (Errors as Values)

### Zig Concept

Zig treats **errors as values**, not exceptions. Functions return error union types (`E!T`) which represent either an error OR a successful value. This is fundamentally different from exception-based languages.

```zig
// Zig error union type: AmpeError!*Message
// Can be: AmpeError.AllocationFailed OR *Message (success)

pub fn create(allocator: Allocator) AmpeError!*Message {
    var msg: *Message = allocator.create(Message) catch {
        return AmpeError.AllocationFailed;  // Return error VALUE
    };
    // ... more initialization ...
    return msg;  // Return success VALUE
}
```

**Key Zig error handling mechanisms:**

| Mechanism | Syntax | Purpose |
|-----------|--------|---------|
| Error union | `E!T` or `!T` | Type that holds error OR value |
| `try` | `try expr` | Propagate error up (short for `catch \|err\| return err`) |
| `catch` | `expr catch \|err\| ...` | Handle error locally |
| `catch` (default) | `expr catch default_value` | Provide fallback value |
| `catch unreachable` | `expr catch unreachable` | Assert cannot fail |

**tofu error patterns:**

```zig
// Error propagation with try
pub fn format(self: *const TCPClientAddress, msg: *Message) AmpeError!void {
    try self.toHeaders(&msg.*.thdrs);  // Propagate any error
}

// Error conversion with catch
var msg: *Message = allocator.create(Message) catch {
    return AmpeError.AllocationFailed;  // Convert to domain error
};

// Error handling with payload capture
const msg = rtr.pool.get(strategy) catch |err| {
    switch (err) {
        AmpeError.PoolEmpty => return null,  // Handle specific error
        else => return err,                   // Propagate others
    }
};
```

### Python Challenge

Python's native error handling is exception-based. To match Zig's "errors as values" pattern while maintaining Pythonic interfaces, we need:

1. **Result type** for internal code (errors as values)
2. **Exception conversion** at API boundaries
3. **Clear separation** between internal and public interfaces

### Python Idiom: Result Type Pattern

A `Result[T, E]` type that can hold either a success value or an error.

**Uses Python 3.12+ type syntax (PEP 695):**

```python
from dataclasses import dataclass
from enum import IntEnum, auto

@dataclass(frozen=True, slots=True)
class Ok[T]:
    """Success variant of Result."""
    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value


@dataclass(frozen=True, slots=True)
class Err[E]:
    """Error variant of Result."""
    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap[T](self) -> T:
        raise ResultUnwrapError(f"Called unwrap on Err: {self.error}")

    def unwrap_or[T](self, default: T) -> T:
        return default


# Result type alias (PEP 695 syntax)
type Result[T, E] = Ok[T] | Err[E]


class ResultUnwrapError(Exception):
    """Raised when unwrap() is called on an Err."""
    pass
```

### Error Enum (Matching Zig's Error Set)

```python
class AmpeError(IntEnum):
    """
    Error codes matching Zig's AmpeError.
    Used as error VALUES in internal code.
    """
    NOT_IMPLEMENTED_YET = auto()
    WRONG_ADDRESS = auto()
    NOT_ALLOWED = auto()
    NULL_MESSAGE = auto()
    INVALID_MESSAGE = auto()
    INVALID_OP_CODE = auto()
    INVALID_HEADERS_LEN = auto()
    INVALID_BODY_LEN = auto()
    INVALID_CHANNEL_NUMBER = auto()
    INVALID_MESSAGE_CHANNEL_GROUP = auto()
    INVALID_MESSAGE_ID = auto()
    INVALID_ADDRESS = auto()
    UDS_PATH_NOT_FOUND = auto()
    NOTIFICATION_DISABLED = auto()
    NOTIFICATION_FAILED = auto()
    PEER_DISCONNECTED = auto()
    COMMUNICATION_FAILED = auto()
    POOL_EMPTY = auto()
    ALLOCATION_FAILED = auto()
    RECEIVER_UPDATE = auto()
    CHANNEL_CLOSED = auto()
    SHUTDOWN_STARTED = auto()
    CONNECT_FAILED = auto()
    LISTEN_FAILED = auto()
    ACCEPT_FAILED = auto()
    SEND_FAILED = auto()
    RECV_FAILED = auto()
    SETSOCKOPT_FAILED = auto()
    PROCESSING_FAILED = auto()
    UNKNOWN_ERROR = auto()
```

### Internal Functions: Return Result

Internal functions return `Result[T, AmpeError]` instead of raising exceptions:

```python
def _create_message(allocator: Allocator) -> Result[Message, AmpeError]:
    """
    Internal: Create a new message.
    Returns Result instead of raising exception.
    Equivalent to Zig's: pub fn create(allocator: Allocator) AmpeError!*Message
    """
    try:
        msg = allocator.create(Message)
    except MemoryError:
        return Err(AmpeError.ALLOCATION_FAILED)

    # Initialize body
    match msg.body.init(allocator, BODY_LEN):
        case Err():
            msg.destroy()
            return Err(AmpeError.ALLOCATION_FAILED)
        case Ok():
            pass

    # Initialize text headers
    match msg.thdrs.init(allocator, THDRS_LEN):
        case Err():
            msg.destroy()
            return Err(AmpeError.ALLOCATION_FAILED)
        case Ok():
            pass

    return Ok(msg)


def _pool_get(pool: Pool, strategy: AllocationStrategy) -> Result[Message | None, AmpeError]:
    """
    Internal: Get message from pool.
    Equivalent to Zig's: fn _get(rtr: *Reactor, strategy: AllocationStrategy) AmpeError!?*Message
    """
    if pool.closed:
        return Err(AmpeError.NOT_ALLOWED)

    msg = pool._try_get()
    if msg is not None:
        return Ok(msg)

    # Pool empty
    if strategy == AllocationStrategy.POOL_ONLY:
        return Ok(None)  # Not an error - valid "no message" response

    # Strategy is ALWAYS - create new
    return _create_message(pool.allocator)
```

### Note on Allocator

The `allocator` parameter in examples mirrors Zig's explicit allocator pattern. In pytofu, this represents **object pool management** and factory functions, not low-level memory allocation (which Python handles automatically). The Allocator abstraction enables:
- Message pooling for performance
- Tracking of allocated resources
- Consistent cleanup patterns

### Error Propagation: `try_result` Helper

Mimics Zig's `try` keyword for propagating errors:

```python
from functools import wraps
from typing import Callable

def try_result[T, E](result: Result[T, E]) -> T:
    """
    Equivalent to Zig's `try` keyword.
    If result is Ok, returns the value.
    If result is Err, raises _PropagateError to be caught by decorator.

    Usage:
        value = try_result(some_function())  # Propagates error if Err
    """
    match result:
        case Ok(value):
            return value
        case Err(error):
            raise _PropagateError(error)


class _PropagateError[E](Exception):
    """Internal exception for error propagation within Result-based code."""
    __slots__ = ('error',)

    def __init__(self, error: E):
        self.error = error
        super().__init__()


def with_error_propagation[T, E](func: Callable[..., Result[T, E]]) -> Callable[..., Result[T, E]]:
    """
    Decorator that catches _PropagateError and converts to Err.
    Enables try_result() to work like Zig's try.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Result[T, E]:
        try:
            return func(*args, **kwargs)
        except _PropagateError as e:
            return Err(e.error)
    return wrapper
```

> **⚠️ Performance Warning:** The `try_result` pattern uses internal exception raising/catching to simulate Zig's `try`. While architecturally clean, Python exception handling has overhead. In high-throughput message processing paths, consider using explicit `match` statements on Result instead of `try_result` for hot code paths.

**Usage - matching Zig's try pattern:**

```python
@with_error_propagation
def _format_address(address: TCPClientAddress, msg: Message) -> Result[None, AmpeError]:
    """
    Equivalent to Zig's:
    pub fn format(self: *const TCPClientAddress, msg: *Message) AmpeError!void {
        try self.toHeaders(&msg.*.thdrs);
    }
    """
    _prepare_for_client(msg)
    try_result(address._to_headers(msg.thdrs))  # Propagates error
    return Ok(None)
```

### Error Handling: `catch_result` Helpers

Mimics Zig's `catch` patterns:

```python
from typing import Callable

def catch_or[T, E](result: Result[T, E], default: T) -> T:
    """
    Equivalent to Zig's `expr catch default_value`.
    Returns value if Ok, default if Err.
    """
    match result:
        case Ok(value):
            return value
        case Err():
            return default


def catch_with[T, E](
    result: Result[T, E],
    handler: Callable[[E], Result[T, E]]
) -> Result[T, E]:
    """
    Equivalent to Zig's `expr catch |err| { ... }`.
    If Err, calls handler with the error.
    """
    match result:
        case Ok():
            return result
        case Err(error):
            return handler(error)


# Usage - matching Zig's catch |err| switch pattern:
def _get_from_pool(pool: Pool, strategy: AllocationStrategy) -> Result[Message | None, AmpeError]:
    """
    Equivalent to Zig's:
    const msg = rtr.pool.get(strategy) catch |err| {
        switch (err) {
            AmpeError.PoolEmpty => return null,
            else => return err,
        }
    };
    """
    result = pool._get(strategy)

    match result:
        case Err(AmpeError.POOL_EMPTY):
            return Ok(None)  # Handle specific error
        case Err():
            return result  # Propagate other errors
        case Ok():
            return result
```

## 12. API Boundary Pattern (Exceptions at Interface)

### Design Philosophy

The user's requirement creates a **two-layer architecture**:

1. **Internal layer**: Uses `Result[T, E]` - errors as values, explicit handling
2. **Public API layer**: Converts to exceptions - familiar Python interface

This provides:
- **Internal code**: Explicit error flow, composable, no hidden control flow
- **Public API**: Pythonic interface, familiar to Python developers
- **Clear boundary**: Errors converted at well-defined points

```
┌─────────────────────────────────────────────────────────┐
│  External Code (User's Application)                     │
│  - Uses exceptions (try/except)                         │
│  - Familiar Python patterns                             │
└───────────────────────┬─────────────────────────────────┘
                        │ raises AmpeException
┌───────────────────────▼─────────────────────────────────┐
│  Public API Layer (Interface Methods)                   │
│  - Ampe.get(), ChannelGroup.post(), etc.               │
│  - Converts Result → Exception                          │
│  - Decorated with @public_api                           │
└───────────────────────┬─────────────────────────────────┘
                        │ returns Result[T, AmpeError]
┌───────────────────────▼─────────────────────────────────┐
│  Internal Layer                                         │
│  - _create_message(), _pool_get(), etc.                │
│  - Returns Result[T, AmpeError]                         │
│  - Uses try_result() for propagation                    │
└─────────────────────────────────────────────────────────┘
```

### Exception Class Hierarchy

```python
class AmpeException(Exception):
    """
    Base exception for all Ampe errors.
    Raised at API boundaries when internal Result is Err.
    """
    __slots__ = ('error_code', 'message')

    def __init__(self, error: AmpeError, message: str = ""):
        self.error_code = error
        self.message = message or error.name
        super().__init__(f"{error.name}: {message}" if message else error.name)

    @classmethod
    def from_error(cls, error: AmpeError) -> 'AmpeException':
        """Factory method to create appropriate exception subclass."""
        exception_map = {
            AmpeError.ALLOCATION_FAILED: AllocationFailedException,
            AmpeError.POOL_EMPTY: PoolEmptyException,
            AmpeError.SHUTDOWN_STARTED: ShutdownException,
            AmpeError.PEER_DISCONNECTED: PeerDisconnectedException,
            AmpeError.CONNECT_FAILED: ConnectionFailedException,
            AmpeError.INVALID_OP_CODE: InvalidMessageException,
            AmpeError.NULL_MESSAGE: InvalidMessageException,
            # ... map other errors
        }
        exc_class = exception_map.get(error, AmpeException)
        return exc_class(error)


# Specific exception types for common errors
class AllocationFailedException(AmpeException):
    """Memory allocation failed."""
    pass

class PoolEmptyException(AmpeException):
    """Message pool is empty (when using poolOnly strategy)."""
    pass

class ShutdownException(AmpeException):
    """Engine is shutting down."""
    pass

class PeerDisconnectedException(AmpeException):
    """Remote peer disconnected."""
    pass

class ConnectionFailedException(AmpeException):
    """Failed to establish connection."""
    pass

class InvalidMessageException(AmpeException):
    """Message is invalid or null."""
    pass
```

### Boundary Decorator: `@public_api`

Automatically converts `Result` returns to exceptions:

```python
from functools import wraps
from typing import Callable

def public_api[R](func: Callable[..., Result[R, AmpeError]]) -> Callable[..., R]:
    """
    Decorator for public API methods.
    Converts internal Result[T, AmpeError] to:
    - Return T on success (Ok)
    - Raise AmpeException on error (Err)

    This is the BOUNDARY between internal (Result-based) and
    external (exception-based) code.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> R:
        match func(*args, **kwargs):
            case Ok(value):
                return value
            case Err(error):
                raise AmpeException.from_error(error)

    return wrapper
```

### Complete API Implementation Example

**Internal implementation (errors as values):**

```python
class _ReactorInternal:
    """Internal implementation - uses Result pattern."""

    def _get(self, strategy: AllocationStrategy) -> Result[Message | None, AmpeError]:
        """Internal: get message from pool."""
        if self._shutdown_started:
            return Err(AmpeError.SHUTDOWN_STARTED)

        return _pool_get(self._pool, strategy)

    def _put(self, holder: Holder[Message]) -> Result[None, AmpeError]:
        """Internal: return message to pool."""
        msg = holder.take()
        if msg is None:
            return Ok(None)

        msg.reset()
        self._pool.put(msg)
        return Ok(None)

    @with_error_propagation
    def _create_channel_group(self) -> Result[MchnGroup, AmpeError]:
        """Internal: create channel group."""
        if self._shutdown_started:
            return Err(AmpeError.SHUTDOWN_STARTED)

        grp = try_result(_allocate_mchn_group(self._allocator))
        try_result(grp.init(self))
        return Ok(grp)
```

**Public API (exception-based):**

```python
class Ampe:
    """
    Public API - the engine interface.
    All methods raise exceptions on error.
    """

    def __init__(self, internal: _ReactorInternal):
        self._internal = internal

    @public_api
    def get(self, strategy: AllocationStrategy = AllocationStrategy.ALWAYS) -> Message | None:
        """
        Get a message from the pool.

        Args:
            strategy: POOL_ONLY returns None if empty, ALWAYS creates new

        Returns:
            Message or None (if pool empty with POOL_ONLY strategy)

        Raises:
            ShutdownException: If engine is shutting down
            AllocationFailedException: If memory allocation fails
        """
        return self._internal._get(strategy)

    def put(self, holder: Holder[Message]) -> None:
        """
        Return a message to the pool.
        Invalidates the holder.

        This method never fails - if pool is closed, message is destroyed.
        """
        # put() is void and cannot fail in Zig, so no @public_api needed
        _ = self._internal._put(holder)
        # Silently ignore errors (matches Zig behavior)

    @public_api
    def create(self) -> 'ChannelGroup':
        """
        Create a new channel group.

        Returns:
            ChannelGroup for communication

        Raises:
            ShutdownException: If engine is shutting down
            AllocationFailedException: If memory allocation fails
        """
        match self._internal._create_channel_group():
            case Err() as err:
                return err  # Will be converted to exception by @public_api
            case Ok(mchn):
                return Ok(ChannelGroup(mchn))


class ChannelGroup:
    """Public API for channel operations."""

    def __init__(self, internal: MchnGroup):
        self._internal = internal

    @public_api
    def post(self, holder: Holder[Message]) -> BinaryHeader:
        """
        Post a message for async processing.

        On success, holder is invalidated (ownership transferred).

        Args:
            holder: Message holder (will be invalidated on success)

        Returns:
            BinaryHeader for tracking

        Raises:
            InvalidMessageException: If message is null
            ShutdownException: If engine is shutting down
        """
        return self._internal._post(holder)

    @public_api
    def wait_receive(self, timeout_ns: int) -> Message | None:
        """
        Wait for next message from queue.

        Args:
            timeout_ns: Timeout in nanoseconds

        Returns:
            Message or None if timeout

        Raises:
            ShutdownException: If engine is shutting down
            ChannelClosedException: If channel was closed
        """
        return self._internal._wait_receive(timeout_ns)
```

### Usage Example: User Code

```python
# User code - uses familiar Python exception handling

def process_messages(engine: Ampe):
    """Example of using the public API."""
    try:
        channels = engine.create()
    except ShutdownException:
        print("Engine is shutting down")
        return
    except AllocationFailedException:
        print("Out of memory")
        return

    try:
        while True:
            # Get message - may raise or return None
            msg = channels.wait_receive(timeout_ns=1_000_000_000)
            if msg is None:
                continue  # Timeout, try again

            # Process the message
            holder = Holder(msg)
            try:
                process(holder.value)
                channels.post(holder)  # Send response
            finally:
                engine.put(holder)  # Return to pool if not posted

    except PeerDisconnectedException:
        print("Peer disconnected")
    except ShutdownException:
        print("Shutdown requested")
    finally:
        try:
            engine.destroy(channels)
        except AmpeException:
            pass  # Ignore errors during cleanup
```

### Summary: Zig to Python Error Pattern Mapping

| Zig Pattern | Internal Python | Public Python |
|-------------|-----------------|---------------|
| `AmpeError!T` return | `Result[T, AmpeError]` | Raises `AmpeException` |
| `try expr` | `try_result(expr)` | N/A (use exceptions) |
| `catch { return Err }` | `if result.is_err(): return Err(...)` | N/A |
| `catch \|err\| switch` | `if isinstance(result, Err): match err` | `except SpecificException:` |
| `return AmpeError.X` | `return Err(AmpeError.X)` | `raise AmpeException.from_error(...)` |
| void function | `Result[None, AmpeError]` | `None` or raises |

### Design Rationale

This hybrid approach provides:

1. **Internal explicitness**: Error flow is visible in types and code
2. **No hidden control flow**: Internal code never surprises with exceptions
3. **Composability**: Results can be chained, transformed, collected
4. **Pythonic public API**: External users get familiar exception patterns
5. **Clear boundaries**: `@public_api` decorator marks conversion points
6. **Testability**: Internal functions can be tested without try/except
7. **Wire compatibility**: Error codes match Zig's `AmpeError` for protocol compatibility

### References

- [Zig Guide - Errors](https://zig.guide/language-basics/errors/)
- [Zig Documentation](https://ziglang.org/documentation/master/)
- [Introduction to Zig - Error Handling](https://pedropark99.github.io/zig-book/Chapters/09-error-handling.html)
