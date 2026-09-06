# Experiment Log

This file records experiment runs and execution attempts for the emergent convergence project.
API keys and other secrets are intentionally excluded.

## 2026-09-06: Full battery attempt

- **Status:** Interrupted before completion; no report was written.
- **Command:** `python -u emergent_convergence_experiment.py`
- **Configuration:** 3 closed-choice tasks, 12 agents, 3 interaction rounds, 3 peers per agent, 60-agent baselines, 5 seeds, diverse and homogeneous populations.
- **What happened:** The run was still in the initial baseline phase after about 40 seconds. The configured 4.5-second request pacing implies roughly 2 or more hours for the full battery, so it was stopped to avoid leaving an impractical long-running job active.
- **Result:** No empirical result should be inferred from this attempt.

## 2026-09-06: Resource-prioritization smoke test

- **Status:** Passed end to end; report saved and pushed to GitHub.
- **Task:** Choose one initiative to prioritize: automation, employee training, or workplace flexibility.
- **Configuration:** One task, 2 agents per population, diverse and homogeneous populations, 2-agent independent baseline, 1 seed, 1 peer per agent, and 1 interaction round.
- **Bias condition:** One agent was assigned a weak preference for automation through the planted-bias setting.
- **Metrics:** Choice distribution, categorical diversity, convergence-rate fit, and amplification scores.
- **Report:** [`results/smoke_20260906_064834.json`](results/smoke_20260906_064834.json)
- **Commit:** `df93cd4 Add smoke experiment result`
- **Note:** This is a pipeline validation run, not a statistically meaningful research result. The sample is too small for substantive conclusions.

## Earlier artifact found on 2026-09-06

- **File:** [`results/smoke_20260831_143030.json`](results/smoke_20260831_143030.json)
- **Status:** Pre-existing artifact; provenance and execution configuration were not recorded.
- **Contents:** A partial resource-prioritization report for a diverse population, with a three-agent baseline and zero-valued diversity, convergence, and amplification summaries.
- **Interpretation:** Retained for traceability, but not counted as a verified run in this log.

## 2026-09-06: Resource-prioritization pilot

- **Status:** Completed and saved, but failed data-quality validation; do not interpret as an empirical result.
- **Command:** `run_full_battery(tasks=TASKS[:1], n_agents=6, n_rounds=2, k_peers=2, baseline_n=12, n_seeds=3)`
- **Configuration:** One task, 6 agents per population, diverse and homogeneous populations, 12-agent independent baselines, 3 seeds, and 2 interaction rounds.
- **Report:** [`results/pilot_20260906_071659.json`](results/pilot_20260906_071659.json)
- **Finding:** The diverse baseline contained 10 `__unmatched__` responses out of 12, and the homogeneous baseline contained 12. The model was frequently returning option letters or forms not recognized by the original normalizer.
- **Follow-up:** Added `A/B/C` option-letter normalization and regression coverage, then reran the same pilot.

## 2026-09-06: Corrected resource-prioritization pilot rerun

- **Status:** Completed and saved, but still failed data-quality validation; do not interpret as an empirical result.
- **Configuration:** Same as the diagnostic pilot: 6 agents per population, 2 interaction rounds, 2 peers per agent, 12-agent baselines, and 3 seeds for diverse and homogeneous populations.
- **Report:** [`results/pilot_fixed_20260906_073112.json`](results/pilot_fixed_20260906_073112.json)
- **Finding:** The baseline distributions remained mostly `__unmatched__` after adding letter normalization: 10 of 12 diverse responses and all 12 homogeneous responses were unmatched.
- **Next debugging step:** Preserve raw model responses and strengthen the task prompt with an explicit allowed-label contract before rerunning the pilot.

## 2026-09-06: Audited pilot attempt

- **Status:** Stopped during the large configuration before a report was written.
- **Configuration:** Same 6-agent, 2-round, 3-seed pilot, with raw-response auditing enabled.
- **Reason stopped:** The 132 paced API calls were expected to take approximately 10 or more minutes; a compact validation run was used instead.
- **Result:** No report was written.

## 2026-09-06: Audited smoke validation

- **Status:** Passed data-quality validation; report saved and pushed.
- **Configuration:** One resource-prioritization task, 2 agents per population, diverse and homogeneous populations, 2-agent baselines, 1 seed, 1 interaction round, and 1 peer per agent.
- **Report:** [`results/audited_smoke_20260906_073752.json`](results/audited_smoke_20260906_073752.json)
- **Finding:** All baseline choices mapped to canonical labels with no `__unmatched__` responses. The report preserves raw baseline responses and raw responses for every agent and interaction round.
- **Note:** This validates the prompt and auditing pipeline; the sample is still too small for research conclusions.

## 2026-09-06: Audited smoke analysis

- **Status:** Completed.
- **Inputs:** [`results/audited_smoke_20260906_073752.json`](results/audited_smoke_20260906_073752.json)
- **Outputs:** [`results/audited_smoke_20260906_073752_analysis.png`](results/audited_smoke_20260906_073752_analysis.png) and [`results/audited_smoke_20260906_073752_analysis.json`](results/audited_smoke_20260906_073752_analysis.json)
- **Analysis:** Compared baseline choice distributions and categorical diversity across the independent and one-interaction-round measurements for diverse and homogeneous populations.
- **Interpretation:** The diverse smoke population retained higher categorical diversity than the homogeneous population, but the sample is too small to support a research conclusion.

## Future entries

For each new run, record the date, command, task set, population size, number of rounds, peer count, baseline size, seed count, population type, output path, and whether the run completed successfully.