# Subagent Code Review — Opt-In

**Extension**: Subagent Code Review

## Opt-In Prompt

The following question is automatically included in the Requirements Analysis clarifying questions when this extension is loaded:

```markdown
## Question: Subagent Code Review Extension
Should an isolated subagent review each unit's generated code against the approved plan before completion is presented?

A) Yes — after each unit's code is generated, an isolated reviewer (with no access to the generation conversation) checks the code against the approved plan and interface contracts. Critical findings block completion and are auto-fixed for up to 2 rounds, then escalated to you. Recommended.
B) No — present generated code directly for your review without an intermediate subagent review.
X) Other (please describe after [Answer]: tag below)

[Answer]: 
```
