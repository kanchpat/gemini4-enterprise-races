# Approach and reasoning

*Gemini for Real-Life Enterprise Use Cases · Part 1: Right Model, Right Job*

How we tested Gemini 4 Hydrogen, Gemini 4 Neon and Gemini 3.8 Flash on enterprise work, why we made each choice, and what changed along the way.

> *Independent practitioner evaluation by Kanchana Patlolla. Not an official Google benchmark. Results apply to these tasks only.*

---

## 1. The question

Published benchmarks rank models on intelligence. Enterprise architects ask a narrower question:

> **For a given job, which model gives the right answer at a speed and cost I can run thousands of times a day?**

So we measured three things per task: **accuracy** (graded by script), **wall-clock time**, and **cost per task**. We did not try to crown a "best model".

---

## 2. Design principles and why

| Principle | What we did | Why |
|---|---|---|
| **Real enterprise work** | Finance analysis, earnings-call intake, and a filing audit | Architects need to see their own workloads, not puzzles |
| **Public data only** | Alphabet's Q3 2026 Form 10-Q and its earnings call recording | Anyone can rerun it. No customer data, no approvals needed |
| **Machine-checkable answers** | Every answer is a number (or `null`), compared by script to an answer key | Removes grader bias and model-as-judge disputes, and lets us publish the same day |
| **Answer keys from primary sources** | Filing questions are keyed to the 10-Q's own inline XBRL data | XBRL is the SEC's machine-readable version of the filing: the most defensible source of truth |
| **Trap questions** | Each test has at least one question whose only correct answer is "not in the source" | Measures whether a model makes things up, which is the costly enterprise failure |
| **Same conditions for every model** | Identical document, prompt, system instruction, JSON output mode and grading | Differences come from the model, not the setup |
| **Repeat runs** | 5 runs per model per test, medians reported, ranges kept | Model output and latency vary run to run |
| **Report ties and losses** | Every result is published, including where an older or cheaper model won | An honest loss is what makes the wins credible |
| **Google vs Google only** | Neon, Hydrogen and the previous generation, 3.8 Flash | Scope decision: a routing guide within one model family, with no competitive claims |

---

## 3. Models and settings

| Setup | Model ID | Thinking level | Why it's included |
|---|---|---|---|
| Neon | `gemini-4-neon` | high (default) | The model we wanted to showcase |
| Hydrogen | `gemini-4-hydrogen` | high (default) | The everyday Gemini 4 model |
| Hydrogen, low | `gemini-4-hydrogen` | low | Shows the speed/cost dial within one model |
| 3.8 Flash | `gemini-3.8-flash` | high | Previous-generation baseline that many enterprises run today |
| Neon, extra-high | `gemini-4-neon` | xhigh | Hard tasks only, to test whether more thinking pays off |

**Not included:**
- **Gemini 4 Carbon:** not yet available to businesses (cyber defenders only, via the Fairwind Program).
- **Other vendors' models:** out of scope by decision (see §2).

**Calls:** Vertex AI `generateContent`, global endpoint, one call per task. Output in JSON mode. Output cap 32,768 tokens for tests 1–2, and 65,536 for the hard tests. No context caching, batch mode or tools.

---

## 4. The tests

### Test 1: Analyst (filing extraction and simple math)
- **Input:** the full 10-Q converted from SEC HTML to plain text, with table cells kept as `|`-separated rows (about 61k tokens).
- **Task:** 25 questions: 13 direct figures, 11 computed ratios and growth rates, and 1 trap (Gemini app users, which isn't in a 10-Q).
- **Key:** every answer comes from the filing's XBRL facts, e.g. `Revenues`, `OperatingIncomeLoss` × Google Cloud segment, `RevenueRemainingPerformanceObligation`.
- **Tolerance:** amounts within 0.5%, percentages within 0.15 points.
- **Why:** the most common enterprise document task, reading a long filing and computing from it.

### Test 2: Intake (earnings-call video, no transcript)
- **Input:** the public YouTube recording of the Q3 2026 earnings call, prepared remarks only (0:00–33:46). Low media resolution, about 185k–213k tokens.
- **Task:** 20 figures as spoken on the call.
- **Key:**
  - 11 answers cross-checked against the 10-Q and the earnings release.
  - 8 are said only on the call (e.g. CapEx guidance, Waymo cities, the 24-month backlog share). Several of these are also corroborated by press coverage and the CEO remarks on blog.google.
  - 1 trap: Q4 revenue guidance, which Alphabet doesn't give.
- **How we located the call-only figures:** a reference transcript made with Gemini 4 Carbon, which isn't one of the models under test. See limitations, §8.
- **Tolerance:** within 1% of the stated figure.
- **Why:** turning recorded meetings and calls into structured facts is a top multimodal enterprise use case.

### Test 3: Audit (find planted errors)
- **Input:** the same 10-Q with **six inconsistencies planted** by changing one number each:

| ID | Where | Planted change | How it can be caught |
|---|---|---|---|
| e1 | Revenue by segment table | Cloud revenue 30,709 → 31,709 | Segments no longer sum to total revenues, and it differs from other tables |
| e2 | MD&A summary | Cloud growth 103% → 113% | Doesn't match 15,157 → 30,709 |
| e3 | MD&A operating income table | Change 9,348 → 9,848 | 40,576 − 31,228 ≠ 9,848 |
| e4 | MD&A segment operating income | Cloud operating income 11,121 → 12,121 | Rows no longer sum to 40,576 |
| e5 | Backlog note | Total backlog 567.7B → 557.7B | Total is now smaller than its Cloud portion (560.8B) |
| e6 | MD&A summary | Cost-of-revenues growth 24% → 34% | Doesn't match 41,369 → 51,419 |

- **Task:** list every inconsistency provable from the document, with the wrong value. False flags are discouraged in the prompt.
- **Grading:** a finding counts if its wrong value matches a planted value (within 0.5%, with unit-scale tolerance). Anything else is a false flag.
- **Why:** checking work is where the cost of a miss is highest, and where we expected stronger reasoning to show.

### Test 4: Ladder (multi-step reasoning)
- **Input:** the unmodified 10-Q.
- **Task:** 16 questions that combine figures across sections, plus 2 traps:
  - Implied first-half figures (nine months minus Q3).
  - Margin changes in percentage points.
  - Reconciliations, e.g. segment profit vs total.
  - A "what if other income were zero" net income.
  - Traps: Q2 Cloud operating income alone, which can't be derived from the filing, and Cloud revenue excluding TPU sales, which isn't disclosed.
- **Key:** computed from the same XBRL and filing figures, with formulas recorded in the key.
- **Why:** to test whether multi-step reasoning separates the models where extraction didn't.

---

## 5. Measurement

- **Accuracy:** share of questions answered correctly. A missing answer or a value outside tolerance is wrong. A trap is correct only if answered `null`.
- **Time:** wall-clock seconds per request, measured by the harness from one machine on one day (2026-11-20). Includes network. The configurations ran side by side; runs within a configuration ran one after another.
- **Cost:**

  $$\text{cost} = \frac{\text{input tokens} \times \text{input price} + (\text{output} + \text{thinking tokens}) \times \text{output price}}{10^6}$$

  Token counts come from the API's usage metadata. Prices are public list prices per 1M tokens, checked 2026-11-20:

| Model | Input | Output (incl. thinking) |
|---|---|---|
| Gemini 4 Neon | \$3.00 | \$15.00 |
| Gemini 4 Hydrogen | \$1.50 | \$7.50 |
| Gemini 3.8 Flash | \$0.75 promo (\$1.50 from 2027-01-01) | \$3.75 promo (\$7.50 from 2027-01-01) |

  We don't apply caching or batch discounts, though both would lower real costs.

---

## 6. How the approach evolved (and why)

We changed course twice. Both changes are documented here because they shape how the results should be read.

| Step | What happened | What we decided | Reasoning |
|---|---|---|---|
| 1. Plan | Three races: analyst, earnings-call intake, and R→Python modernization | Start with the two document races, which can be graded fastest | Same-day publishing needs automatic grading |
| 2. First results | **Every model scored 100% on every run** of tests 1 and 2 | Report the tie. Treat extraction as the "route it cheap" evidence | Extraction is a solved task for this generation. Hiding the tie would mislead |
| 3. "How could Neon shine?" | The easy tests can't show any accuracy gap | Add harder rungs (audit, ladder), defined by **how the task is built** (steps, planted errors), not by which model failed | Avoids tuning the test until a chosen model wins |
| 4. Pilot (1 run) | Ladder: 100% for all again. Audit: Hydrogen-high and Neon 6/6, Hydrogen-low 5/6, 3.8 Flash 4/6. Neon extra-high returned nothing | The audit becomes the test that separates. Confirm with 5 runs | First real accuracy gap, between generations, not between Neon and Hydrogen |
| 5a. Audit, 5 runs | Hydrogen-high and Neon 30/30, Hydrogen-low 28/30, 3.8 Flash 23/30; zero false flags for all. The part-vs-whole backlog error (e5) was missed most | Publish the 5-run figures | Confirms the pilot pattern |
| 5. Grading fix after the pilot | Two models flagged the Cloud backlog (560.8B) instead of the planted total (557.7B) for error e5 | Credit either side of a part-vs-whole contradiction (also for e1 and e4) | The document alone can't say which side is wrong. Applied to every model, and disclosed here |
| 6. Neon extra-high | Used all 65,536 output tokens on thinking and returned no answer | Excluded from published results. Rerun later with a higher cap | Our cap caused it, not the model |

**Where Neon stands:** in our document tests Neon matched Hydrogen at high thinking on accuracy, at 2.5–3× the cost. Neon's published lead is in long-running agent and coding work: #1 on the Artificial Analysis Coding Agent Index and on Zapier AutomationBench, per the [launch post](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-neon/). We haven't tested that yet. The planned follow-up is an agentic R→Python modernization race graded against real R output.

---

## 7. What the results support (and what they don't)

**Supported:**
- On filing and earnings-call extraction, all four setups were equally accurate here. Choose by latency and cost.
- On the planted-error audit, the Gemini 4 models caught errors that 3.8 Flash missed (5 runs: Hydrogen-high and Neon 100%, Hydrogen-low 93%, 3.8 Flash 77%).
- Turning up Hydrogen's thinking level bought accuracy on the audit at modest cost.

**Not supported:**
- That Neon is no better than Hydrogen in general. We didn't test its strongest area.
- Any claim outside these tasks, this company's filings, or this date's latency.
- Any comparison with other vendors' models.

---

## 8. Limitations and threats to validity

- **Small scope:** four tests on one company's filings. This shows a pattern; it isn't a benchmark.
- **Ceiling effects:** tests 1, 2 and 4 hit 100% for every model, so they can't rank accuracy.
- **Call-only answers were located with a model transcript** (Gemini 4 Carbon). Each of those 8 figures should be checked by listening to the recording before publishing. Several are also corroborated by press coverage and blog.google.
- **Grading rule changed after the pilot** (§6, step 5). The rule is symmetric and applies to all models.
- **Latency depends on time, region and load.** Treat times as relative within one run.
- **Pricing:** 3.8 Flash's promotional price flatters its cost until 2026-12-31.
- **Planted errors were written by the author.** Real filing errors may be subtler.
- **Data contamination:** the filing and call are public from late October 2026. Answers depend on the provided input, and the trap questions check for outside knowledge, but we can't rule out that a model has seen the material.

---

## 9. Reproduce it

```bash
git clone https://github.com/kanchpat/gemini4-enterprise-races.git
cd gemini4-enterprise-races
export GEMINI_API_KEY=...            # or GOOGLE_CLOUD_PROJECT=<your-project> (Vertex AI)
python3 races/race1_analyst.py --runs 5
python3 races/race2_intake.py  --runs 5
python3 races/race_hard.py --task audit  --runs 5
python3 races/race_hard.py --task ladder --runs 5
```

Raw per-run results (answers, tokens, time and cost) are written to `results/*.jsonl`. Answer keys and their sources are in `data/`.

---

## 10. Sources
- [Introducing Gemini 4 Neon](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-neon/), [Hydrogen](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/), [Carbon](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-carbon/) (blog.google)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) (checked 2026-11-20)
- [Alphabet Form 10-Q, Q3 2026](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000084/goog-20260930.htm) and its [XBRL instance](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000084/goog-20260930_htm.xml) (SEC EDGAR)
- [Alphabet Q3 2026 earnings release, Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000080/googexhibit991q32026.htm)
- [Alphabet Q3 2026 earnings call recording](https://www.youtube.com/watch?v=X9mmCagxJTo) (YouTube)
