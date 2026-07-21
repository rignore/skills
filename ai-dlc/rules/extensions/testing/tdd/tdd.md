# Test-Driven Development Rules

## Overview

These test-driven development (TDD) rules are cross-cutting constraints that govern the **Code Generation** stage of the CONSTRUCTION phase. They enforce a red-green-refactor cycle: a test is written and executed to confirm it fails (red) before any implementation exists, the minimal implementation is written to make it pass (green), and the code is then cleaned up while the test stays green (refactor).

TDD changes the *order* of the existing Code Generation steps. The default plan in `construction/code-generation.md` sequences each layer as "Generation → Unit Testing" (implement first, test after). When this extension is enabled, that ordering is replaced by "Test Writing → Implementation → Refactor" for every layer that produces testable logic.

**Enforcement**: At the Code Generation stage (both Planning and Generation parts), the model MUST verify compliance with these rules before presenting the stage completion message to the user.

### Blocking TDD Finding Behavior

A **blocking TDD finding** means:
1. The finding MUST be listed in the stage completion message under a "TDD Findings" section with the TDD rule ID and description
2. The stage MUST NOT present the "Continue to Next Stage" option until all blocking findings are resolved
3. The model MUST present only the "Request Changes" option with a clear explanation of what needs to change
4. The finding MUST be logged in `aidlc-docs/audit.md` with the TDD rule ID, description, and stage context

If a TDD rule is not applicable to the current unit (e.g., TDD-01 for a unit that only produces database migration scripts and configuration), mark it as **N/A** in the compliance summary — this is not a blocking finding.

### Default Enforcement

All rules in this document are **blocking** by default. If any rule's verification criteria are not met, it is a blocking TDD finding — follow the blocking finding behavior defined above.

### Verification Criteria Format

Verification items in this document are plain bullet points describing compliance checks. They are distinct from the `- [ ]` / `- [x]` progress-tracking checkboxes used in stage plan files. Each item should be evaluated as compliant or non-compliant during review.

---

## Rule TDD-01: Test-First Step Ordering in the Code Generation Plan

**Rule**: When creating the unit code generation plan (`construction/code-generation.md` PART 1), every layer that produces testable logic MUST be planned as three ordered steps instead of the default two-step "Generation → Unit Testing" sequence:

1. **`{Layer} Test Writing`** — Derive test cases from the unit's story acceptance criteria (see TDD-06), write the tests, and run them to confirm they fail because the implementation does not yet exist (red — see TDD-02).
2. **`{Layer} Implementation`** — Write the minimal implementation that makes the failing tests pass, and run the tests to confirm they now pass (green — see TDD-03).
3. **`{Layer} Refactor`** — Improve the implementation while keeping tests green, re-running after changes (see TDD-04).

This applies to every layer in the default plan that contains logic: Business Logic, API Layer, Repository Layer (data transformation logic), and Frontend Components (component behavior). The three steps replace that layer's original "Generation" and "Unit Testing" steps.

**Verification**:
- Every logic-bearing layer in the code generation plan has explicit Test Writing, Implementation, and Refactor steps in that order
- No layer has an Implementation step that precedes its Test Writing step
- No layer has an Implementation step without a preceding Test Writing step for the same layer
- Each step carries its own progress checkbox `[ ]` per the plan-level checkbox enforcement rules

---

## Rule TDD-02: Red Confirmation Before Implementation

**Rule**: For each layer, the tests MUST be executed and observed to fail *before* any implementation code for that layer is written. "Written but not run" is a violation — the failure must be confirmed by actually running the test command. The failure must be for the right reason: the test fails because the behavior is unimplemented, not because of a syntax error or a broken test harness.

**Reaching a genuine red (stub-first)**: If the module/class under test does not exist at all, running the tests raises an import/collection error — which is a broken-harness failure, NOT the behavioral (assertion) failure this rule requires. To reach a genuine red, first create a minimal **stub** of the unit under test: the functions/classes exist with the correct signatures but return placeholder values (e.g. `""`, `0`, `None`) or raise `NotImplementedError`. Run the tests against the stub so they fail on assertions (the behavior is wrong), not on import. Then replace the stub with the real implementation to reach green (TDD-03). The stub is scaffolding for the red step, not an implementation.

A short summary of the red confirmation (the test command, the count of failing tests, and the failure reason) MUST be recorded in the unit's code summary document under `aidlc-docs/construction/{unit-name}/code/` so the red-before-green sequence is auditable.

**Verification**:
- A red confirmation record exists for each layer, capturing the test command and the observed failure
- The recorded failure reason is "behavior not implemented" (assertion/expectation failure), not a compilation or harness error
- No implementation file for a layer was created or modified before that layer's red confirmation was recorded
- The red confirmation precedes the green confirmation (TDD-03) in the recorded sequence

---

## Rule TDD-03: Green Confirmation After Implementation

**Rule**: After the minimal implementation for a layer is written, the same tests MUST be executed and observed to pass (green). The implementation MUST be the minimal code that satisfies the tests — not speculative functionality beyond what the tests and acceptance criteria require.

The green confirmation (test command and pass count) MUST be recorded in the unit's code summary document.

**Verification**:
- A green confirmation record exists for each layer, showing all of that layer's tests passing
- The green confirmation follows the corresponding red confirmation (TDD-02)
- The implementation does not introduce behavior beyond what the tests and acceptance criteria require (no speculative, untested code paths)

---

## Rule TDD-04: Refactor Under Green

**Rule**: Any refactoring (renaming, extraction, de-duplication, structural cleanup) performed after green MUST keep all tests passing. Tests MUST be re-run after refactoring to reconfirm green. Refactoring MUST NOT change the observable behavior asserted by the tests; if behavior needs to change, that requires a new or modified test (returning to TDD-02), not a silent refactor.

**Verification**:
- Where refactoring occurred, a post-refactor test run confirms tests remain green
- No behavioral change was introduced under the guise of refactoring without a corresponding test change
- If no refactoring was needed for a layer, the Refactor step is explicitly marked N/A with a brief rationale (not silently skipped)

---

## Rule TDD-05: Scope Exclusions

**Rule**: TDD applies to artifacts that carry testable behavior. The following artifact types are OUT of scope and MUST NOT block on TDD rules — mark them N/A:
- Database migration scripts (DDL/DML with no branching logic)
- Deployment artifacts (Dockerfiles, IaC templates, CI configuration)
- Static configuration files
- Documentation (README, API docs)
- Pure declarative schema definitions with no logic

If a unit consists *only* of excluded artifacts, all TDD rules for that unit are N/A and the unit proceeds under the default (non-TDD) generation flow.

**Verification**:
- Excluded artifact types are marked N/A, not forced through a red-green cycle
- Logic embedded inside otherwise-excluded artifacts (e.g., a migration containing conditional data transformation) is NOT excluded — it is tested
- Units consisting only of excluded artifacts are documented as such in the code generation plan

---

## Rule TDD-06: Tests Derived from Acceptance Criteria

**Rule**: Test cases MUST be traceable to the unit's story acceptance criteria and functional design. Each acceptance criterion for a story assigned to the unit MUST be covered by at least one test written during the Test Writing step. Tests MUST NOT be written to match a pre-existing implementation (there is none at red time, by construction), and MUST NOT be weakened to pass trivially.

**Verification**:
- Every acceptance criterion for the unit's assigned stories maps to at least one test
- Tests assert on the criterion's expected behavior, not on incidental implementation details
- No test is a tautology (e.g., asserting a constant equals itself) or is disabled/skipped to force a pass
- Story traceability in the plan references the tests that cover each story

---

## Rule TDD-07: Relationship to Build and Test

**Rule**: Because unit tests are written and confirmed green during Code Generation under this extension, the Build and Test stage MUST treat unit tests as already generated and passing, and focus its own execution on cross-unit concerns: integration tests, contract tests, and end-to-end tests. Build and Test MUST re-run the full unit test suite as a regression gate, but the *authoring* of unit tests is complete before Build and Test begins.

**Verification**:
- The Build and Test instructions reference the unit tests as already-authored-and-passing (not to be written during Build and Test)
- Build and Test re-runs the unit suite as a regression check
- Integration, contract, and e2e tests are the net-new test authoring done at Build and Test

---

## Enforcement Integration

These rules apply to the following AI-DLC stages:

| Stage | Applicable Rules | Enforcement |
|---|---|---|
| Code Generation (Planning) | TDD-01, TDD-05, TDD-06 | The code generation plan MUST sequence test-first steps for logic layers and mark exclusions |
| Code Generation (Generation) | TDD-02, TDD-03, TDD-04, TDD-06 | Generated work MUST record red-before-green per layer with test-run evidence |
| Build and Test | TDD-07 | Build and Test instructions MUST treat unit tests as authored-and-passing and re-run them as regression |

At each applicable stage:
- Evaluate all applicable TDD rule verification criteria against the artifacts produced
- Include a "TDD Compliance" section in the stage completion summary listing each rule as compliant, non-compliant, or N/A
- If any applicable rule is non-compliant, this is a blocking TDD finding — follow the blocking finding behavior defined in the Overview
- Include TDD references (red/green confirmation records) in the unit code summary documents

---

## Interaction with Other Extensions

- **Property-Based Testing (PBT)**: If both extensions are enabled, property-based tests are authored within the Test Writing step alongside example-based tests. The red confirmation (TDD-02) applies to both: property tests must also be observed to fail before implementation. PBT-10 (complementary testing strategy) governs the split between example-based and property-based tests.
- **Subagent Code Review**: If the subagent-code-review extension is enabled, the absence of a red confirmation record (TDD-02) for a logic layer is a **Critical** review finding, because it means the test-first sequence cannot be verified from the artifacts.
