import unittest

from emergent_convergence_experiment import (
    UNMATCHED_CHOICE,
    categorical_diversity,
    choice_distribution,
    normalize_choice,
)


class ChoiceNormalizationTests(unittest.TestCase):
    def test_maps_free_form_choice_to_canonical_option(self):
        options = ["automation", "training", "flexibility"]

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


if __name__ == "__main__":
    unittest.main()