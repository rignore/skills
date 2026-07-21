# Subagent Code Review Rules

## Overview

These rules add an **isolated code review** to the Code Generation stage. After a unit's code is generated (`construction/code-generation.md` PART 2) and before the completion message is presented to the user, a separate reviewer subagent evaluates the generated code against the approved plan. The reviewer is deliberately isolated from the generation context so it judges "the plan vs. the result" without the bias of having authored the code.

This mirrors the generation-≠-evaluation separation used elsewhere in this toolchain: the entity that produces an artifact does not grade it.

**Enforcement**: At the Code Generation stage, the model MUST run the reviewer and resolve all blocking findings before presenting the stage completion message.

### Blocking Review Finding Behavior

A **blocking review finding** is any finding the reviewer classifies as **Critical** (see CR-03). A blocking review finding means:
1. The finding MUST be listed under a "Code Review Findings" section with its severity, the affected file, and the plan reference it violates
2. The stage MUST NOT present the "Continue to Next Stage" option until all Critical findings are resolved or explicitly waived by the user
3. The model MUST route Critical findings into the bounded auto-fix loop (CR-05) before presenting completion
4. The finding MUST be logged in `aidlc-docs/audit.md` with severity, file, and plan reference

### Default Enforcement

Critical findings are **blocking** by default. Major and Minor findings are **non-blocking** — they are reported in the completion message for the user to accept or defer, but they do not stop the workflow.

### Verification Criteria Format

Verification items in this document are plain bullet points describing compliance checks. Each item should be evaluated as compliant or non-compliant during review.

---

## Rule CR-01: Reviewer Isolation

**Rule**: The reviewer MUST run as a separate subagent invocation that does NOT receive the generation session's conversation, reasoning, or trial-and-error history. The reviewer receives only a **review context pack**:

**Provided to the reviewer**:
- The approved code generation plan for the unit (`aidlc-docs/construction/plans/{unit-name}-code-generation-plan.md`)
- The unit's design artifacts (functional design, NFR design, infrastructure design as applicable)
- The unit's interface contracts (method signatures, API endpoints, shared data models it must honor)
- The generated code: the list of created/modified files and their contents (or diff for brownfield)
- The test execution results, **when they exist at this stage**: red/green confirmation records if the TDD extension is enabled. When TDD is disabled, unit tests are authored but not yet executed at Code Generation (execution is deferred to Build and Test per `construction/code-generation.md` Completion Criteria), so no execution results are in the pack — see CR-02 for how the reviewer treats this case

**NOT provided to the reviewer**:
- The generation conversation or the generating model's chain of thought
- Any instruction to be lenient or to assume the code is correct

**Verification**:
- The reviewer is invoked as a distinct subagent, not the same context that generated the code
- The review context pack contains the approved plan and interface contracts
- The review context pack excludes the generation conversation/reasoning

---

## Rule CR-02: Review Scope — Plan Conformance

**Rule**: The reviewer evaluates the generated code strictly against the approved plan and design, not against its own preferences. The review MUST check:
- **Plan conformance**: every planned step produced the artifact it described; no planned functionality is missing
- **Interface contract compliance**: the code honors the declared method signatures, API endpoints, and shared data models — no silent contract changes
- **Test presence and coverage**: tests exist for the unit's stories and cover their acceptance criteria. Pass/fail is conditional on TDD: if the TDD extension is **enabled**, the red/green confirmation records (TDD-02/TDD-03) MUST show the tests passing; if TDD is **disabled**, unit tests are not yet executed at this stage, so the reviewer checks presence and coverage only and defers pass/fail to Build and Test (the reviewer MUST NOT treat not-yet-executed tests as failing)
- **Boundary compliance**: no files outside the unit's declared code paths were created or modified
- **Story coverage**: every story assigned to the unit is implemented

The reviewer MUST NOT propose scope changes, redesigns, or new features. Findings are limited to deviations from the approved plan/design and defects in fulfilling it.

**Verification**:
- Each finding references a specific plan item, interface contract, or story it relates to
- The reviewer did not introduce new requirements or redesign proposals
- The review covers plan conformance, contract compliance, test presence and coverage (and pass/fail when TDD is enabled), boundaries, and story coverage

---

## Rule CR-03: Severity Classification

**Rule**: Every finding MUST be classified into exactly one severity. The reviewer outputs findings with this schema: `severity · file · issue · plan_reference`.

| Severity | Meaning | Blocking |
|---|---|---|
| **Critical** | Approved plan not fulfilled; interface contract violated; no tests authored for an assigned story; when TDD is enabled, tests failing or a red confirmation missing; files modified outside the unit's boundary; an assigned story not implemented | Yes — blocks completion |
| **Major** | Code works but diverges from the plan's intent; missing error handling; a planned edge case not handled | No — reported for user decision |
| **Minor** | Style, naming, formatting, non-functional cleanliness | No — recorded |

The reviewer MUST default to the higher severity when a finding is ambiguous between two levels (lean toward blocking rather than waving through).

**Verification**:
- Every finding has exactly one severity from {Critical, Major, Minor}
- Contract violations, boundary breaches, and tests entirely absent for an assigned story are classified Critical; failing tests are Critical only when TDD is enabled (pass/fail is otherwise deferred to Build and Test)
- Ambiguous findings are classified at the higher severity, not the lower

---

## Rule CR-04: Critical Findings Block Completion

**Rule**: If the review produces any Critical finding, the model MUST NOT present the unit's Code Generation completion message. It MUST instead route the Critical findings into the bounded auto-fix loop (CR-05). Major and Minor findings do not block; they are surfaced in the completion message once no Critical findings remain.

**Verification**:
- No completion message was presented while a Critical finding was open
- Major/Minor findings appear in the completion message for user decision
- The blocking behavior matches the "Blocking Review Finding Behavior" in the Overview

---

## Rule CR-05: Bounded Auto-Fix Loop

**Rule**: Critical findings are resolved by a **fix subagent** — a fresh subagent invocation given the findings and the same isolation constraints. The fix subagent's prompt MUST include:
- The specific Critical findings to resolve
- The instruction: **do NOT change the approved plan's approach or the frozen interface contracts.** If a finding cannot be resolved without changing the plan or a contract, STOP and report it as an escalation rather than making the change.
- The boundary constraint: modify only files within the unit's declared code paths
- The instruction to keep tests green (and, if TDD is enabled, to preserve the red-before-green sequence for any newly added tests)

After the fix subagent completes, the reviewer (CR-01) re-runs on the updated code. The loop repeats until no Critical findings remain OR **2 fix rounds have completed**. If Critical findings remain after 2 rounds, the model MUST STOP the auto-fix loop and escalate to the user: present the remaining Critical findings, what was attempted, and ask the user how to proceed. The model MUST NOT loop indefinitely.

**Verification**:
- The fix subagent prompt forbids plan/contract changes and requires escalation instead
- The reviewer re-runs after each fix round
- The auto-fix loop terminates after at most 2 rounds
- Remaining Critical findings after 2 rounds are escalated to the user, not silently accepted or looped further

---

## Rule CR-06: Review Report Artifact and Audit

**Rule**: The full review output (all findings across all rounds, with severities and resolutions) MUST be saved to `aidlc-docs/construction/{unit-name}/code/review-report.md`. The orchestrator (the main workflow session) — NOT the reviewer or fix subagents — writes the audit summary to `aidlc-docs/audit.md`: the finding counts by severity, the number of fix rounds, and the final disposition (all resolved / escalated).

Subagents (reviewer and fix) MUST NOT write to `aidlc-docs/audit.md` or `aidlc-docs/aidlc-state.md`. Shared state is written only by the orchestrator.

**Verification**:
- A review-report.md exists for the unit capturing all findings and resolutions
- The audit.md entry was written by the orchestrator, summarizing counts, rounds, and disposition
- No subagent wrote to audit.md or aidlc-state.md

---

## Enforcement Integration

These rules apply to the following AI-DLC stage:

| Stage | Applicable Rules | Enforcement |
|---|---|---|
| Code Generation (Generation) | CR-01 through CR-06 | The reviewer runs after code generation and before the completion message; Critical findings block until resolved or escalated |

At the Code Generation stage:
- Run the reviewer subagent (CR-01) after PART 2 generation completes, before the completion message
- Classify findings by severity (CR-03) and block on Critical (CR-04)
- Resolve Critical findings via the bounded auto-fix loop (CR-05), escalating after 2 rounds
- Save the review report and write the audit summary from the orchestrator (CR-06)
- Include a "Code Review" section in the completion message summarizing Major/Minor findings for user decision

---

## Interaction with Other Extensions

- **TDD**: When enabled, a missing red confirmation record (TDD-02) for a logic layer is a Critical finding (CR-03), and failing/missing tests are Critical.
- **Parallel Construction**: When enabled, the reviewer runs per unit inside that unit's worktree after implementation and before merge. The merge (and any conflict resolution) is performed by the orchestrator only after the unit's review is clean. The bounded auto-fix loop runs within the unit's worktree.
- **Security Baseline / PBT**: Their blocking findings are evaluated at their own stages per their Enforcement Integration; the reviewer additionally treats an un-remediated blocking finding from an enabled extension as a Critical review finding if it appears in generated code.
