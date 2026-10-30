# Contributing to APFEA

Thank you for your interest. This repository is public and read-only for
most visitors: anyone may view, clone, fork, and open issues. Only the
maintainer can merge. Contributions arrive as pull requests from a fork.

## Before you start

- Read `README.md` first, especially the core idea (design to anticipated
  VTs, pre-tape-out corner DOE) and the business-model rule:
  **foundry mode** treats SRAM as a foundry-fixed macro (constraint only,
  CMOS-side remedy); **IDM mode** may co-optimize CMOS and SRAM.
- Read `TERMS.md`. By contributing you agree to those terms, including
  the defensive-publication rule: APFEA content may not be used to be
  patented.
- This is a planner-level prototype, not production EDA. The agent
  observes, attributes, and recommends; it does not actuate a fab, change
  a recipe, or make a tape-out decision. Keep it that way.

## How to contribute

1. Fork the repository and clone your fork.
2. Create a branch from `main`, e.g. `feat/estimator-refit` or
   `fix/tower-report`.
3. Make a small, focused change: one idea per pull request.
4. Run the full test suite and the demo commands before you open the PR:

```bash
python3 -m unittest discover -s tests -v
python3 -m apfea run
python3 -m apfea agent
```

5. Open a pull request against `main` from your fork. Describe what
   changed, why, and what the tests show. Link any related issue.
6. The maintainer reviews, requests changes if needed, and merges.
   Branch protection requires one approval and a passing `tests` check.

Direct pushes to `main` are not open to contributors, even though the
repository is public.

## Ground rules

- **Standard library only.** No new dependencies without discussion in
  an issue first.
- **Phenomenology as data where possible.** Shift rules belong in
  `config/shift_rules.json`, not hard-coded in a new place.
- **Synthetic demo data only.** Do not submit real PDK extracts, real
  silicon data, customer chip profiles, or anything under NDA. Demo
  data in `data/` is synthetic and must stay that way.
- **Keep generated reports in sync.** If you change the code that
  produces a demo report, regenerate that report in the same PR.
- **Do not widen the agent's authority.** No code that talks to fab
  equipment, changes a process recipe, or commits a tape-out.

## Issues

Issues are welcome for bugs, ideas, and questions. For a bug, include
the command you ran, the output, and a reproduction using the synthetic
demo data. Feature ideas are best opened as an issue first, so the
maintainer can agree on the direction before you write code.

## Questions

Use GitHub Issues for questions about the code. The maintainer answers
there; there is no separate support channel for this repository.
