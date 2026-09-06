# Emergent Convergence and Bias in Interacting LLM Agents
A computational research prototype exploring how repeated information exchange between LLM-based agents affects decision diversity, convergence, and the amplification of shared preferences.

The project is being developed as a potential research project for the GoEMMI Göttingen Winter School, with a focus on emergence, learning, computation, and complex systems.

## Research Question

> How does interaction between LLM-based agents affect the diversity of their decisions, and can repeated information exchange lead to the emergence or amplification of shared decision patterns?

The project investigates a simple micro-to-macro setting:

```
Individual agents
       ↓
Independent decisions
       ↓
Information exchange
       ↓
Repeated interaction
       ↓
Collective behaviour
       ↓
Convergence / diversity / amplification
```

## Experimental Design
The current prototype models a population of 12 heterogeneous LLM-based agents, with an alternative homogeneous-population configuration.

Each agent is assigned a professional persona and receives the same knowledge-work task.

The experiment consists of:

1. Round 0 — Independent decisions
   - Agents solve the task independently.
   - Their initial decisions establish the baseline.
2. Interaction rounds
   - Agents exchange information through a controlled, sparse peer-to-peer interaction graph.
   - Agents reconsider and revise their decisions after receiving information from other agents.
3. Measurement
   - Decision diversity is measured after each round.
   - Changes in the distribution of decisions are examined for convergence and potential amplification of particular preferences.
4. Replication
   - Multiple random seeds are used to examine whether observed patterns are robust across different interaction configurations.
   - Diverse and homogeneous agent populations can be compared.

## Current Experimental Components
The experimental pipeline currently includes:

- 12 heterogeneous agent personas
- A homogeneous-population variant
- 3 closed-choice knowledge-work tasks
- 1 open-ended knowledge-work task
- Independent baseline decisions
- Controlled peer-to-peer information exchange
- Sparse interaction graphs
- Categorical, entropy-based diversity metrics
- Semantic, embedding-based diversity metrics
- A non-interacting Monte Carlo baseline
- A merit-neutral bias amplification measure
- Multi-seed replication

## Why This Project?
The project is motivated by the question of how system-level behaviour can emerge from interactions between individual computational agents.

Rather than assuming that interaction necessarily improves collective decision-making, the experiment investigates whether information exchange can produce:

- convergence between initially different agents
- loss of decision diversity
- persistence or amplification of particular preferences
- different collective outcomes depending on the initial diversity of the population

The goal is to explore these phenomena computationally while keeping the experimental setup reproducible and interpretable.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your environment file

```bash
cp .env.example .env
```

Then add your Gemini API key:

```bash
GEMINI_API_KEY=your_actual_key
```

Do not commit your `.env` file to GitHub.

The repository includes `.env` in `.gitignore`, and the script loads the key locally using `python-dotenv`.

### 3. Run the experiment

```bash
python emergent_convergence_experiment.py
```

For initial testing, use a small number of seeds and a single task before running the complete experimental battery.

### 4. Analyze a saved report

```bash
python analyze_results.py results/audited_smoke_20260906_073752.json
```

This writes a PNG comparison plot and a JSON analysis summary beside the input report. New battery reports also include the model, experiment parameters, task IDs, request pacing, and UTC generation timestamp in their `metadata` section.

## Project Structure

```
.
├── emergent_convergence_experiment.py
├── requirements.txt
├── .gitignore
├── README.md
└── .env
```

### Main files

- `emergent_convergence_experiment.py` — experimental pipeline for agent generation, interaction, decision collection, diversity measurement, baseline comparison, and multi-seed experiments.
- `requirements.txt` — Python dependencies required to run the project.
- `.env` — local environment file containing your Gemini API key.

## Status
🚧 Early prototype — active development

The experimental pipeline has been validated end-to-end using a mocked model backend, including agent decisions, peer interaction, diversity metrics, baseline comparison, and multi-seed aggregation.

The project is now being tested with a live Gemini API. The experimental parameters, implementation, and methodology may evolve as the prototype is evaluated.

No empirical conclusions are being claimed yet.

## Future Directions
Potential extensions include:

- Comparing different LLM models
- Testing different network structures
- Varying the degree of initial agent diversity
- Studying longer interaction sequences
- Investigating polarization as well as convergence
- Comparing computational-agent behaviour with small-scale human experiments
- Exploring information-theoretic measures of collective behaviour

## Research Context
This is an exploratory computational study, not a claim that LLM agents are equivalent to human participants.

The project uses LLM-based agents as computational systems for investigating how local information exchange can produce collective-level patterns such as convergence and preference amplification.