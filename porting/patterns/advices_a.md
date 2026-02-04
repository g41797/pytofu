# Zig → Python Porting Patterns: Architectural Advice & Pitfalls

This document complements the main **Zig → Python porting pattern guide**.  
It provides **practical advice, constraints, and “gotchas”** for each pattern to ensure semantic correctness, performance, and long-term maintainability.

**Audience:** Contributors working on `pytofu` or similar Zig-derived systems  
**Goal:** Preserve Zig semantics where correctness matters, while remaining realistic in Python

---

## 1. Tagged Unions

### Advice
- Prefer **small, immutable dataclasses** for union variants.
- Keep variants **structurally distinct** (different field names or shapes).
- Always handle all cases explicitly in `match`.

### Avoid
- Using a single class with a `kind` field (this reintroduces manual dispatch).
- Relying on inheritance hierarchies (they do not map well to Zig unions).

### Enforcement Rule
> Every `match` on a tagged union must either be exhaustive or raise explicitly on unknown cases.

---

## 2. Error Handling Strategy (Overview)

### Advice
- Treat **exceptions as an API concern**, not a core logic mechanism.
- Internal code should **never raise domain exceptions**.
- Errors should be visible in function signatures (`Result[T, E]`).

### Avoid
- Mixing `Result` returns with `raise` in the same layer.
- Raising exceptions inside hot-path internal logic.

### Enforcement Rule
> If a function returns `Result`, it must not raise domain exceptions.

---

## 3. Interfaces (Protocols)

### Advice
- Use `typing.Protocol` to model **capability-based design**, not inheritance.
- Keep protocols **minimal** (only the required methods).
- Prefer **read-only protocols** where possible.

### Avoid
- Marker base classes.
- ABCs unless runtime enforcement is explicitly required.

### Enforcement Rule
> Protocols must describe behavior, not ownership or lifecycle.

---

## 4. Structs

### Advice
- Use `@dataclass(slots=True)` for all Zig-like structs.
- Keep structs **dumb**: data + minimal invariants.
- Move logic into functions or controllers.

### Avoid
- Rich, behavior-heavy data objects.
- Mutable public fields without invariants.

### Enforcement Rule
> Structs may validate state but must not coordinate system behavior.

---

## 5. Dynamic Byte Buffers

### Advice
- Wrap `bytearray` to expose **explicit operations** (`append`, `shrink`, `reset`).
- Make buffer ownership explicit in APIs.

### Avoid
- Passing raw `bytearray` across ownership boundaries.
- Implicit resizing hidden behind slicing.

### Enforcement Rule
> Any buffer crossing threads or queues must have a single clear owner.

---

## 6. Thread-Safe Blocking Queues (MailBox)

### Advice
- Prefer explicit `interrupt()` / `wake_all()` semantics.
- Model shutdown as **a first-class state**, not an exception.

### Avoid
- `queue.Queue` when shutdown signaling is required.
- Sentinel values unless strongly typed.

### Enforcement Rule
> Blocking waits must be interruptible without timeouts.

---

## 7. Temporary Files and Directories

### Advice
- Always use context managers.
- Scope temporary resources as narrowly as possible.

### Avoid
- Manual cleanup logic.
- Relying on garbage collection for filesystem cleanup.

### Enforcement Rule
> Temporary resources must be released deterministically.

---

## 8. Ownership Transfer (`*?*T` → `Holder[T]`)

### Advice
- Treat `Holder[T]` as **the ownership token**, not a convenience wrapper.
- Invalidate aggressively and fail fast on misuse.
- Assume **single-thread ownership** only.

### Avoid
- Silent reuse after `take()` or `clear()`.
- Passing raw values instead of holders across ownership boundaries.

### Enforcement Rule
> After ownership transfer, the source holder must be unusable.

---

## 9. `defer` Semantics

### Advice
- Use `with` for single-resource lifetimes.
- Use `ExitStack` when more than one cleanup action exists.
- Preserve **LIFO cleanup order**.

### Avoid
- Deeply nested `try/finally` blocks.
- Cleanup logic duplicated across return paths.

### Enforcement Rule
> Multiple deferred cleanups must execute in reverse order of registration.

---

## 10. `errdefer` Semantics

### Advice
- Use `ErrDefer` (or equivalent) **only for partial construction rollback**.
- Explicitly call `success()` to transfer ownership.
- Suppress cleanup errors intentionally.

### Avoid
- Using `errdefer`-style logic for normal control flow.
- Mixing `errdefer` and unconditional cleanup.

### Enforcement Rule
> Error-only cleanup must not run on successful return.

---

## 11. Errors as Values (`Result[T, E]`)

### Advice
- Use `Result` for:
  - allocation
  - pool access
  - protocol validation
  - message lifecycle operations
- Pattern-match explicitly in hot paths.

### Avoid
- Exception-based propagation in tight loops.
- Converting errors to strings prematurely.

### Enforcement Rule
> Internal functions must return errors explicitly, not implicitly.

---

## 12. API Boundary (Result → Exception)

### Advice
- Convert errors **only at clearly marked boundaries**.
- Use a decorator or wrapper to make conversion obvious.
- Preserve error codes inside exceptions.

### Avoid
- Leaking `Result` into user-facing APIs.
- Raising raw enums or strings.

### Enforcement Rule
> All public APIs must either return values or raise exceptions — never `Result`.

---

## Performance Guidance (Global)

### Hot Paths
- Prefer explicit `match Result` over exception-based helpers.
- Minimize allocations.
- Avoid dynamic typing in inner loops.

### Cold Paths
- Prefer clarity over micro-optimizations.
- `try_result` and helpers are acceptable.

---

## Mental Model Reminder

Zig guarantees:
- compile-time ownership checks
- deterministic cleanup
- explicit error flow

Python guarantees **none** of these by default.

This pattern set exists to **reintroduce those guarantees deliberately**, not accidentally.

---

## Final Rule of Thumb

> If a pattern feels “too strict for Python”, it probably exists to replace a Zig compiler guarantee.

Respect it.

