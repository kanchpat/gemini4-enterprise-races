# Contributing to `gemini4-enterprise-races`

Thanks for helping keep these enterprise tests honest and reproducible.

## What we welcome

- **Reruns on your own project.** Open an issue with your `results/summary.json` (region, date and backend). Different numbers are useful, not wrong.
- **Answer-key corrections.** Every key value should trace to a primary source (SEC filing, XBRL fact or call timestamp). Include the source line.
- **New enterprise workflows.** Propose the use case, the owner (for example, controllership), the public data you'd use and how it's graded by script. Open an issue first so we can agree on scope.
- **Harness fixes.** Bug fixes, clearer errors, or support for another backend.

## Ground rules

- **Grade by script, never by eye.** Every new test needs a deterministic grader and an answer key in `data/`.
- **Publish ties and losses.** Don't remove results because they're unflattering.
- **Disclose grading changes.** If you change a grader after seeing results, note it in [docs/approach.md](docs/approach.md#6-how-the-approach-evolved-and-why).
- **Google models only.** This series compares Gemini models with each other.
- **No secrets or private data.** Never commit API keys, project IDs, tokens or non-public documents.

## How to make changes

> `docs/index.html` is generated from `site/src/` by `scripts/build_site.py`. Don't hand-edit it; the next build overwrites your edits.

1. Fork and clone (Python 3.10+, standard library only):
   ```bash
   git clone https://github.com/kanchpat/gemini4-enterprise-races.git
   cd gemini4-enterprise-races
   ```
2. Make your change in `races/`, `data/`, `site/src/` or `docs/approach.md`.
3. If results changed, regenerate the summary and the site:
   ```bash
   python3 scripts/summarize.py --print
   python3 scripts/build_site.py
   python3 -m http.server 8000 --directory docs
   ```
4. Open http://localhost:8000 and check the tables match `results/summary.json`.
5. Commit the source change, regenerated `results/summary.json` and `docs/index.html`, then open a pull request against `main`.

## License

By submitting a pull request, you agree that your contribution is licensed under the [Apache License 2.0](LICENSE).
