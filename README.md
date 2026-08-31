# Emergent Convergence and Bias in Interacting LLM Agents

Prototype for a GoEMMI Göttingen research proposal studying how repeated
information exchange between LLM-based agents affects the diversity of
their decisions, and whether interaction can amplify particular
preferences into disproportionate consensus.

## Contents

- `research_proposal.md` — full research proposal: motivation, method,
  formal definitions of diversity/convergence/bias, and feasibility.
- `emergent_convergence_experiment.py` — working pipeline:
  - 12 heterogeneous agent personas (+ a homogeneous-population variant)
  - a battery of 3 closed-choice tasks + 1 open-ended task
  - independent (Round 0) decisions, then N rounds of controlled
    peer-to-peer information exchange over a sparse interaction graph
  - categorical (entropy-based) and semantic (embedding-based) diversity
    metrics
  - a Monte Carlo, non-interacting baseline used to define a
    merit-neutral bias amplification score
  - multi-seed replication across diverse vs. homogeneous populations

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# then edit .env and paste your key: GEMINI_API_KEY=your_actual_key
python emergent_convergence_experiment.py
```

Get a free Gemini API key at https://aistudio.google.com/apikey — Google's
free tier is generous enough for the smoke-test scale (a few seeds, one
task) before committing to the full 5-seed × 3-task battery.

`.env` is already listed in `.gitignore`, so your key stays local and is
never committed to the repo — the script loads it automatically via
`python-dotenv` on every run, so you only have to set it once.

The `call_llm()` function is model-agnostic by design — swap it for the
Anthropic API or any other provider if you want to compare models later.

## Status

Prototype validated end-to-end (agent decisions, peer graph, diversity
metrics, baseline, multi-seed aggregation) against a mocked model
backend. Not yet run against a live model at full scale — see the
runtime/cost note in `research_proposal.md` before running the full
5-seed × 3-task battery.