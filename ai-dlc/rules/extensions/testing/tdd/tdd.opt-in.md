# Test-Driven Development — Opt-In

**Extension**: Test-Driven Development (TDD)

## Opt-In Prompt

The following question is automatically included in the Requirements Analysis clarifying questions when this extension is loaded:

```markdown
## Question: Test-Driven Development (TDD) Extension
Should TDD be enforced during Code Generation?

A) Yes — every implementation step must be preceded by a test that is written and run to confirm it fails first, then made to pass (red-green-refactor). Recommended for business logic, API layers, and data transformations.
B) No — keep the default order (implement first, then add unit tests).
X) Other (please describe after [Answer]: tag below)

[Answer]: 
```
