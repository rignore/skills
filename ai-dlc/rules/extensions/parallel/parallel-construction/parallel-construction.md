# Parallel Construction Rules

## Overview

This extension organizes the system's units of work into dependency-ordered **execution waves**, freezes the interfaces between units into explicit **contracts**, and builds the mutually-independent units of a wave **concurrently** in isolated `git worktree`s. Units with no mutual dependencies are implemented in parallel by separate subagents; waves are separated by a merge barrier so a later wave always builds on the merged code of earlier waves.

**Scope**: This extension spans two stages.
- **Units Generation** (PC-01–PC-03): produce the wave schedule and inter-unit interface contracts (planning artifacts).
- **CONSTRUCTION** (PC-04–PC-08): replace `workflow.md`'s sequential per-unit loop with wave-based parallel execution, isolated worktrees, batched approval gates, orchestrator-only shared-state writes, and frozen-contract enforcement.

**Precondition**: Parallel execution requires a git repository and a workspace where each unit maps to a distinct code path (per `construction/code-generation.md` greenfield multi-unit structure). If those preconditions do not hold, the extension falls back to sequential execution (see PC-05 preflight) — the planning artifacts (PC-01–03) are still produced, but CONSTRUCTION runs the default `workflow.md` loop.

**Enforcement**: At Units Generation the model MUST produce the two artifacts and block on cycles/contract gaps. At CONSTRUCTION, when preconditions hold, the model MUST follow the wave-based flow below instead of the sequential per-unit loop.

### Blocking Parallel-Construction Finding Behavior

A **blocking parallel-construction finding** means:
1. The finding MUST be listed in the stage completion message under a "Parallel Construction Findings" section with the PC rule ID and description
2. The stage MUST NOT present the "Continue to Next Stage" / "Approve & Continue" option until all blocking findings are resolved
3. The model MUST present only the "Request Changes" option with a clear explanation of what needs to change
4. The finding MUST be logged in `aidlc-docs/audit.md` with the PC rule ID, description, and stage context

If this extension is enabled but the system decomposes into a single unit (no inter-unit dependencies and no boundaries to contract), rules PC-01 and PC-02 are marked **N/A**, PC-03 is trivially satisfied, and PC-04–PC-08 still apply but collapse: the single unit's design stages are batched into one W1 gate (PC-06's W1/W2/W3 gates still hold), and PC-05's merge step is a no-op because PC-08 lets the main session implement the sole unit directly on base without a worktree. This is not a blocking finding. Note this is **not identical** to the sequential per-stage flow (it presents three batched wave gates, not the up-to-six per-stage gates) — it only removes the parallel/worktree overhead.

### Default Enforcement

All rules in this document are **blocking** by default. If any rule's verification criteria are not met, it is a blocking parallel-construction finding — follow the blocking finding behavior defined above.

### Verification Criteria Format

Verification items are plain bullet points describing compliance checks, distinct from the `- [ ]` progress-tracking checkboxes in stage plan files. Each item is evaluated as compliant or non-compliant.

---

## Rule PC-01: Wave Derivation from the Unit Dependency Matrix

**Rule**: During Units Generation, after the mandatory `unit-of-work-dependency.md` (the unit dependency matrix) is produced, the model MUST derive an execution wave schedule and save it as `aidlc-docs/inception/application-design/unit-of-work-waves.md`.

The derivation is a topological ordering of the dependency matrix:
- **Wave 1**: every unit that depends on no other unit
- **Wave N** (N ≥ 2): every unit whose dependencies are all satisfied by units in Waves 1 through N−1
- A unit is assigned to the earliest wave in which all of its dependencies are already placed

The schedule MUST be a table with these columns:

| Column | Meaning |
|---|---|
| Wave | The wave number the unit is assigned to |
| Unit | The unit name (matching `unit-of-work.md`) |
| depends_on | The units this unit directly depends on (empty for Wave 1) |
| Rationale | Why this unit lands in this wave (which dependency forces it later, or "no dependencies") |

Units in the same wave are, by construction, mutually independent — this is the property the parallel execution in PC-04 relies on.

**Verification**:
- `unit-of-work-waves.md` exists and covers every unit listed in `unit-of-work.md` (no unit missing, none invented)
- Every unit's wave number is strictly greater than the wave number of each of its dependencies
- Wave 1 contains exactly the units with an empty `depends_on`
- The `depends_on` column is consistent with `unit-of-work-dependency.md` (no dependency added or dropped)
- Each row's Rationale names the dependency that determines its wave, or states "no dependencies"

---

## Rule PC-02: Inter-Unit Interface Contract Extraction

**Rule**: During Units Generation, the model MUST extract the interfaces that cross unit boundaries and record them as `aidlc-docs/inception/application-design/unit-interface-contracts.md`. The source material is the Application Design output — `component-methods.md` (method signatures, input/output types), `components.md` (component interfaces), and `services.md` (service orchestration) — combined with `unit-of-work.md` (which components/services belong to which unit).

Only **cross-unit** interfaces are contracts. An interface used entirely within a single unit is that unit's private implementation detail and MUST NOT be contracted. A contract is required wherever one unit calls, consumes, or shares data with another.

Each contract entry MUST record:
- **Providing unit**: the unit that owns/implements the interface
- **Consuming unit(s)**: the unit(s) that depend on it
- **Interface**: the method signature, API endpoint, event, or shared data model
- **Input / output types**: the data shapes crossing the boundary
- **Stability note**: this contract is **frozen** for the duration of construction — a unit may not unilaterally change a contract it provides; a change requires returning to Application Design / Units Generation and re-approving. PC-08 enforces this against parallel subagents.

**Verification**:
- `unit-interface-contracts.md` exists and every inter-unit dependency in `unit-of-work-dependency.md` is backed by at least one contract entry (a dependency with no contract is a gap)
- No contract entry describes an interface whose provider and consumer are the same unit (internal interfaces are excluded)
- Each contract names a providing unit, at least one consuming unit, and concrete input/output types (not "TBD")
- Contract interfaces trace to a real entry in `component-methods.md` / `components.md` / `services.md`

---

## Rule PC-03: Dependency Cycle Detection

**Rule**: If the topological ordering in PC-01 cannot be completed because two or more units depend on each other (directly or transitively), the model MUST NOT fabricate a wave assignment to force completion. A cycle means the decomposition is invalid for wave scheduling. The model MUST:
1. Halt wave generation
2. Report the specific cycle (the exact chain of units, e.g. "Unit A → Unit B → Unit A")
3. Raise it as a blocking finding requiring a return to Units Generation (or Application Design) to redraw unit boundaries so the cycle is broken (e.g. by extracting the shared concern into its own Wave-1 unit)

**Verification**:
- If a cycle exists, no `unit-of-work-waves.md` was produced with a forced/arbitrary assignment; instead a blocking finding names the cycle
- If no cycle exists, PC-03 is satisfied and the wave schedule is complete
- The reported cycle (if any) lists the exact unit chain

---

## Rule PC-04: Wave-Based Execution Scheduling

**Rule**: When preconditions hold (PC-05 preflight passes), CONSTRUCTION executes wave by wave using `unit-of-work-waves.md`, replacing the sequential per-unit loop in `workflow.md`. For each wave, in order:

1. **Design (parallel)**: run the applicable design stages (Functional Design, NFR Requirements, NFR Design, Infrastructure Design — CONDITIONAL exactly as in the sequential flow) for every unit in the wave concurrently (PC-08 dispatch). Present them together at Gate W1 (PC-06).
2. **Code planning (parallel)**: create each unit's code generation plan (with TDD step ordering if TDD is enabled) concurrently. Present together at Gate W2.
3. **Implementation (parallel)**: implement every unit in the wave concurrently, each in its own worktree (PC-05), each subagent following its approved plan, the frozen contracts (PC-08), and TDD/review extensions if enabled.
4. **Per-unit review + merge**: run the subagent code review (if enabled) per unit inside its worktree; then, at Gate W3, present the wave's results and, on approval, the orchestrator merges the units in dependency order and runs the wave integration build/test (PC-05).

A later wave MUST NOT start until the previous wave is merged and its integration check has run. Within a wave, per-stage rule files (`functional-design.md`, `code-generation.md`, etc.) still govern each unit — this rule changes *when and how many units run at once*, not what each stage does.

**Verification**:
- CONSTRUCTION followed the wave order in `unit-of-work-waves.md`
- Units within a wave were designed/planned/implemented concurrently, not one fully before the next
- No wave began before the prior wave was merged and integration-checked
- Each unit still went through its applicable per-stage rules

---

## Rule PC-05: Git Worktree Isolation and Merge Lifecycle

**Rule**: Parallel implementation MUST isolate each unit in its own `git worktree` so concurrent subagents cannot conflict on file writes.

**Preflight (before the first wave, orchestrator)**:
- Verify the workspace is a git repository. If not: for greenfield, offer to `git init`; if the user declines or it is otherwise impossible, DISABLE parallel execution and fall back to the sequential per-unit loop (log the fallback in audit.md).
- Verify the **application-code** paths are clean (no uncommitted changes to source under the workspace's code directories). The `aidlc-docs/` tree is *expected* to be dirty — the orchestrator appends `audit.md` and updates `aidlc-state.md` throughout the workflow (per workflow.md Prompts Logging), so the clean check MUST exclude `aidlc-docs/` (equivalently, the orchestrator commits or `.gitignore`s `aidlc-docs/` before the preflight). If application-code paths have uncommitted changes from an unrelated prior edit, halt and report. On greenfield where no application code is tracked yet, an empty/untracked code tree counts as clean.
- Verify units map to distinct code paths (per `code-generation.md` structure). If units would write the same files, treat those files as shared (Wave 0 below).

**Wave 0 — shared files (orchestrator, sequential)**: Files multiple units would touch (root config like `package.json`/`pyproject`, shared modules) are excluded from parallel work. The orchestrator creates them sequentially before the first wave and commits them to the base branch. Subagent prompts forbid modifying shared paths (escalate if needed — PC-08).

**Per wave**:
- For each unit, create branch `unit/{unit-name}` from the current base and `git worktree add` an isolated directory. Each subagent works only inside its own worktree.
- After Gate W3 approval, the orchestrator merges units into the base in dependency order. On merge conflict, the orchestrator attempts resolution; if resolution would require changing a frozen contract or an approved plan, it STOPS and reports to the user rather than changing them.
- After merging the wave, remove the worktrees and unit branches, then run the **wave integration build/test** (unit greens do not guarantee integrated greens). Integration failure is a blocking finding for that wave.
- The next wave branches from the merged base.

**Verification**:
- Preflight ran; non-git / dirty-tree / same-path conditions were handled (fallback or Wave 0), not ignored
- Each parallel unit was implemented in its own worktree/branch
- Merges happened in dependency order, performed by the orchestrator
- Conflicts requiring contract/plan changes were escalated, not silently resolved
- Worktrees/branches were cleaned up and a wave integration check ran after each merge

---

## Rule PC-06: Batched Approval Gates (per wave)

**Rule**: In parallel mode the sequential flow's per-unit gates (up to six per unit) are replaced by **three gates per wave**:

| Gate | Content | What the user sees |
|---|---|---|
| W1 — wave design | all units' design-stage outputs for the wave | per-unit design summary table + document paths; approve or request changes per unit (only changed units are reworked) |
| W2 — wave code plans | all units' code generation plans | per-unit plan summary + step counts |
| W3 — wave merge | parallel implementation + per-unit review complete | per-unit: created/modified files, test results, review findings summary; on approval the orchestrator merges |

Each gate MUST present a per-unit summary table so the reviewer can act unit by unit despite the batched gate. Requesting changes on one unit reworks only that unit; the others in the wave are unaffected.

**Verification**:
- Exactly the three wave gates were presented per wave (not per-unit gates)
- Each gate included a per-unit summary table
- A change request on one unit did not force rework of the whole wave
- The user approved the merge (W3) before the orchestrator merged

---

## Rule PC-07: Orchestrator-Only Shared-State Writes

**Rule**: During concurrent execution, shared state MUST be written only by the orchestrator (the main workflow session). This includes `aidlc-docs/audit.md`, `aidlc-docs/aidlc-state.md`, stage/plan checkbox updates, and any file outside a single unit's directory. Implementation/review/fix subagents write ONLY within their own unit's worktree and their own unit's `aidlc-docs/construction/{unit-name}/` directory.

The orchestrator collects each subagent's results and performs all shared-state writes itself (audit entries, state updates, checkbox marks), preserving audit.md's append-only integrity (concurrent writes would corrupt it).

**Verification**:
- No subagent wrote to audit.md, aidlc-state.md, or another unit's files
- The orchestrator performed all shared-state writes, aggregating subagent results
- audit.md remained append-only and uncorrupted across the wave

---

## Rule PC-08: Parallel Dispatch and Frozen-Contract Enforcement

**Rule**: Each unit in a wave is implemented by a subagent given a **context pack**: its own unit's design artifacts, its approved code generation plan, `unit-interface-contracts.md` (the frozen contracts it must honor and may consume), and the TDD rule if enabled. The pack does NOT include other units' in-progress work or the generation conversation.

Each subagent prompt MUST state:
- **Do not change any frozen interface contract** (yours or another unit's). If fulfilling the plan appears to require a contract change, STOP and report an escalation instead of changing it.
- **Modify only files within your unit's declared code path** (and your worktree). Do not touch shared paths (Wave 0) or other units.
- Follow the approved plan; keep tests green (and, if TDD is enabled, preserve red-before-green for new tests).

A wave with only one unit MAY be implemented directly by the main session without a separate subagent/worktree (isolation overhead is unnecessary when nothing runs concurrently).

**Verification**:
- Each subagent's context pack contained its plan and the frozen contracts, and excluded other units' work and the generation conversation
- Subagent prompts forbade contract changes and out-of-boundary writes, requiring escalation
- No contract was changed by an implementation subagent; contract-change needs were escalated
- Single-unit waves did not incur unnecessary worktree/subagent overhead

---

## Enforcement Integration

| Stage | Applicable Rules | Enforcement |
|---|---|---|
| Units Generation | PC-01, PC-02, PC-03 | Produce wave schedule + interface contracts; block on cycles/contract gaps |
| CONSTRUCTION (parallel mode) | PC-04, PC-05, PC-06, PC-07, PC-08 | Execute waves with isolated worktrees, batched gates, orchestrator-only shared writes, frozen contracts; fall back to sequential if preconditions fail |

At each stage:
- Include a "Parallel Construction Compliance" section in the stage completion summary listing each applicable PC rule as compliant, non-compliant, or N/A
- Non-compliance with any applicable rule is a blocking finding — follow the blocking finding behavior in the Overview

---

## Interaction with Other Extensions

- **TDD**: applies per unit inside each worktree. Each implementation subagent runs its own red-green-refactor cycle for its unit; red/green records go in that unit's `code/` directory.
- **Subagent Code Review**: the reviewer runs per unit inside that unit's worktree after implementation and before merge (Gate W3). The bounded auto-fix loop (CR-05) runs within the worktree. Merge (PC-05) happens only after the unit's review is clean.
- **Security Baseline / PBT**: enforce at their own stages per their Enforcement Integration; they apply per unit and are unaffected by parallelism.
- **Single-unit or single-chain decompositions**: if every wave has one unit (a pure dependency chain), no units run concurrently, so PC-08 removes the worktree/subagent overhead and PC-05's merge is a no-op. The wave gates (PC-06) still apply — each single-unit wave gets W1/W2/W3 with its design stages batched into W1 — so this is **not identical** to the sequential per-stage flow, only free of parallelism overhead. Enabling the extension here mainly adds the planning artifacts plus the batched-gate structure.
