# Voice generation prompt

Inputs:

- a style-free semantic seed
- `style.md`
- `card.json`
- 3-5 short exemplars matched to rhetorical slots and target mode
- optional validated adversarial findings

Write a fresh piece that expresses the seed content in the target author's register.

Priorities:

1. Preserve the seed's facts and meaning.
2. Follow the mechanisms in `style.md`, respecting mode/scope distinctions.
3. Use `card.json` as soft range guidance, never as a quota checklist.
4. Use exemplars as rhythm/move demonstrations, never as content donors.
5. Prefer natural variation over mechanically satisfying every listed feature.

Do not copy exemplar topics, anecdotes, unusual phrases, or ordering. Do not mention the style instructions. Do not invent autobiographical details. Do not optimize for generic "human" writing; optimize for the target author's evidenced distribution.

When used for evaluation, generate multiple independent candidates from the same seed rather than polishing one candidate indefinitely.
