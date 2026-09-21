# VoiceKit

A small, portable toolkit for building and testing an author-voice profile without fine-tuning.

This directory is intentionally a self-contained subproject. It does **not** import `twentyfour_myself`, read the 24hmoyu ledger/corpus schema, or depend on any host-application model. It can later be moved to its own repository as-is.

## What it keeps from prior work

VoiceKit deliberately combines only the high-value pieces of several public approaches:

- evidence / operative-style / exemplar separation;
- neutral content seeds so content and style are evaluated separately;
- document-level stylometry and real-vs-real baselines;
- matched 7-real + 1-synthetic blind lineups;
- blind judgment separated from post-reveal analysis;
- discriminator tells validated against real corpus evidence before profile updates.

It deliberately omits LoRA/GRPO, generic AI-detector optimization, generic "humanizer" rules, borrowed secondary voices, and host-application memory/ledger integration.

## Artifact boundary

A built author profile is expected to look like:

```text
profile/
  evidence.json              # raw/document-level metrics; builder + evaluator only
  style.md                   # compact operational mechanisms for the generator
  card.json                  # small set of actionable ranges / soft controls
  adversarial-findings.md    # only validated tells; periodically compacted
  exemplars/
    opener/
    development/
    transition/
    qualification/
    ending/
```

The generator should not receive all of `evidence.json`. Raw metrics are for evaluation; the writer consumes `style.md`, `card.json`, a few matched exemplars, and validated findings.

## Corpus split

Before style mining, freeze three disjoint sets:

- `profile`: used to build the profile;
- `dev`: used for adversarial iteration and tell validation;
- `final`: untouched until final evaluation.

```bash
voicekit split ./my-writing --out split.json
```

The final set should not leak into prompts, exemplar curation, tell validation, or iterative edits.

## Quantitative profile

The profiler is standard-library only. It retains document-level metrics instead of collapsing everything into one author mean.

```bash
voicekit measure corpus/profile/*.md --out profile/evidence.json
```

Measured families include sentence/paragraph distributions, punctuation, function words, stance/pronouns, transition position, light rhetorical-move heuristics, paragraph cadence, syntax texture, contractions, and repetition.

To inspect a candidate against within-author variation:

```bash
voicekit distance profile/evidence.json candidate.md
```

The reported percentile is a **distance percentile**, not an authorship probability. High means the candidate is farther from real texts than more of the author's own texts.

## Blind lineup

```bash
voicekit lineup \
  --fake candidate.md \
  --real dev/*.md \
  --out lineup.md \
  --key key.json
```

The library API supports `mode`, `register`, and `era` metadata through `voicekit.lineup.Document` and selects controls by a matching cost before shuffling. The simple CLI, which only sees files, matches primarily on length.

Use `prompts/blind-judge.md` for the cold judgment, reveal the key only after the guess is recorded, then use `prompts/reveal-analysis.md` and `prompts/validate-tell.md`.

## Suggested build loop

```text
profile corpus
  -> measure + 4 independent mining lenses
  -> synthesize style.md/card.json + curate exemplars
  -> neutral seed from dev/final source
  -> generate fresh candidate(s)
  -> quantitative distance + repetition checks
  -> matched blind lineup
  -> reveal analysis
  -> validate tells against real dev texts
  -> append only validated findings
  -> periodically resynthesize/compact the profile
```

Do not use "two consecutive misses" as a convergence criterion. Run multiple independent lineups and report raw hit counts alongside same-content A/B tests and quantitative distance distributions.

## Development

```bash
cd voicekit
python -m pip install -e '.[dev]'
pytest
```

Runtime dependencies: none beyond Python 3.11+.
