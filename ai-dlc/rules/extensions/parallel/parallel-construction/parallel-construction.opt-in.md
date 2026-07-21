# Parallel Construction — Opt-In

**Extension**: Parallel Construction

## Opt-In Prompt

The following question is automatically included in the Requirements Analysis clarifying questions when this extension is loaded:

```markdown
## Question: Parallel Construction
Should independent units be built in parallel, using a dependency-ordered wave schedule and frozen inter-unit interface contracts?

A) Yes — Units Generation produces a wave schedule (units topologically ordered by dependency) and interface contracts (the boundary APIs each unit must honor). During CONSTRUCTION, units in the same wave (mutually independent) are implemented concurrently by separate subagents in isolated git worktrees, then merged in dependency order. Approval gates are batched per wave (three gates per wave instead of up to six per unit): fewer round-trips, but each review covers all units in the wave. Requires a git repository; without one, it falls back to sequential construction (the planning artifacts are still produced).
B) No — sequential construction with the default per-unit loop, no wave/contract planning.
X) Other (please describe after [Answer]: tag below)

[Answer]: 
```
