# Advice C — Implementation Notes for Zig → Python Porting

This document provides **NON-NORMATIVE** implementation guidance for applying the
canonical rules defined in **Advice D — Canonical Zig → Python Porting Rules**.

It contains practical tips, common pitfalls, and performance considerations
intended to help implementers write correct, efficient, and maintainable code.

If this document conflicts with Advice D, **Advice D ALWAYS WINS**.

This document answers **HOW** to implement the rules.
Advice D defines **WHAT is allowed**.

---

## 1. Tagged Unions  
(See Advice D — Pattern 1)

- **Tip:** Use `@dataclass(frozen=True)` for variants to prevent accidental mutation and better mirror Zig’s immutability guarantees.
- **Tip:** Include an explicit `case _:` branch in `match` statements to fail fast on unexpected variants.
- **Tooling:** Enable mypy or pyright exhaustiveness warnings (e.g. `--warn-unreachable`) to partially simulate Zig’s compile-time checks.
- **Performance:** Structural pattern matching is generally O(1), but profile if used in hot loops with large unions.
- **Pitfall:** Subclassing dataclasses that use `__slots__` can break slot inheritance and introduce subtle bugs.

---

## 2. Errors and Error Handling (Overview)  
(See Advice D — Patterns 10 & 11)

- **Best Practice:** Maintain a strict separation: internal code uses `Result`, public APIs raise exceptions.
- **Tip:** Document all public exceptions using `Raises:` sections in docstrings for predictability.
- **Performance:** Minimize Result↔exception boundary crossings in hot paths to avoid conversion overhead.
- **Tip:** Represent error sets using enums internally and map them to specific exception subclasses at the API boundary.
- **Pitfall:** Never mix exceptions and `Result` values within the same internal module.

---

## 3. Interfaces (Protocols)  
(See Advice D — Pattern 2)

- **Tooling:** Use mypy or pyright to catch Protocol mismatches early and simulate Zig’s implicit interface enforcement.
- **Tip:** Use `@runtime_checkable` Protocols sparingly for runtime validation in critical paths.
- **Best Practice:** Keep Protocols minimal to preserve structural typing and avoid over-constraining implementations.
- **Performance:** Protocols impose no runtime cost and are preferable to ABCs for Zig-like contracts.
- **Pitfall:** When interfacing with C extensions, ensure Protocol definitions match actual binary layouts.

---

## 4. Structs and Data Aggregates  
(See Advice D — Pattern 3)

- **Best Practice:** Always use `__slots__` to reduce memory usage and prevent accidental attribute creation.
- **Tip:** Use `field(default_factory=...)` for mutable defaults to avoid shared state.
- **Performance:** Large dataclasses can be expensive to instantiate; consider splitting hot-path structs if needed.
- **Tip:** For binary serialization, add explicit `to_bytes()` / `from_bytes()` helpers using `struct.pack/unpack`.
- **Pitfall:** Overusing `frozen=True` can make legitimate state transitions awkward; apply intentionally.

---

## 5. Dynamic Byte Buffers (Appendable)  
(See Advice D — Pattern 4)

- **Best Practice:** Implement exponential growth strategies to reduce reallocations.
- **Performance:** Use `memoryview` for zero-copy slicing and data access.
- **Tip:** Prefer batch appends over many small appends to reduce interpreter overhead.
- **Pitfall:** Sharing buffers across threads without locks can corrupt data.
- **Performance:** Prefer per-thread buffers to avoid contention in multi-threaded code.

---

## 6. Thread-Safe Blocking Queues (MailBox)  
(See Advice D — Pattern 5)

- **Best Practice:** Use `Condition` with `notify_all()` to guarantee deterministic wakeup on interrupt.
- **Tip:** Support optional timeouts via `condition.wait(timeout)` for graceful shutdown logic.
- **Testing:** Stress-test with artificial contention and forced interrupts.
- **Pitfall:** Improper lock ordering or re-entrancy can easily cause deadlocks.
- **Performance:** For true parallelism, consider multiprocessing — but only with explicit ownership transfer.

---

## 7. Temporary Files and Directories  
(See Advice D — Pattern 6)

- **Best Practice:** Always use context managers to guarantee cleanup.
- **Tip:** Prefer `mkstemp` or `NamedTemporaryFile` for secure, race-free file creation.
- **Tip:** Use `tempfile.gettempdir()` to respect platform-specific temp locations.
- **Pitfall:** Large temporary files can silently exhaust disk space; monitor or enforce size limits.
- **Best Practice:** Clean up persistent temp files explicitly if `delete=False` is required.

---

## 8. Ownership Transfer and Use-After-Release Prevention  
(See Advice D — Pattern 7)

- **Best Practice:** Require `Holder[T]` explicitly in function signatures to communicate ownership transfer.
- **Tip:** In multi-threaded code, transfer ownership via queues and create new Holders on receipt.
- **Performance:** Holder is intentionally lightweight; prioritize safety over micro-optimizations.
- **Tip:** Integrate Holder with context managers where appropriate to reduce boilerplate.
- **Pitfall:** Forgetting to validate empty Holders can lead to `None` misuse; assert aggressively in debug builds.

---

## 9. Deferred Cleanup (`defer`)  
(See Advice D — Pattern 8)

- **Best Practice:** Use `ExitStack` for multiple cleanup actions to preserve LIFO semantics.
- **Tip:** Encapsulate repeated defer patterns in helpers or decorators.
- **Tooling:** Add logging inside cleanup callbacks when debugging resource lifetimes.
- **Pitfall:** Exceptions raised inside ExitStack callbacks are suppressed; log them explicitly if relevant.
- **Tip:** Use `AsyncExitStack` in async contexts.

---

## 10. Error-Only Cleanup (`errdefer`)  
(See Advice D — Pattern 9)

- **Best Practice:** Use a dedicated `ErrDefer` helper for factories and constructors.
- **Testing:** Inject failures intentionally to verify cleanup ordering and suppression behavior.
- **Performance:** Keep cleanup logic minimal to avoid cascading failures.
- **Pitfall:** Deeply nested ErrDefers can obscure ordering; flatten where possible.
- **Tip:** Optional logging is useful for diagnostics but should not alter semantics.

---

## 11. Errors as Values (Internal)  
(See Advice D — Pattern 10)

- **Performance:** Prefer explicit `match` on `Result` in hot paths to avoid exception overhead.
- **Tip:** Add functional helpers (`map`, `and_then`) to improve composability.
- **Tooling:** Leverage mypy’s type narrowing when matching on Results.
- **Pitfall:** Excessive Result chaining can harm readability; refactor when it obscures intent.
- **Best Practice:** Convert low-level errors to domain-specific ones early.

---

## 12. API Boundary (Exceptions)  
(See Advice D — Pattern 11)

- **Best Practice:** Define a common base exception (e.g. `AmpeException`) with structured error codes.
- **Tip:** Use specific exception subclasses to allow granular user handling.
- **Performance:** Avoid repeated conversion at boundaries; centralize it.
- **Pitfall:** Never allow third-party exceptions to leak into internal logic.
- **Testing:** Verify that public APIs never return `Result` under any condition.

---

## Final Note

Advice C exists to **help**, not to rule.

If you find yourself asking:
> “Is this allowed?”

You are in the wrong document.

Consult **Advice D**.
