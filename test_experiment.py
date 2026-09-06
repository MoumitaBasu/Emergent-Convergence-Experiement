import json
import unittest
from unittest.mock import patch

from emergent_convergence_experiment import (
    Agent,
    UNMATCHED_CHOICE,
    categorical_diversity,
    choice_distribution,
    normalize_choice,
)


class ChoiceNormalizationTests(unittest.TestCase):
    def test_maps_free_form_choice_to_canonical_option(self):
        options = ["automation", "training", "flexibility"]

        self.assertEqual(normalize_choice("A", options), "automation")
        self.assertEqual(normalize_choice("option C", options), "flexibility")
        self.assertEqual(
            normalize_choice("Investing in employee training", options),
            "training",
        )
        self.assertEqual(
            normalize_choice("workplace flexibility", options),
            "flexibility",
        )

    def test_handles_punctuation_plural_and_word_order(self):
        options = ["marketing", "r&d", "cost_cutting"]

        self.assertEqual(normalize_choice("R&D", options), "r&d")
        self.assertEqual(normalize_choice("cutting costs", options), "cost_cutting")

    def test_rejects_unmatched_or_ambiguous_choices(self):
        options = ["automation", "training", "flexibility"]

        self.assertEqual(normalize_choice("something unrelated", options), UNMATCHED_CHOICE)
        self.assertEqual(normalize_choice("automation and training", options), UNMATCHED_CHOICE)

    def test_metrics_use_canonical_labels(self):
        options = ["automation", "training", "flexibility"]
        choices = ["automation", "employee training"]

        self.assertEqual(
            choice_distribution(choices, options),
            {"automation": 1, "training": 1},
        )
        self.assertGreater(categorical_diversity(choices, options), 0.0)


class DecisionAuditTests(unittest.TestCase):
    def test_prompt_requires_exact_allowed_label_and_keeps_raw_response(self):
        response = json.dumps({
            "choice": "training",
            "justification": "Training improves internal capability.",
            "confidence": 0.8,
            "assumptions": "The team can implement the program.",
        })

        with patch("emergent_convergence_experiment.call_llm", return_value=response) as call:
            agent = Agent(agent_id=0, persona="HR manager")
            decision = agent.decide(
                "Choose one initiative.",
                options=["automation", "training", "flexibility"],
            )

        prompt = call.call_args.args[0]
        self.assertIn("Allowed choice labels: automation, training, flexibility", prompt)
        self.assertIn("must be exactly one allowed label", prompt)
        self.assertEqual(decision["_raw_response"], response)


if __name__ == "__main__":
    unittest.main()