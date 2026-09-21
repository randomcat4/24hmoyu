# Tell validation prompt

Validate one discriminator/reveal hypothesis against real corpus evidence before it is allowed to modify the style profile.

Inputs include the tell, its direction (`PRESENCE` or `ABSENCE`), its suspected scope, and a representative sample of real texts. Prefer matched texts from the same mode/register plus some cross-mode controls.

For each tell return:

- `verdict`: VALIDATED / DISCARDED / UNCERTAIN
- `direction`: PRESENCE / ABSENCE
- `scope`: global / register / mode / era / unknown
- `support_count`: number of real documents supporting the diagnostic claim
- `counterexample_count`: number contradicting it
- `evidence`: short observations with document IDs
- `counterexamples`: explicit exceptions
- `confidence`: HARD / TENDENCY / SPECULATIVE
- `patch`: only if validated; state the smallest positive or negative mechanism to append

Rules:

- For mechanically measurable tells, prefer the supplied quantitative distribution over subjective reading.
- One counterexample does not automatically falsify a tendency; scope it correctly.
- Do not promote a finding to HARD without broad, cross-document support.
- UNCERTAIN is preferable to forcing a binary answer.
- Never penalize authentic behavior merely because a blind judge disliked it.
