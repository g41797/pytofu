# Advices for Porting Zig to Python Patterns

This document provides targeted advices, tips, best practices, and potential pitfalls for each pattern described in "zig_to_python.md". These are designed to help implementers avoid common issues, optimize performance, ensure safety, and maintain fidelity to Zig's semantics while leveraging Python's strengths. Advices are grouped by section for easy reference.

## 1. Tagged Unions
- Use `frozen=True` in `@dataclass` to make variants immutable, mirroring Zig's compile-time safety and preventing accidental mutations.
- Always include a `case _:` in `match` statements to handle unexpected variants and avoid runtime errors; enable mypy's `--warn-unreachable` for static exhaustiveness checks.
- For large unions, consider performance: Pattern matching has O(1) average case but profile if used in hot loops.
- Tip: Combine with `typing.Literal` for enum-like tags if variants are simple, reducing boilerplate.
- Pitfall: Avoid subclassing dataclasses if using `__slots__`, as it can break slot inheritance.

## 2. Errors and Error Handling (Overview)
- Maintain strict separation: Use `Result` internally for all non-public functions to prevent exception leakage and ensure explicit error paths.
- In public APIs, document all possible exceptions in docstrings with `Raises:` sections for better user experience.
- Performance advice: In high-throughput code, minimize boundary crossings to avoid repeated Result-to-exception conversions.
- Best practice: Use enums for error sets to allow easy extension without breaking APIs; map to specific exception subclasses for granularity.
- Pitfall: Don't mix exceptions and Results in the same module—enforce via code reviews or linters.

## 3. Interfaces (Protocols)
- Leverage mypy or pyright for static type checking to catch interface mismatches early, simulating Zig's implicit interface verification.
- For runtime validation, use `typing.runtime_checkable` on Protocols and `isinstance` in critical paths, but sparingly to avoid overhead.
- Tip: Define Protocols with default implementations via class methods if needed, but keep them minimal to preserve duck typing flexibility.
- Performance: Protocols add no runtime cost; prefer over ABCs for Zig-like implicit conformance.
- Pitfall: If interfacing with C extensions (e.g., via ctypes), ensure Protocols align with struct layouts for binary compatibility.

## 4. Structs
- Always use `__slots__` to reduce memory footprint and improve access speed, especially for message-like structs in high-volume scenarios.
- For binary serialization, integrate `struct.pack/unpack` in dataclass methods (e.g., `to_bytes/from_bytes`) to handle endianness and packing.
- Best practice: Make dataclasses frozen for immutability unless mutation is required, preventing bugs akin to Zig's const correctness violations.
- Tip: Use `field(default_factory=...)` for complex defaults, like lists or dicts, to avoid shared mutable state.
- Pitfall: Large structs with many fields can slow down instantiation; profile and consider splitting if necessary.

## 5. Dynamic Byte Buffers (Appendable)
- Implement exponential resizing in the wrapper class to minimize reallocations, similar to Zig's arena growth strategies.
- For thread-safety, add locks if buffers are shared, but prefer per-thread buffers to avoid contention in multi-threaded environments.
- Performance tip: Use `memoryview` on `bytearray` for zero-copy slicing and views, reducing memory overhead in processing pipelines.
- Best practice: Add bounds checking in methods like `append` to prevent buffer overflows, with custom exceptions for errors.
- Pitfall: Avoid frequent small appends; batch operations where possible to mitigate Python's interpreter overhead.

## 6. Thread-Safe Blocking Queues (MailBox)
- Use `threading.Condition` with `notify_all` for interrupts to ensure all waiting threads wake up promptly during shutdown.
- Test extensively for race conditions: Use `concurrent.futures` or `pytest` with threading mocks to simulate high-load scenarios.
- Performance advice: If GIL-bound, consider multiprocessing for true parallelism, but note increased complexity for shared state.
- Tip: Add timeout support via `condition.wait(timeout)` and handle `queue.Empty`-like cases gracefully.
- Pitfall: Custom queues can deadlock if locks are nested improperly; use `with lock:` consistently and avoid reentrancy issues.

## 7. Temporary Files (temp.zig)
- Always use `with` statements for automatic cleanup, even in simple cases, to prevent file descriptor leaks.
- For security, specify `delete=True` in `tempfile` functions and use `mkstemp` for unique names to avoid race conditions.
- Best practice: Handle platform differences (e.g., Windows vs. Unix paths) by using `tempfile.gettempdir()` dynamically.
- Tip: If needing persistent temps, use `NamedTemporaryFile(delete=False)` but manually clean up in `finally` blocks.
- Pitfall: Large temp files can exhaust disk space; monitor and add size limits if applicable.

## 8. Ownership Transfer and Use-After-Release Prevention (`*?*` Idiom)
- Enforce usage with type hints: Make functions accept `Holder[T]` to signal ownership semantics clearly.
- In multi-threaded code, use queues or channels to transfer ownership, creating new Holders on receipt to maintain single-owner invariant.
- Performance tip: Since Holder is lightweight, inline its logic if overhead is an issue, but prioritize safety.
- Best practice: Integrate with context managers for automatic put-back on scope exit, reducing boilerplate.
- Pitfall: Forgetting to check `is_empty()` after operations can lead to NoneType errors; add assertions in debug mode.

## 9. Deferred Cleanup (`defer`)
- Prefer `ExitStack` for multiple cleanups to maintain LIFO order and avoid deep nesting of `try/finally`.
- For repetitive patterns, use decorators to encapsulate common defers, improving code reuse and readability.
- Best practice: Combine with logging in callbacks for tracing resource lifetimes in debug modes.
- Tip: In async code, use `asyncio` equivalents like `async with` or `contextlib.AsyncExitStack`.
- Pitfall: Callbacks that raise exceptions are suppressed by `ExitStack`; log them if critical.

## 10. Error-Only Cleanup (`errdefer`)
- Use `ErrDefer` in factory functions to ensure partial objects are destroyed only on failure, transferring ownership on success.
- Test with deliberate failures: Inject exceptions to verify cleanups run in reverse order without masking originals.
- Performance advice: Keep cleanups lightweight to avoid compounding errors in failure paths.
- Best practice: Suppress cleanup exceptions intentionally, as in Zig, but add optional logging for diagnostics.
- Pitfall: Nested `ErrDefer` can complicate ordering; flatten where possible or document interactions.

## 11. Error Union Types (Errors as Values)
- In hot paths, use explicit `match` on Results instead of `try_result` to avoid exception overhead.
- Extend `Result` with methods like `map` or `and_then` for functional chaining, improving composability.
- Best practice: Use mypy's union narrowing to ensure type safety when unwrapping.
- Tip: For error conversion, define a mapping function to translate low-level errors to domain-specific ones.
- Pitfall: Overusing Results can make code verbose; balance with exceptions at natural boundaries.

## 12. API Boundary Pattern (Exceptions at Interface)
- Document public methods thoroughly, listing all possible exceptions and their causes for user predictability.
- Use subclassed exceptions for better catch granularity, allowing users to handle specific errors without broad `except`.
- Performance tip: Cache common Results if boundaries are crossed frequently, but avoid if stateful.
- Best practice: Add a base `AmpeException` with `error_code` for programmatic handling.
- Pitfall: Ensure internal functions never raise exceptions; wrap any third-party calls in Results.