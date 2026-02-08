
# Advice D — Canonical Zig → Python Porting Rules for pytofu

This document is the **authoritative consolidation** of all Zig→Python porting advice
for the `pytofu` project.

It resolves contradictions between earlier advice documents and establishes
**explicit bias rules** that govern how conflicts are decided.

This file is normative.  
If guidance elsewhere disagrees with this document, **this document wins**.

---

## Bias Resolution Model (MANDATORY READING)

When porting Zig idioms to Python, multiple valid translations may exist.
To prevent inconsistency and architectural drift, **every rule in this document
is governed by an explicit bias**.

A *bias* is a conflict-resolution policy — not a preference.

### The Three Biases

#### 1. Conservative Bias
**Primary value:** safety, predictability, misuse resistance

When advice conflicts, the Conservative bias chooses the option that:
- Fails fast and loudly
- Preserves invariants under refactor pressure
- Is hardest to misuse by non-experts
- Prefers explicit state over convention

Assumptions:
- Future maintainers may not understand Zig
- Code will be modified under time pressure
- Defensive checks are preferable to elegance

Typical outcomes:
- Explicit runtime validation
- Single allowed pattern instead of multiple variants
- Boilerplate is acceptable

Used for:
- Ownership and lifecycle management
- Thread boundaries
- Shutdown and recovery paths
- Pool and allocator logic

---

#### 2. Pythonic Bias
**Primary value:** idiomatic Python and developer familiarity

When advice conflicts, the Pythonic bias chooses the option that:
- Matches common Python expectations
- Integrates cleanly with Python tooling
- Minimizes ceremony at API boundaries
- Uses standard language features where possible

Assumptions:
- Public users think in exceptions, not error values
- Readability outweighs strict semantic mirroring
- Python conventions reduce cognitive load

Typical outcomes:
- Exceptions instead of Result
- Context managers instead of manual stacks
- Duck typing over explicit protocols (where safe)

Used for:
- Public API surface
- Examples and documentation
- Integration with external Python code

---

#### 3. Zig-Faithful Bias

**Primary value:** semantic equivalence with Zig

When advice conflicts, the Zig-Faithful bias chooses the option that:
- Preserves Zig’s guarantees, not just behavior
- Makes ownership transfer explicit
- Prevents states Zig would make impossible
- Accepts verbosity to encode meaning

Assumptions:
- Zig semantics are intentional and relied upon
- Compile-time guarantees must be simulated at runtime
- Implicit behavior is dangerous

Typical outcomes:
- Explicit ownership wrappers
- Errors as values internally
- Deterministic cleanup ordering
- No implicit control flow

Used for:
- Core engine internals
- Message lifecycle and ownership
- Concurrency and protocol correctness
- Code mirrored 1:1 from Zig



### Bias Precedence Rule

If multiple biases apply and no bias is explicitly stated, the following
precedence order is MANDATORY:

Zig-Faithful > Conservative > Pythonic

Rationale:
- Zig-Faithful preserves semantic guarantees and protocol correctness
- Conservative protects invariants under maintenance and refactor pressure
- Pythonic is limited to usability and surface-level ergonomics


## MANDATORY RULE

Public API is the **only** place where Pythonic bias may override Zig-Faithful behavior.
In all internal code, Zig-Faithful and Conservative biases always take precedence.


## Pattern 1: Tagged Unions

### Scope
- Internal and public
- Data modeling

### Zig Guarantees
- Exactly one active variant
- Exhaustive handling enforced by compiler

### Python Risks
- Silent acceptance of unknown variants
- Non-exhaustive `match` statements

### Canonical Rule (Zig-Faithful)
**Tagged unions MUST be modeled using dataclasses and structural pattern matching.**

### Allowed Implementations
- `@dataclass` variants + `match/case`

### Forbidden Patterns
- Untagged dicts
- Stringly-typed discriminators

### Notes
- Exhaustiveness is enforced by convention + tests

---

## Pattern 2: Interfaces / Implicit Contracts

### Scope
- Internal and public

### Zig Guarantees
- Implicit interfaces enforced structurally

### Python Risks
- Accidental partial implementations

### Canonical Rule (Zig-Faithful)
**Interfaces MUST be expressed using `typing.Protocol`.**

### Allowed Implementations
- Structural protocols (PEP 544)

### Forbidden Patterns
- ABC inheritance for implicit contracts
- Duck typing without type checking in core logic

---

## Pattern 3: Structs and Data Aggregates

### Scope
- Internal and public

### Canonical Rule (Conservative)
**Zig structs MUST map to `@dataclass(slots=True)` unless mutation semantics forbid it.**

### Notes
- `__slots__` is required to prevent accidental attribute creation
- Binary layout concerns are handled separately

---

## Pattern 4: Dynamic Byte Buffers

### Scope
- Internal

### Canonical Rule (Conservative)
**Growable buffers MUST be wrapped `bytearray` with explicit methods.**

### Forbidden Patterns
- Raw `bytes` concatenation in loops

---

## Pattern 5: Thread-Safe Blocking Queues (MailBox)

### Scope
- Internal, cross-thread

### Zig Guarantees
- Interruptible blocking
- Deterministic wakeup

### Canonical Rule (Zig-Faithful)
**`queue.Queue` MUST NOT be used.**

A custom queue using:
- `deque`
- `Lock`
- `Condition`
is REQUIRED to support `interrupt()` semantics.

---

## Pattern 6: Temporary Files and Directories

### Scope
- Internal

### Canonical Rule (Pythonic)
**Use `tempfile` with context managers.**

This is one of the few areas where Python provides a strictly superior abstraction.

---

## Pattern 7: Ownership Transfer (`*?*T`)

### Scope
- Internal ONLY
- Core invariant

### Zig Guarantees
- Single owner
- Source invalidated on transfer
- Use-after-release is impossible

### Canonical Rule (Zig-Faithful + Conservative)
**Ownership transfer MUST use an explicit invalidating wrapper (`Holder[T]`).**

### Allowed Implementations
- `Holder[T]` with `take()`, `clear()`

### Forbidden Patterns
- Passing raw `Message` across ownership boundaries
- Relying on discipline or comments

### Notes
- Holder is intentionally NOT thread-safe
- Ownership transfer must be explicit in signatures

---

## Pattern 8: `defer` (Always-Run Cleanup)

### Scope
- Internal

### Canonical Rule (Conservative)
**Multiple cleanup actions MUST use `ExitStack`.**

### Allowed Implementations
- `with obj:` for single resource
- `ExitStack` for multiple LIFO cleanup

### Forbidden Patterns
- Deeply nested `try/finally`
- Manual cleanup duplication

---

## Pattern 9: `errdefer` (Error-Only Cleanup)

### Scope
- Internal
- Constructors and factories

### Zig Guarantees
- Cleanup runs ONLY on error
- LIFO order
- Cleanup failures do not mask original error

### Canonical Rule (Zig-Faithful)
**Error-only cleanup MUST use a dedicated `ErrDefer` helper.**

### Forbidden Patterns
- Boolean success flags
- `finally` with conditional checks in core code

---

## Pattern 10: Errors as Values (Internal)

### Scope
- Internal ONLY

### Zig Guarantees
- Errors are values
- Explicit propagation

### Canonical Rule (Zig-Faithful)
**Internal functions MUST return `Result[T, AmpeError]`.**

### Notes
- `try_result()` MAY be used, but explicit matching is preferred in hot paths

---

## Pattern 11: API Boundary (Exceptions)

### Scope
- Public API ONLY

### Canonical Rule (Pythonic)
**Public API MUST raise exceptions, never return `Result`.**

### Boundary Enforcement
- Conversion happens ONLY at explicit boundary decorators
- No exception leakage into internal logic

---

## Pattern 12: Bias Annotation Requirement

### Scope
- Documentation and review

### Canonical Rule (Conservative)
**Every non-trivial porting rule MUST declare its governing bias.**

This prevents:
- Silent semantic drift
- “Feels Pythonic” rewrites of Zig-critical code
- Review deadlocks

---

## Final Invariant

pytofu is **not** a Python rewrite of Zig code.  
It is a **semantic port**.

Python syntax is allowed to differ.  
Python idioms are allowed at boundaries.  
**Zig guarantees are not optional.**

If a choice must be made:

> Preserve the guarantee.  
> Encode the invariant.  
> Make misuse impossible.

---

