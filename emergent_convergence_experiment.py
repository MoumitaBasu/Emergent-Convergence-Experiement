"""
Emergent Convergence and Bias in Interacting LLM Agents
---------------------------------------------------------
Prototype for the GoEMMI proposal, scaled to the study's intended size:
  - 12 heterogeneous agent personas (+ a homogeneous-population variant)
  - a battery of 3 closed-choice tasks + 1 open-ended task
  - 3 interaction rounds
  - a properly-sized Monte Carlo baseline (default 60 independent agents)
    for a stable merit-neutral pi_0 estimate (Sec 4.4)
  - multi-seed replication (Sec 4.5), reported as mean +/- std, not a
    single noisy trial

Model backend: Google Gemini API. The rest of the pipeline is model-
agnostic -- swap `call_llm()` again if you want to compare providers.

Usage:
    export GEMINI_API_KEY=...
    python emergent_convergence_experiment.py
"""

from __future__ import annotations

import json
import os
import random
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()  # reads GEMINI_API_KEY from a local .env file, if present

MODEL = "gemini-3.5-flash-lite"  # lower-demand option that is more reliable during usage spikes
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# Free-tier rate limits are typically ~15 requests/minute for gemini-2.5-flash.
# REQUEST_DELAY_SECONDS spaces calls out to stay under that; raise it if you
# still hit 429s, lower it if you're on a paid tier with higher limits.
REQUEST_DELAY_SECONDS = 4.5
MAX_RETRIES = 5


# ---------------------------------------------------------------------
# LLM call (Google Gemini API)
# ---------------------------------------------------------------------
def call_llm(prompt: str, system: str | None = None, max_tokens: int = 400) -> str:
    """Single-turn call to the Gemini API. Returns plain text.

    Paces requests by REQUEST_DELAY_SECONDS and retries with exponential
    backoff on 429 (rate limit) responses, so a long multi-seed battery
    run doesn't die partway through on a free-tier key.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system:
        payload["system_instruction"] = {"parts": [{"text": system}]}

    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_DELAY_SECONDS)
        resp = requests.post(
            API_URL,
            params={"key": api_key},
            headers={"content-type": "application/json"},
            json=payload,
            timeout=60,
        )
        if resp.status_code in {429, 500, 502, 503, 504}:
            backoff = REQUEST_DELAY_SECONDS * (2 ** attempt)
            status_label = {
                429: "rate limited",
                500: "server error",
                502: "bad gateway",
                503: "service unavailable",
                504: "gateway timeout",
            }.get(resp.status_code, "temporary error")
            print(f"  [{status_label}, attempt {attempt+1}/{MAX_RETRIES} -- "
                  f"waiting {backoff:.1f}s]")
            time.sleep(backoff)
            continue
        resp.raise_for_status()
        data = resp.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError):
            # e.g. response blocked by safety filters, or malformed candidate
            return json.dumps({
                "choice": "PARSE_ERROR", "justification": str(data),
                "confidence": None, "assumptions": "",
            })

    raise RuntimeError(f"Gemini API rate-limited after {MAX_RETRIES} retries.")


# ---------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------
@dataclass
class Agent:
    agent_id: int
    persona: str
    planted_bias: str | None = None  # e.g. a weakly-justified preference to seed
    history: list[dict] = field(default_factory=list)  # one entry per round

    def system_prompt(self) -> str:
        base = (
            f"You are an LLM-based agent role-playing the professional persona of a "
            f"{self.persona}. You are participating in a controlled study of "
            f"decision-making among interacting AI agents -- you are not a real "
            f"human and should not claim to be one."
        )
        if self.planted_bias:
            base += (
                f" For this study, lean toward favoring '{self.planted_bias}' in your "
                f"initial reasoning, even though the evidence for it is weak -- this "
                f"is a deliberately planted preference used to test whether weak "
                f"preferences get amplified through interaction."
            )
        return base

    def decide(self, task: str, peer_proposals: list[str] | None = None) -> dict:
        if peer_proposals is None:
            prompt = textwrap.dedent(f"""
                Task: {task}

                Give your decision and reasoning as strict JSON with keys:
                "choice" (a short label, 1-4 words), "justification" (2-3 sentences),
                "confidence" (0-1 float), "assumptions" (1 sentence).
                Return only the JSON object, no other text.
            """).strip()
        else:
            peers_block = "\n\n".join(
                f"Peer proposal {i+1}: {p}" for i, p in enumerate(peer_proposals)
            )
            prompt = textwrap.dedent(f"""
                Task: {task}

                Your previous decision: {self.history[-1]}

                You have been shown the following peer proposals:
                {peers_block}

                Review these alternatives and reconsider your decision. You may
                retain, modify, or replace your original proposal.

                Give your (possibly revised) decision as strict JSON with keys:
                "choice" (a short label, 1-4 words), "justification" (2-3 sentences),
                "confidence" (0-1 float), "assumptions" (1 sentence).
                Return only the JSON object, no other text.
            """).strip()

        raw = call_llm(prompt, system=self.system_prompt())
        parsed = _safe_json(raw)
        self.history.append(parsed)
        return parsed


def _safe_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1] if raw.lower().startswith("json") else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"choice": raw[:40], "justification": raw, "confidence": None, "assumptions": ""}


# ---------------------------------------------------------------------
# Diversity, convergence, bias metrics (Sec 4.2 - 4.4 of the proposal)
# ---------------------------------------------------------------------
def population_diversity(justifications: list[str]) -> float:
    """
    Semantic diversity (Sec 4.2b), TF-IDF cosine as a lightweight
    dependency-free proxy for a real embedding model. Returns [0, 1]:
    1 = maximally diverse, 0 = identical justifications.
    """
    if len(justifications) < 2:
        return 0.0
    vec = TfidfVectorizer(stop_words="english").fit_transform(justifications)
    sims = cosine_similarity(vec)
    n = sims.shape[0]
    off_diag = sims[~np.eye(n, dtype=bool)]
    return float(1 - off_diag.mean())


def choice_distribution(choices: list[str]) -> dict:
    dist: dict[str, int] = {}
    for c in choices:
        key = c.strip().lower()
        dist[key] = dist.get(key, 0) + 1
    return dict(sorted(dist.items(), key=lambda kv: -kv[1]))


def categorical_diversity(choices: list[str], options: list[str]) -> float:
    """
    Normalized Shannon entropy over a FIXED, predefined option set
    (Sec 4.2a). Returns [0, 1]: 1 = uniform spread across all K options,
    0 = full consensus on one option.
    """
    k = len(options)
    if k < 2:
        return 0.0
    counts = {opt: 0 for opt in options}
    for c in choices:
        key = c.strip().lower()
        for opt in options:
            if opt in key:
                counts[opt] += 1
                break
    n = sum(counts.values())
    if n == 0:
        return 0.0
    probs = [c / n for c in counts.values() if c > 0]
    entropy = -sum(p * np.log(p) for p in probs)
    return float(entropy / np.log(k))


def amplification_scores(post_dist: dict, baseline_dist: dict, options: list[str]) -> dict:
    """
    Log-ratio amplification score A_k = log(pi_r(k) / pi_0(k)) (Sec 4.4).
    Positive => option k became more popular after interaction than its
    standalone (no-interaction) merit alone would predict.
    """
    n_post = sum(post_dist.values()) or 1
    n_base = sum(baseline_dist.values()) or 1
    eps = 1e-6  # avoid log(0) for options nobody picked
    scores = {}
    for opt in options:
        p_post = post_dist.get(opt, 0) / n_post
        p_base = baseline_dist.get(opt, 0) / n_base
        scores[opt] = float(np.log((p_post + eps) / (p_base + eps)))
    return scores


def fit_convergence_rate(diversities: list[float]) -> dict:
    """
    Fit D_r ~= D_inf + (D_0 - D_inf) * exp(-lambda * r) via grid-search
    least squares (Sec 4.3, no scipy dependency needed for the prototype).
    """
    r = np.arange(len(diversities))
    d = np.array(diversities)
    if len(d) < 3 or np.allclose(d, d[0]):
        return {"d_inf": float(d[-1]), "lambda": 0.0}

    def loss(d_inf, lam):
        pred = d_inf + (d[0] - d_inf) * np.exp(-lam * r)
        return np.sum((pred - d) ** 2)

    best = None
    for d_inf in np.linspace(0, d[0], 20):
        for lam in np.linspace(0.01, 3.0, 30):
            l = loss(d_inf, lam)
            if best is None or l < best[0]:
                best = (l, d_inf, lam)
    return {"d_inf": float(best[1]), "lambda": float(best[2])}


# ---------------------------------------------------------------------
# Population and task battery (Sec 4.1, Sec 3.4 scale: 10-12 agents)
# ---------------------------------------------------------------------
PERSONAS = [
    "HR manager",
    "financial analyst",
    "product manager",
    "operations manager",
    "strategy consultant",
    "marketing lead",
    "IT director",
    "customer success manager",
    "supply chain manager",
    "sustainability officer",
    "R&D lead",
    "legal & compliance officer",
]

HOMOGENEOUS_PERSONA = "generalist management consultant"

TASKS = [
    {
        "id": "resource_prioritization",
        "prompt": (
            "A mid-sized company has limited resources and must decide which ONE of "
            "the following three initiatives to prioritize this year: (A) automating "
            "repetitive back-office processes, (B) investing in employee training and "
            "upskilling, or (C) increasing workplace flexibility (remote/hybrid policy). "
            "Pick one and justify it."
        ),
        "options": ["automation", "training", "flexibility"],
        "planted_bias_option": "automating repetitive back-office processes",
    },
    {
        "id": "budget_allocation",
        "prompt": (
            "A company must allocate a surplus budget to exactly ONE of: (A) increasing "
            "the marketing budget, (B) funding R&D for new product features, or (C) cutting "
            "costs and holding the surplus in reserve. Pick one and justify it."
        ),
        "options": ["marketing", "r&d", "cost_cutting"],
        "planted_bias_option": "cutting costs and holding the surplus in reserve",
    },
    {
        "id": "hiring_focus",
        "prompt": (
            "A growing team can make ONE type of hire this quarter: (A) senior specialists, "
            "(B) junior generalists who will be trained internally, or (C) external "
            "contractors for flexible capacity. Pick one and justify it."
        ),
        "options": ["senior", "junior", "contractors"],
        "planted_bias_option": "external contractors for flexible capacity",
    },
]

OPEN_ENDED_TASK = (
    "A company has limited resources and must decide which three initiatives to "
    "prioritize to improve organizational performance. Describe your top priority "
    "and your reasoning."
)


def build_population(n: int, planted_bias_fraction: float = 0.0, seed: int = 0,
                      planted_bias_option: str | None = None,
                      homogeneous: bool = False) -> list[Agent]:
    rng = random.Random(seed)
    if homogeneous:
        personas = [HOMOGENEOUS_PERSONA] * n
    else:
        # cycle through the full 12-persona roster; only repeats if n > 12
        personas = [PERSONAS[i % len(PERSONAS)] for i in range(n)]
    n_biased = int(round(n * planted_bias_fraction))
    biased_idx = set(rng.sample(range(n), n_biased)) if n_biased else set()
    return [
        Agent(
            agent_id=i,
            persona=personas[i],
            planted_bias=(planted_bias_option if i in biased_idx else None),
        )
        for i in range(n)
    ]


def sparse_peer_graph(agents: list[Agent], k_peers: int, seed: int = 0) -> dict[int, list[int]]:
    """Each agent sees k_peers other agents' latest proposals (random sparse graph)."""
    rng = random.Random(seed)
    graph = {}
    ids = [a.agent_id for a in agents]
    for a in agents:
        others = [i for i in ids if i != a.agent_id]
        graph[a.agent_id] = rng.sample(others, min(k_peers, len(others)))
    return graph


# ---------------------------------------------------------------------
# Single-run experiment
# ---------------------------------------------------------------------
def run_baseline(task_prompt: str, n_agents: int, seed: int = 0,
                  homogeneous: bool = False) -> dict:
    """
    Sec 4.4 step 1: purely independent agents, NO interaction, used to
    estimate each option's standalone-merit distribution pi_0. Uses a
    larger n_agents than the main run for a stable Monte Carlo estimate.
    """
    agents = build_population(n_agents, planted_bias_fraction=0.0, seed=seed,
                               homogeneous=homogeneous)
    for a in agents:
        a.decide(task_prompt)
    choices = [a.history[-1].get("choice", "") for a in agents]
    return choice_distribution(choices)


def run_experiment(task_prompt: str, options: list[str], n_agents: int = 12,
                    n_rounds: int = 3, k_peers: int = 3,
                    planted_bias_fraction: float = 0.33,
                    planted_bias_option: str | None = None,
                    homogeneous: bool = False, seed: int = 0) -> dict:
    agents = build_population(n_agents, planted_bias_fraction, seed=seed,
                               planted_bias_option=planted_bias_option,
                               homogeneous=homogeneous)

    for a in agents:
        a.decide(task_prompt)  # Round 0: independent decisions

    trajectory = []
    justifications = [a.history[-1].get("justification", "") for a in agents]
    choices = [a.history[-1].get("choice", "") for a in agents]
    trajectory.append({
        "round": 0,
        "semantic_diversity": population_diversity(justifications),
        "categorical_diversity": categorical_diversity(choices, options),
        "distribution": choice_distribution(choices),
    })

    graph = sparse_peer_graph(agents, k_peers, seed=seed)

    for r in range(1, n_rounds + 1):
        current_proposals = {
            a.agent_id: f"{a.history[-1].get('choice','')} -- {a.history[-1].get('justification','')}"
            for a in agents
        }
        for a in agents:
            peer_proposals = [current_proposals[pid] for pid in graph[a.agent_id]]
            a.decide(task_prompt, peer_proposals=peer_proposals)

        justifications = [a.history[-1].get("justification", "") for a in agents]
        choices = [a.history[-1].get("choice", "") for a in agents]
        trajectory.append({
            "round": r,
            "semantic_diversity": population_diversity(justifications),
            "categorical_diversity": categorical_diversity(choices, options),
            "distribution": choice_distribution(choices),
        })

    convergence_fit = fit_convergence_rate([p["categorical_diversity"] for p in trajectory])
    return {"agents": agents, "trajectory": trajectory, "convergence_fit": convergence_fit}


# ---------------------------------------------------------------------
# Full battery: multiple tasks x multiple seeds x diverse/homogeneous
# (Sec 4.5 replication, Sec 3.3 two-population comparison)
# ---------------------------------------------------------------------
def run_full_battery(tasks: list[dict] = TASKS, n_agents: int = 12, n_rounds: int = 3,
                      k_peers: int = 3, planted_bias_fraction: float = 0.33,
                      baseline_n: int = 60, n_seeds: int = 5) -> dict:
    """
    Runs each task under both population types (diverse personas vs.
    homogeneous personas), replicated across n_seeds, with a properly
    sized (baseline_n) Monte Carlo baseline per task.

    Returns per-task, per-population aggregated results:
      - mean +/- std categorical diversity per round
      - mean +/- std convergence rate (lambda)
      - mean amplification score per option, at the final round
    """
    report = {}
    for task in tasks:
        task_id = task["id"]
        report[task_id] = {}
        for pop_type, homogeneous in (("diverse", False), ("homogeneous", True)):
            baseline_dist = run_baseline(task["prompt"], n_agents=baseline_n,
                                          seed=1000, homogeneous=homogeneous)

            div_by_round = []   # list of lists: [seed][round]
            lambdas = []
            final_amplifications = []

            for seed in range(n_seeds):
                result = run_experiment(
                    task["prompt"], task["options"], n_agents=n_agents,
                    n_rounds=n_rounds, k_peers=k_peers,
                    planted_bias_fraction=planted_bias_fraction,
                    planted_bias_option=task["planted_bias_option"],
                    homogeneous=homogeneous, seed=seed,
                )
                div_by_round.append([p["categorical_diversity"] for p in result["trajectory"]])
                lambdas.append(result["convergence_fit"]["lambda"])
                final_dist = result["trajectory"][-1]["distribution"]
                final_amplifications.append(
                    amplification_scores(final_dist, baseline_dist, task["options"])
                )

            div_arr = np.array(div_by_round)  # shape (n_seeds, n_rounds+1)
            amp_keys = task["options"]
            amp_mean = {
                k: float(np.mean([a[k] for a in final_amplifications])) for k in amp_keys
            }
            amp_std = {
                k: float(np.std([a[k] for a in final_amplifications])) for k in amp_keys
            }

            report[task_id][pop_type] = {
                "baseline_distribution": baseline_dist,
                "categorical_diversity_mean": div_arr.mean(axis=0).tolist(),
                "categorical_diversity_std": div_arr.std(axis=0).tolist(),
                "convergence_lambda_mean": float(np.mean(lambdas)),
                "convergence_lambda_std": float(np.std(lambdas)),
                "amplification_mean": amp_mean,
                "amplification_std": amp_std,
            }
    return report


def print_battery_report(report: dict) -> None:
    for task_id, pops in report.items():
        print(f"\n=== Task: {task_id} ===")
        for pop_type, stats in pops.items():
            print(f"  -- {pop_type} population --")
            print(f"     baseline distribution: {stats['baseline_distribution']}")
            div_mean = [round(x, 3) for x in stats["categorical_diversity_mean"]]
            div_std = [round(x, 3) for x in stats["categorical_diversity_std"]]
            print(f"     categorical diversity by round (mean): {div_mean}")
            print(f"     categorical diversity by round (std):  {div_std}")
            print(f"     convergence rate lambda: {stats['convergence_lambda_mean']:.3f} "
                  f"+/- {stats['convergence_lambda_std']:.3f}")
            amp_mean = {k: round(v, 3) for k, v in stats["amplification_mean"].items()}
            print(f"     amplification A_k (mean over seeds): {amp_mean}")


RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def save_report(report: dict, prefix: str = "experiment") -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"{prefix}_{timestamp}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Saved report to: {output_path}")
    return output_path


if __name__ == "__main__":
    # Full-scale run matching the proposal: 12 agents, 3 tasks, 3 rounds,
    # a 60-agent Monte Carlo baseline per task/population, and 5-seed
    # replication for diverse vs. homogeneous populations.
    battery_report = run_full_battery(
        tasks=TASKS,
        n_agents=12,
        n_rounds=3,
        k_peers=3,
        planted_bias_fraction=0.33,
        baseline_n=60,
        n_seeds=5,
    )
    print_battery_report(battery_report)
    save_report(battery_report, prefix="battery")
