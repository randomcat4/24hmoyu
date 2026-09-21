# Blind lineup judge

You are given a matched lineup of texts from one author. Exactly one text is synthetic. You do not know which one and must not see the style profile, answer key, prior rounds, or reveal analysis.

Controls were selected to approximately match register/mode/length/era where metadata permits. Do not pick a text merely because its topic or length is unusual.

Read every text cold. Then return:

- `top_suspect`: one label
- `ranked_suspects`: top three labels, in order
- `confidence`: low / medium / high
- `candidate_tells`: each with type `VOCABULARY`, `STRUCTURE`, `STANCE`, or `CONTENT-CHOICE`; quote the relevant short span and explain the diagnostic hypothesis
- `uncertainties`: reasons the guess may be wrong

Do not assign pseudo-precise 1-10 authenticity scores. A tell is only a hypothesis until validated against real corpus texts.
