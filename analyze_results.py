"""Create compact plots and summaries from an experiment JSON report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def analyze_report(report_path: Path) -> tuple[Path, Path]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    tasks = {
        task_id: values
        for task_id, values in report.items()
        if task_id != "metadata"
    }
    if not tasks:
        raise ValueError("Report contains no task results")

    summary = {"metadata": report.get("metadata", {}), "tasks": {}}
    for task_id, populations in tasks.items():
        summary["tasks"][task_id] = {}
        for population, stats in populations.items():
            summary["tasks"][task_id][population] = {
                "baseline_distribution": stats["baseline_distribution"],
                "categorical_diversity_mean": stats["categorical_diversity_mean"],
                "categorical_diversity_std": stats["categorical_diversity_std"],
                "convergence_lambda_mean": stats["convergence_lambda_mean"],
                "amplification_mean": stats["amplification_mean"],
            }

    figure, axes = plt.subplots(len(tasks) * 2, 1, figsize=(10, 5 * len(tasks)))
    axes = list(axes)
    for task_index, (task_id, populations) in enumerate(tasks.items()):
        baseline_axis = axes[task_index * 2]
        diversity_axis = axes[task_index * 2 + 1]
        labels = sorted({
            label
            for stats in populations.values()
            for label in stats["baseline_distribution"]
        })
        positions = list(range(len(labels)))
        width = 0.8 / max(len(populations), 1)
        for population_index, (population, stats) in enumerate(populations.items()):
            values = [stats["baseline_distribution"].get(label, 0) for label in labels]
            offsets = [position + population_index * width for position in positions]
            baseline_axis.bar(offsets, values, width=width, label=population)
            diversity_axis.errorbar(
                range(len(stats["categorical_diversity_mean"])),
                stats["categorical_diversity_mean"],
                yerr=stats["categorical_diversity_std"],
                marker="o",
                capsize=3,
                label=population,
            )

        baseline_axis.set_title(f"{task_id}: baseline choice distribution")
        baseline_axis.set_ylabel("Agents")
        baseline_axis.set_xticks([position + width / 2 for position in positions])
        baseline_axis.set_xticklabels(labels, rotation=20, ha="right")
        baseline_axis.legend()
        diversity_axis.set_title(f"{task_id}: categorical diversity by round")
        diversity_axis.set_xlabel("Interaction round")
        diversity_axis.set_ylabel("Normalized entropy")
        diversity_axis.set_ylim(bottom=0)
        diversity_axis.legend()

    figure.tight_layout()
    image_path = report_path.with_name(f"{report_path.stem}_analysis.png")
    summary_path = report_path.with_name(f"{report_path.stem}_analysis.json")
    figure.savefig(image_path, dpi=150)
    plt.close(figure)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return image_path, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to an experiment JSON report")
    args = parser.parse_args()
    image_path, summary_path = analyze_report(args.report)
    print(f"Saved analysis plot to: {image_path}")
    print(f"Saved analysis summary to: {summary_path}")


if __name__ == "__main__":
    main()