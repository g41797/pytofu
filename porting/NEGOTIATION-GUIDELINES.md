# Negotiation Guidelines: Collaborative Porting Protocol

To ensure the successful porting of **tofu** to **pytofu**, we will follow this structured, **file-based** negotiation process for every architectural decision and implementation step.

## 1. The File-Based Negotiation Cycle

We will use `porting/NEGOTIATION.md` as our persistent discussion buffer. The interactive terminal will be used only for high-level coordination and triggering tool actions.

### Step 1: Proposal (AI)
The AI analyzes the Zig source code (Source of Truth) and:
1. Creates or updates a specification file in `porting/specifications/`.
2. Appends a new "Negotiation Entry" to `porting/NEGOTIATION.md` summarizing the proposal and linking to the spec.

### Step 2: Review & Feedback (Author)
The Author reviews the proposal and the spec. The Author provides feedback by:
- Appending comments/questions directly to the relevant entry in `porting/NEGOTIATION.md`.
- Modifying the specification file (if specific wording changes are desired).

### Step 3: Refinement (Collaborative)
The AI reads `porting/NEGOTIATION.md`, addresses the Author's points, and updates the specification. This continues until a "Handshake" is reached.

### Step 4: Decision & Handshake (Author)
The Author signals the final decision by writing "DECIDED" or "HANDSHAKE" in `porting/NEGOTIATION.md`.
1. The AI records the decision in `DECISION-LOG.md`.
2. The AI updates `SESSION-STATE.md` to mark the task as ready for implementation.

### Step 5: Implementation (Author)
The Author writes the code in the `src/` or `tests/` folders based on the finalized spec.

### Step 6: Peer Review (AI)
After implementation, the AI reviews the Python code to ensure it meets the negotiated spec.

## 2. Resolving Conflicts
- **Source of Truth Priority:** In cases of protocol behavior, the original Zig implementation is the absolute authority.
- **Pythonic Idioms:** Pythonic best practices (PEP 8, asyncio standards) should generally prevail, unless they break protocol compatibility.
- **Author's Veto:** As the sole implementer, the Author has the final word on what code is written.

## 3. Long-Term Consistency
- No decision is too small to log if it affects the public API or the wire protocol.
- We will periodically review the `MASTER-PLAN.md` to ensure our micro-decisions aren't drifting away from the core architectural goals.
