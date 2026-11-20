# Verification runs

Independent reruns of the Part 1 tests by the author, made after the published 5-run results, using `scripts/run_all.py`. Each row in the `.jsonl` files stores the API's receipt fields (`extra.response_id`, `extra.model_version`, `extra.create_time`).

## 2026-11-20T2212Z (1 run per setup, Vertex AI `global`)

Run by Kanchana Patlolla from the command line and screen-recorded. Compared with the published medians in [../summary.json](../summary.json):

| Test | Setup | Accuracy (this run) | Published | Time (this run) | Published median [range] |
|---|---|---|---|---|---|
| Analyst | Hydrogen low | 100% | 100% | 19 s | 18 s [16–23] |
| Analyst | Hydrogen high | 100% | 100% | 21 s | 25 s [23–26] |
| Analyst | 3.8 Flash | 100% | 100% | 24 s | 38 s [31–45] |
| Analyst | Neon high | 100% | 100% | 59 s | 61 s [59–75] |
| Intake | 3.8 Flash | 100% | 100% | 24 s | 31 s [27–35] |
| Intake | Hydrogen low | 100% | 100% | 34 s | 39 s [31–77] |
| Intake | Hydrogen high | 100% | 100% | 35 s | 40 s [35–52] |
| Intake | Neon high | 100% | 100% | **85 s** | 33 s [30–50] |
| Audit | Hydrogen low | 5/6 (missed e5) | 28/30 | 28 s | 30 s [23–50] |
| Audit | Hydrogen high | 6/6 | 30/30 | 183 s | 204 s [192–217] |
| Audit | 3.8 Flash | 5/6 (missed e5) | 23/30 | 274 s | 268 s [235–350] |
| Audit | Neon high | 6/6 | 30/30 | 359 s | 420 s [395–461] |

**What it shows**

- Every accuracy result matches the published pattern. Hydrogen high and Neon found all 6 planted errors again, with zero false flags.
- e5 (a backlog total smaller than its Cloud part) is again the error that Hydrogen low and 3.8 Flash miss. Flash's 5/6 is at the better end of its published runs.
- Costs are within a few cents of the published medians; token counts barely move between runs.
- Times mostly fall inside or below the published ranges. One outlier: Neon on the call-intake test took 85 s (published 30–50 s). Latency depends on load; it doesn't change the routing advice.
