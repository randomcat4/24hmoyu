# Content-seed distillation prompt

Extract semantic content from the source text so another model can regenerate it without inheriting the source's style.

Return:

- core claims / events / facts
- supporting evidence or examples that are semantically necessary
- named entities, dates, numbers, and citations that must be preserved
- intended audience/topic context if explicitly inferable
- approximate length class and broad document mode

Critical constraints:

- Use neutral, plain prose.
- Do not preserve distinctive wording, rhythm, punctuation, metaphors, jokes, catchphrases, or sentence shapes.
- Do not preserve paragraph order, opening device, closing device, section sequence, or rhetorical progression.
- Do not summarize "how the author writes".
- Do not add facts.

The output is a semantic seed, not an outline of the original article.
