# Style synthesis prompt

You receive four independent style-mining reports plus quantitative evidence from `evidence.json`.

Build two artifacts:

## 1. `style.md`

Use only these sections:

1. Voice invariants
2. Writing modes and activation conditions
3. Argument and structural moves
4. Sentence and rhythm mechanics
5. Epistemic stance and reader relationship
6. Lexical and punctuation tendencies
7. Negative space / anti-patterns
8. Adversarial findings (initially empty unless validated findings are supplied)

Every mechanism must state scope and confidence. Preserve meaningful counterexamples. Do not claim access to the author's private mental state. Write operational generative constraints, not biography or flattering adjectives.

## 2. `card.json`

Include only generator-actionable ranges and soft controls:

- sentence-length bands/distribution guidance
- paragraph-shape guidance
- perspective/pronoun balance
- hedge/booster/directive tendency
- punctuation tendency
- preferred rhetorical moves
- preferred/soft-avoid words or transitions when strongly evidenced

Do NOT copy the full forensic metrics into `card.json`. Do NOT encode exact quotas such as "4.7 em dashes per 1,000 words". Raw numbers remain in `evidence.json` for evaluation.

Before finalizing, remove any rule that could describe many unrelated authors without modification.
