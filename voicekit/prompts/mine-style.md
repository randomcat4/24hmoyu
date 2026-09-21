# Style mining prompt

You are extracting operational writing evidence from a real author's corpus. Work from the supplied texts directly, not from a prior summary.

Run exactly one lens per invocation. Valid lenses:

1. `rhythm-syntax`: sentence/paragraph construction, pacing, punctuation function, recurring syntactic shapes.
2. `argument-structure`: openings, progression, pivots, evidence placement, concessions, endings, repeated macro moves.
3. `stance-reader`: hedging/assertion, authority, assumed reader knowledge, direct address, emotional distance.
4. `variation-negative-space`: registers/modes, what changes between them, stable invariants, counterexamples, conspicuous absences.

For every claimed pattern, return:

- `claim`: a falsifiable description, not an adjective.
- `status`: `OBSERVED`, `INFERRED`, or `SPECULATIVE`.
- `confidence`: `HARD`, `TENDENCY`, or `SPECULATIVE`.
- `scope`: global, register-specific, mode-specific, era-specific, or unknown.
- `evidence`: multiple short corpus excerpts and/or counts.
- `counterexamples`: evidence that limits the claim.
- `generation_effect`: what concrete writing decision would change if the claim is true.

Rules:

- Do not write personality fan-fiction. Infer hidden cognition only when text provides direct evidence; otherwise mark it SPECULATIVE.
- Preserve contradictions instead of smoothing them away.
- Do not treat generic good-writing advice as an author mechanism.
- Distinguish a surface tic from the function it performs.
- Prefer distributions and ranges over point targets.
- Do not propose fixes or generate prose yet.
