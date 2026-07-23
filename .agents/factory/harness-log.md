# Harness change log (`/rf-harness`)

The cross-job ledger of every harness self-improvement **decision** — the *act* side of the
factory's self-improvement loop. `/rf-harness` appends one entry per **applied** / **rejected**
(and notable **deferred**) finding, and **reads this file before applying** so a fix that reverts a
recent change, or repeats a previously-rejected one, is flagged to the human rather than silently
re-applied (anti-thrash memory). Findings themselves live in each feature's `spec/{slug}/META.md`;
this file is the durable record of what was *done* about them.

Entry format — one section per decision, **newest at the bottom**:

```markdown
## {YYYY-MM-DD} — {slug} {F#}: {one-line title}
`decision=applied|rejected|deferred commit={sha|—} target={file}`
- **Rationale:** what changed and why it generalizes / why rejected (overfit, stale, would-weaken-a-gate) / why deferred.
```

<!-- Decisions are appended below this line by /rf-harness. -->
