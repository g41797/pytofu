# Negotiation Buffer: pytofu

This file is the primary channel for architectural discussions, specification reviews, and decision-making.

---

## [2026-02-04] Task: opcode.py Implementation

**Status:** Awaiting Handshake

### AI Proposal:
I have reviewed the original Zig implementation of opcodes. In Zig, these are defined in `src/ampe/ampe.zig`.

**Source Reference:** `porting/repos/tofu/src/ampe/ampe.zig` (OpCode enum)

**Specification:** `porting/specifications/opcode.md`

**Summary of Proposed Mapping:**
- We will use a standard Python `enum.IntEnum` for `OpCode`.
- Values (0-9) must match the Zig implementation exactly to maintain wire compatibility.
- We will include docstrings explaining the purpose of each opcode (e.g., `DATA`, `SYN`, `ACK`, etc.).

### Author Feedback:
(Author: Please add your comments, questions, or "HANDSHAKE" here.)
