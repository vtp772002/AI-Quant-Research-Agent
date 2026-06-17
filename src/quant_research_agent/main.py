from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant_research_agent.execution_simulator import (
    execution_simulation_to_dict,
    run_execution_simulation,
)
from quant_research_agent.idea_review import (
    approved_config_paths,
    mark_configs_ran,
    review_summary,
    update_idea_status,
)
from quant_research_agent.operations import batch_result_to_dict, run_research_batch
from quant_research_agent.paper_alpha import template_to_config, write_alpha_template
from quant_research_agent.registry_export import export_registry_snapshot, registry_export_to_dict
from quant_research_agent.research_agents import (
    critique_run_manifest,
    critique_to_dict,
    generate_idea_configs,
    generate_idea_configs_with_provider,
    mining_result_to_dict,
    mine_alpha,
    paper_to_alpha_v2,
)
from quant_research_agent.run_comparison import (
    compare_run_manifests,
    comparison_to_dict,
    comparison_to_markdown,
)
from quant_research_agent.workflow import run_configured_workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an AI quant research workflow.")
    parser.add_argument("--config", default="configs/base.yaml", help="Path to YAML config.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable metrics.")
    parser.add_argument(
        "--compare-runs",
        help="Compare reproducibility manifests under a results/runs directory or a single manifest path.",
    )
    parser.add_argument(
        "--comparison-metric",
        default="sharpe",
        choices=[
            "sharpe",
            "total_return",
            "ic_mean",
            "max_drawdown",
            "average_total_cost",
            "average_turnover",
        ],
        help="Metric used to rank compared runs.",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of compared runs to return.")
    parser.add_argument("--output", help="Optional path for comparison output.")
    parser.add_argument("--run-batch", nargs="+", help="Run one or more configs and publish batch summary/comparison artifacts.")
    parser.add_argument("--batch-output-dir", default="results/batch", help="Directory for batch summary and comparison artifacts.")
    parser.add_argument(
        "--export-registry",
        help="Export a SQLite registry snapshot to an object-store style directory.",
    )
    parser.add_argument("--registry-path", default="results/experiments.sqlite", help="SQLite registry path for registry export.")
    parser.add_argument("--postgres-table", default="experiment_runs", help="Postgres table name for generated registry SQL.")
    parser.add_argument("--paper-to-alpha", help="Extract a draft alpha experiment template from a paper/blog text file.")
    parser.add_argument("--template-output", help="Output YAML path for --paper-to-alpha.")
    parser.add_argument("--simulate-execution", action="store_true", help="Simulate an as-of execution plan without placing trades.")
    parser.add_argument("--as-of-date", help="As-of date for signal generation or execution simulation.")
    parser.add_argument("--execution-output", help="Optional JSON output path for execution simulation.")
    parser.add_argument("--max-participation", type=float, help="Override simulated max trade participation.")
    parser.add_argument("--generate-ideas", action="store_true", help="Generate validated research idea configs from prior run memory.")
    parser.add_argument("--ideas-output-dir", default="results/ideas", help="Output directory for generated ideas/configs.")
    parser.add_argument("--objective", default="Find robust medium-frequency equity alpha.", help="Research objective for idea generation.")
    parser.add_argument("--n", type=int, default=5, help="Number of research ideas to generate.")
    parser.add_argument("--critique-run", help="Critique one reproducibility manifest and propose a follow-up experiment.")
    parser.add_argument("--paper-to-alpha-v2", help="Extract a validated paper-to-alpha idea payload from a paper/blog text file.")
    parser.add_argument("--mine-alpha", action="store_true", help="Generate alpha ideas, write configs, and optionally run them.")
    parser.add_argument("--mine-output-dir", default="results/alpha_mining", help="Output directory for alpha-mining artifacts.")
    parser.add_argument("--run-generated", action="store_true", help="Run generated configs during --mine-alpha.")
    parser.add_argument("--review-override", action="store_true", help="Allow --mine-alpha --run-generated to run draft ideas without approval.")
    parser.add_argument("--review-queue", help="Path to an idea review queue JSON.")
    parser.add_argument("--review-ideas", action="store_true", help="Print idea review queue status.")
    parser.add_argument("--set-idea-status", choices=["draft", "approved", "rejected", "ran", "archived"], help="Set one idea review status.")
    parser.add_argument("--idea-name", help="Idea name to update in a review queue.")
    parser.add_argument("--review-note", default="", help="Human review note for status changes.")
    parser.add_argument("--run-approved-ideas", action="store_true", help="Run approved configs from a review queue.")
    parser.add_argument("--llm-provider", default="deterministic", choices=["deterministic", "fixture", "command"], help="Research idea provider.")
    parser.add_argument("--llm-fixture", help="JSON fixture response for --llm-provider fixture.")
    parser.add_argument("--llm-command", help="External command for --llm-provider command. Reads prompt JSON from stdin and writes JSON to stdout.")
    parser.add_argument("--allow-external-llm", action="store_true", help="Allow --llm-provider command to run an external process.")
    parser.add_argument("--llm-prompt-version", default="research_idea_v1", help="Prompt/schema version recorded in provider transcripts.")
    args = parser.parse_args(argv)

    if args.review_ideas:
        if not args.review_queue:
            raise SystemExit("--review-ideas requires --review-queue")
        print(json.dumps(review_summary(Path(args.review_queue)), indent=2, sort_keys=True))
        return 0

    if args.set_idea_status:
        if not args.review_queue or not args.idea_name:
            raise SystemExit("--set-idea-status requires --review-queue and --idea-name")
        payload = update_idea_status(
            Path(args.review_queue),
            idea_name=args.idea_name,
            status=args.set_idea_status,
            note=args.review_note,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.run_approved_ideas:
        if not args.review_queue:
            raise SystemExit("--run-approved-ideas requires --review-queue")
        config_paths = approved_config_paths(Path(args.review_queue))
        if not config_paths:
            raise SystemExit("review queue has no approved ideas to run")
        result = run_research_batch(
            config_paths=config_paths,
            output_dir=Path(args.batch_output_dir),
            comparison_metric=args.comparison_metric,
            limit=args.limit,
        )
        if result.status == "completed":
            mark_configs_ran(Path(args.review_queue), config_paths)
        print(json.dumps(batch_result_to_dict(result), indent=2, sort_keys=True))
        return 0 if result.status == "completed" else 1

    if args.generate_ideas:
        ideas, config_paths, ideas_path, review_queue_path, provider_artifacts = generate_idea_configs_with_provider(
            base_config_path=Path(args.config),
            output_dir=Path(args.ideas_output_dir),
            objective=args.objective,
            count=args.n,
            registry_path=Path(args.registry_path),
            provider=args.llm_provider,
            fixture_path=Path(args.llm_fixture) if args.llm_fixture else None,
            command=args.llm_command,
            allow_external=args.allow_external_llm,
            prompt_version=args.llm_prompt_version,
        )
        print(
            json.dumps(
                {
                    "ideas_path": str(ideas_path),
                    "review_queue_path": str(review_queue_path),
                    "config_paths": [str(path) for path in config_paths],
                    "idea_count": len(ideas),
                    "provider_artifacts": None
                    if provider_artifacts is None
                    else {
                        "prompt_path": str(provider_artifacts.prompt_path),
                        "response_path": str(provider_artifacts.response_path),
                        "transcript_path": str(provider_artifacts.transcript_path),
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.critique_run:
        print(json.dumps(critique_to_dict(critique_run_manifest(Path(args.critique_run))), indent=2, sort_keys=True))
        return 0

    if args.paper_to_alpha_v2:
        payload = paper_to_alpha_v2(Path(args.paper_to_alpha_v2).read_text(encoding="utf-8"), name=Path(args.paper_to_alpha_v2).stem)
        if args.template_output:
            output_path = Path(args.template_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            payload["output_path"] = str(output_path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.mine_alpha:
        result = mine_alpha(
            base_config_path=Path(args.config),
            output_dir=Path(args.mine_output_dir),
            objective=args.objective,
            count=args.n,
            registry_path=Path(args.registry_path),
            run_generated=args.run_generated,
            provider=args.llm_provider,
            fixture_path=Path(args.llm_fixture) if args.llm_fixture else None,
            command=args.llm_command,
            allow_external=args.allow_external_llm,
            prompt_version=args.llm_prompt_version,
            review_override=args.review_override,
        )
        print(json.dumps(mining_result_to_dict(result), indent=2, sort_keys=True))
        return 0

    if args.run_batch:
        result = run_research_batch(
            config_paths=[Path(path) for path in args.run_batch],
            output_dir=Path(args.batch_output_dir),
            comparison_metric=args.comparison_metric,
            limit=args.limit,
        )
        print(json.dumps(batch_result_to_dict(result), indent=2, sort_keys=True))
        return 0 if result.status == "completed" else 1

    if args.export_registry:
        export = export_registry_snapshot(
            registry_path=Path(args.registry_path),
            output_dir=Path(args.export_registry),
            postgres_table=args.postgres_table,
        )
        print(json.dumps(registry_export_to_dict(export), indent=2, sort_keys=True))
        return 0

    if args.paper_to_alpha:
        output_path = Path(args.template_output or "results/paper_alpha_template.yaml")
        template = write_alpha_template(Path(args.paper_to_alpha), output_path)
        payload = template_to_config(template)
        payload["output_path"] = str(output_path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.simulate_execution:
        simulation = run_execution_simulation(
            config_path=Path(args.config),
            as_of_date=args.as_of_date,
            output_path=Path(args.execution_output) if args.execution_output else None,
            max_participation=args.max_participation,
        )
        print(json.dumps(execution_simulation_to_dict(simulation), indent=2, sort_keys=True))
        return 0

    if args.compare_runs:
        comparison = compare_run_manifests(
            Path(args.compare_runs),
            metric=args.comparison_metric,
            limit=args.limit,
        )
        if args.json:
            rendered = json.dumps(comparison_to_dict(comparison), indent=2, sort_keys=True)
        else:
            rendered = comparison_to_markdown(comparison)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            print(f"Comparison: {output_path}")
        else:
            print(rendered)
        return 0

    workflow = run_configured_workflow(Path(args.config))
    payload = workflow.payload
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        test = workflow.result.backtest.metrics["test"]
        print(f"Experiment: {workflow.config.experiment.name}")
        print(f"Run: {workflow.manifest['run_id']}")
        print(f"Report: {workflow.report_path}")
        print(f"Results: {workflow.experiments_path}")
        print(f"Manifest: {workflow.manifest['artifacts']['manifest_path']}")
        print(f"Registry: {workflow.config.report.registry_path}")
        print(
            "Test metrics: "
            f"IC={test['ic_mean']:.4f}, Sharpe={test['sharpe']:.2f}, "
            f"MaxDD={test['max_drawdown']:.2%}, Turnover={test['average_turnover']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
