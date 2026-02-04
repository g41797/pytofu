# Negotiation Guidelines: Collaborative Porting Protocol

To ensure the successful porting of **tofu** to **pytofu**, we will follow this structured negotiation process for every architectural decision and implementation step.

## 1. The Negotiation Cycle

### Step 1: Proposal (AI)
The AI analyzes the Zig source code (Source of Truth) and creates a detailed specification or architectural proposal in the `porting/specifications/` or `porting/architecture/` folder.

### Step 2: Review & Challenge (Author)
The Author reviews the proposal. You are encouraged to:
- Ask for clarification on Zig-to-Python translations.
- Challenge choices that feel un-Pythonic.
- Propose alternative libraries or patterns.
- Request "Deep Dives" into specific Zig logic.

### Step 3: Refinement (Collaborative)
We discuss the alternatives. The AI provides pros/cons for each option (e.g., performance vs. readability). We iterate on the specification until both parties are satisfied.

### Step 4: Decision & Handshake (Author)
The Author makes the final decision. Once a decision is reached:
1. The AI updates the relevant specification file.
2. The AI records the decision in `DECISION-LOG.md`.
3. The AI updates `SESSION-STATE.md` to move to the implementation task.

### Step 5: Implementation (Author)
The Author writes the code in the `src/` or `tests/` folders based on the finalized spec.

### Step 6: Peer Review (AI)
After implementation, the AI reviews the Python code to ensure it meets the negotiated spec and maintains protocol compatibility with the Zig source.

## 2. Resolving Conflicts
- **Source of Truth Priority:** In cases of protocol behavior, the original Zig implementation is the absolute authority.
- **Pythonic Idioms:** In cases of implementation style (how we write the code), Pythonic best practices (PEP 8, asyncio standards) should generally prevail, unless they break protocol compatibility.
- **Author's Veto:** As the sole implementer, the Author has the final word on what code is written.

## 3. Long-Term Consistency
- No decision is too small to log if it affects the public API or the wire protocol.
- We will periodically review the `MASTER-PLAN.md` to ensure our micro-decisions aren't drifting away from the core architectural goals.
