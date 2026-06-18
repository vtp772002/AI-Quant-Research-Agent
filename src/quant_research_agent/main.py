from __future__ import annotations

import argparse
import json
import os
import signal
from pathlib import Path
from threading import Event

from quant_research_agent.execution_simulator import (
    execution_simulation_to_dict,
    run_execution_simulation,
)
from quant_research_agent.experiment_family import (
    compare_experiment_family,
    family_comparison_to_dict,
    family_comparison_to_markdown,
)
from quant_research_agent.idea_review import (
    approved_config_paths,
    mark_configs_ran,
    review_audit_events,
    review_summary,
    update_idea_status,
)
from quant_research_agent.managed_registry import (
    managed_registry_deployment_to_dict,
    managed_registry_verification_to_dict,
    stage_managed_registry_deployment,
    verify_managed_registry_deployment,
)
from quant_research_agent.operations import batch_result_to_dict, run_research_batch
from quant_research_agent.paper_alpha import template_to_config, write_alpha_template
from quant_research_agent.promotion_authorization import (
    decide_family_promotion,
    list_family_promotions,
    promotion_ledger_verification_to_dict,
    recommend_family_promotion,
    verify_promotion_ledger,
)
from quant_research_agent.registry_export import (
    export_registry_snapshot,
    registry_export_to_dict,
    registry_governance_verification_to_dict,
    verify_registry_governance_pack,
)
from quant_research_agent.research_job_queue import (
    enqueue_research_job,
    get_research_job,
    list_stale_research_jobs,
    list_research_jobs,
    renew_research_job_lease,
    research_job_stale_diagnostic_to_dict,
    research_job_to_dict,
)
from quant_research_agent.research_job_worker import (
    research_worker_loop_summary_to_dict,
    research_worker_result_to_dict,
    run_research_worker_loop,
    run_research_worker_once,
)
from quant_research_agent.llm_provider import ProviderControlPolicy
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
        "--compare-family",
        help="Compare cross-run experiment-family evidence under a results/runs directory or a single manifest path.",
    )
    parser.add_argument("--family-id", help="Optional experiment family id filter for --compare-family.")
    parser.add_argument("--family-fdr-alpha", type=float, default=0.10, help="FDR alpha for --compare-family.")
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
        "--enqueue-research-job",
        nargs="+",
        help="Enqueue one durable research batch job for the supplied configs.",
    )
    parser.add_argument(
        "--job-queue-path",
        default="results/research_jobs.sqlite",
        help="SQLite research job queue path.",
    )
    parser.add_argument("--job-idempotency-key", help="Idempotency key for job enqueue.")
    parser.add_argument(
        "--job-output-dir",
        default="results/job_batches",
        help="Batch artifact directory persisted in an enqueued job.",
    )
    parser.add_argument(
        "--job-max-attempts",
        type=int,
        default=3,
        help="Maximum worker attempts before dead letter.",
    )
    parser.add_argument(
        "--list-research-jobs",
        action="store_true",
        help="List durable research jobs.",
    )
    parser.add_argument(
        "--list-stale-research-jobs",
        action="store_true",
        help="List running research jobs with stale heartbeats or expired leases.",
    )
    parser.add_argument("--show-research-job", help="Show one durable research job.")
    parser.add_argument(
        "--renew-research-job-lease",
        help="Renew one active research job lease by job id.",
    )
    parser.add_argument(
        "--job-lease-token",
        help="Active lease token for internal research job lease renewal.",
    )
    parser.add_argument(
        "--stale-after-seconds",
        type=int,
        default=300,
        help="Heartbeat age threshold for --list-stale-research-jobs.",
    )
    parser.add_argument(
        "--research-worker-run-once",
        action="store_true",
        help="Claim and execute at most one durable research job.",
    )
    parser.add_argument(
        "--research-worker-loop",
        action="store_true",
        help="Run a supervised durable research worker loop.",
    )
    parser.add_argument("--worker-id", default="local-worker", help="Worker id recorded in job leases and events.")
    parser.add_argument(
        "--worker-lease-seconds",
        type=int,
        default=300,
        help="Worker lease duration.",
    )
    parser.add_argument(
        "--worker-retry-delay-seconds",
        type=int,
        default=60,
        help="Retry delay after a failed worker attempt.",
    )
    parser.add_argument(
        "--worker-poll-seconds",
        type=float,
        default=5.0,
        help="Idle poll delay for --research-worker-loop.",
    )
    parser.add_argument(
        "--worker-max-jobs",
        type=int,
        help="Maximum jobs processed before --research-worker-loop stops.",
    )
    parser.add_argument(
        "--worker-max-runtime-seconds",
        type=float,
        help="Maximum runtime before --research-worker-loop stops.",
    )
    parser.add_argument(
        "--worker-stop-when-idle",
        action="store_true",
        help="Stop --research-worker-loop after the first idle poll.",
    )
    parser.add_argument(
        "--export-registry",
        help="Export a SQLite registry snapshot to an object-store style directory.",
    )
    parser.add_argument("--registry-path", default="results/experiments.sqlite", help="SQLite registry path for registry export.")
    parser.add_argument("--postgres-table", default="experiment_runs", help="Postgres table name for generated registry SQL.")
    parser.add_argument("--registry-owner", default="local-research-operator", help="Owner recorded in registry governance exports.")
    parser.add_argument("--registry-retention-days", type=int, default=365, help="Minimum retention days recorded in registry governance exports.")
    parser.add_argument("--previous-governance-manifest", help="Optional previous governance manifest path to hash-link into this export.")
    parser.add_argument("--verify-registry-governance", help="Verify a registry governance export directory.")
    parser.add_argument("--stage-managed-registry", help="Stage a local dry-run managed Postgres/object-lock deployment bundle.")
    parser.add_argument("--registry-governance-dir", help="Source registry governance export directory for --stage-managed-registry.")
    parser.add_argument("--managed-registry-owner", default="research-ops", help="Owner recorded in managed registry deployment bundles.")
    parser.add_argument("--managed-registry-schema", default="research_registry", help="Postgres schema recorded in managed registry apply plans.")
    parser.add_argument("--managed-registry-table", default="experiment_runs", help="Postgres table recorded in managed registry apply plans.")
    parser.add_argument("--managed-registry-object-prefix", default="research/registry", help="Object prefix recorded in local object-lock inventory.")
    parser.add_argument("--managed-registry-retention-days", type=int, default=730, help="Retention days recorded in local object-lock inventory.")
    parser.add_argument(
        "--managed-registry-no-legal-hold",
        action="store_false",
        dest="managed_registry_legal_hold",
        default=True,
        help="Record legal hold=false in local object-lock inventory.",
    )
    parser.add_argument("--verify-managed-registry", help="Verify a local dry-run managed registry deployment bundle.")
    parser.add_argument(
        "--recommend-family-promotion",
        help="Recommend one FAMILY_PROMOTE run from a manifest directory or manifest path.",
    )
    parser.add_argument(
        "--decide-family-promotion",
        help="Approve or reject one family promotion recommendation id.",
    )
    parser.add_argument("--list-family-promotions", help="List family promotion records from a ledger path.")
    parser.add_argument("--verify-promotion-ledger", help="Verify a family promotion ledger and frozen evidence.")
    parser.add_argument(
        "--promotion-ledger",
        default="results/promotions/promotion_ledger.jsonl",
        help="Family promotion ledger path for recommendation and decision commands.",
    )
    parser.add_argument("--promotion-family-id", help="Family id for a promotion recommendation.")
    parser.add_argument("--promotion-run-id", help="Run id for a promotion recommendation.")
    parser.add_argument("--promotion-decision", choices=["approved", "rejected"], help="Operator decision.")
    parser.add_argument("--promotion-actor", help="Explicit actor id recorded in the promotion ledger.")
    parser.add_argument("--promotion-role", choices=["researcher", "operator"], help="Actor role for a promotion mutation.")
    parser.add_argument("--promotion-note", default="", help="Recommendation or decision note.")
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
    parser.add_argument("--review-audit", action="store_true", help="Print append-only review audit events.")
    parser.add_argument("--set-idea-status", choices=["draft", "approved", "rejected", "ran", "archived"], help="Set one idea review status.")
    parser.add_argument("--idea-name", help="Idea name to update in a review queue.")
    parser.add_argument("--review-note", default="", help="Human review note for status changes.")
    parser.add_argument("--review-actor", default="operator", help="Actor recorded in review audit events.")
    parser.add_argument("--run-approved-ideas", action="store_true", help="Run approved configs from a review queue.")
    parser.add_argument("--llm-provider", default="deterministic", choices=["deterministic", "fixture", "command", "openai"], help="Research idea provider.")
    parser.add_argument("--llm-fixture", help="JSON fixture response for --llm-provider fixture.")
    parser.add_argument("--llm-command", help="External command for --llm-provider command. Reads prompt JSON from stdin and writes JSON to stdout.")
    parser.add_argument("--allow-external-llm", action="store_true", help="Allow external LLM providers to run.")
    parser.add_argument("--llm-prompt-version", default="research_idea_v1", help="Prompt/schema version recorded in provider transcripts.")
    parser.add_argument("--llm-model", help="Live LLM model name, or AIQRA_OPENAI_MODEL for --llm-provider openai.")
    parser.add_argument("--llm-api-url", help="Override live LLM API URL, or AIQRA_OPENAI_RESPONSES_URL.")
    parser.add_argument("--llm-timeout", type=float, default=60.0, help="Live LLM request timeout in seconds.")
    parser.add_argument("--llm-max-requests", type=int, help="Maximum provider requests allowed for this CLI operation.")
    parser.add_argument("--llm-max-estimated-cost-usd", type=float, help="Maximum estimated provider cost allowed for this CLI operation.")
    parser.add_argument("--llm-input-cost-per-1k", type=float, default=0.0, help="Estimated input-token cost per 1k tokens in USD.")
    parser.add_argument("--llm-output-cost-per-1k", type=float, default=0.0, help="Estimated output-token cost per 1k tokens in USD.")
    parser.add_argument("--llm-expected-output-tokens", type=int, help="Expected provider output tokens used for preflight cost estimates.")
    args = parser.parse_args(argv)
    llm_control_policy = ProviderControlPolicy(
        max_requests=args.llm_max_requests,
        max_estimated_cost_usd=args.llm_max_estimated_cost_usd,
        input_cost_per_1k_tokens_usd=args.llm_input_cost_per_1k,
        output_cost_per_1k_tokens_usd=args.llm_output_cost_per_1k,
        expected_output_tokens=args.llm_expected_output_tokens,
    )

    if args.enqueue_research_job:
        if not args.job_idempotency_key:
            raise SystemExit("--enqueue-research-job requires --job-idempotency-key")
        job = enqueue_research_job(
            Path(args.job_queue_path),
            config_paths=[Path(path) for path in args.enqueue_research_job],
            output_dir=Path(args.job_output_dir),
            idempotency_key=args.job_idempotency_key,
            comparison_metric=args.comparison_metric,
            limit=args.limit,
            max_attempts=args.job_max_attempts,
            submitted_by="cli",
        )
        print(json.dumps(research_job_to_dict(job), indent=2, sort_keys=True))
        return 0

    if args.list_research_jobs:
        jobs = list_research_jobs(
            Path(args.job_queue_path),
            limit=args.limit or 100,
        )
        print(
            json.dumps(
                {"jobs": [research_job_to_dict(job) for job in jobs]},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.list_stale_research_jobs:
        diagnostics = list_stale_research_jobs(
            Path(args.job_queue_path),
            stale_after_seconds=args.stale_after_seconds,
            limit=args.limit or 100,
        )
        print(
            json.dumps(
                {
                    "jobs": [
                        research_job_stale_diagnostic_to_dict(diagnostic)
                        for diagnostic in diagnostics
                    ]
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.show_research_job:
        job = get_research_job(Path(args.job_queue_path), args.show_research_job)
        if job is None:
            raise SystemExit(f"research job not found: {args.show_research_job}")
        print(json.dumps(research_job_to_dict(job), indent=2, sort_keys=True))
        return 0

    if args.renew_research_job_lease:
        if not args.job_lease_token:
            raise SystemExit("--renew-research-job-lease requires --job-lease-token")
        job = renew_research_job_lease(
            Path(args.job_queue_path),
            job_id=args.renew_research_job_lease,
            lease_token=args.job_lease_token,
            lease_seconds=args.worker_lease_seconds,
        )
        print(json.dumps(research_job_to_dict(job), indent=2, sort_keys=True))
        return 0

    if args.research_worker_run_once:
        result = run_research_worker_once(
            Path(args.job_queue_path),
            worker_id=args.worker_id,
            lease_seconds=args.worker_lease_seconds,
            retry_delay_seconds=args.worker_retry_delay_seconds,
        )
        print(
            json.dumps(
                research_worker_result_to_dict(result),
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if result.outcome in {"idle", "completed"} else 1

    if args.research_worker_loop:
        stop_event = _install_worker_stop_handlers()
        summary = run_research_worker_loop(
            Path(args.job_queue_path),
            worker_id=args.worker_id,
            lease_seconds=args.worker_lease_seconds,
            retry_delay_seconds=args.worker_retry_delay_seconds,
            poll_seconds=args.worker_poll_seconds,
            max_jobs=args.worker_max_jobs,
            max_runtime_seconds=args.worker_max_runtime_seconds,
            stop_when_idle=args.worker_stop_when_idle,
            stop_requested=stop_event.is_set,
        )
        print(
            json.dumps(
                research_worker_loop_summary_to_dict(summary),
                indent=2,
                sort_keys=True,
            )
        )
        terminal_failures = {"dead_letter", "lease_lost"}
        return 1 if terminal_failures.intersection(summary.outcome_counts) else 0

    if args.recommend_family_promotion:
        if not args.promotion_family_id or not args.promotion_run_id:
            raise SystemExit(
                "--recommend-family-promotion requires --promotion-family-id and --promotion-run-id"
            )
        if not args.promotion_actor or not args.promotion_role:
            raise SystemExit(
                "--recommend-family-promotion requires --promotion-actor and --promotion-role"
            )
        event = recommend_family_promotion(
            source_path=Path(args.recommend_family_promotion),
            family_id=args.promotion_family_id,
            run_id=args.promotion_run_id,
            ledger_path=Path(args.promotion_ledger),
            actor=args.promotion_actor,
            role=args.promotion_role,
            signing_key=_promotion_signing_key(),
            note=args.promotion_note,
            fdr_alpha=args.family_fdr_alpha,
        )
        print(json.dumps(event, indent=2, sort_keys=True))
        return 0

    if args.decide_family_promotion:
        if not args.promotion_decision or not args.promotion_actor or not args.promotion_role:
            raise SystemExit(
                "--decide-family-promotion requires --promotion-decision, --promotion-actor, and --promotion-role"
            )
        event = decide_family_promotion(
            ledger_path=Path(args.promotion_ledger),
            recommendation_id=args.decide_family_promotion,
            decision=args.promotion_decision,
            actor=args.promotion_actor,
            role=args.promotion_role,
            signing_key=_promotion_signing_key(),
            note=args.promotion_note,
        )
        print(json.dumps(event, indent=2, sort_keys=True))
        return 0

    if args.list_family_promotions:
        print(
            json.dumps(
                list_family_promotions(
                    Path(args.list_family_promotions),
                    signing_key=_promotion_signing_key(),
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.verify_promotion_ledger:
        verification = verify_promotion_ledger(
            Path(args.verify_promotion_ledger),
            signing_key=_promotion_signing_key(),
        )
        print(
            json.dumps(
                promotion_ledger_verification_to_dict(verification),
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if verification.valid else 1

    if args.review_ideas:
        if not args.review_queue:
            raise SystemExit("--review-ideas requires --review-queue")
        print(json.dumps(review_summary(Path(args.review_queue)), indent=2, sort_keys=True))
        return 0

    if args.review_audit:
        if not args.review_queue:
            raise SystemExit("--review-audit requires --review-queue")
        print(json.dumps(review_audit_events(Path(args.review_queue)), indent=2, sort_keys=True))
        return 0

    if args.set_idea_status:
        if not args.review_queue or not args.idea_name:
            raise SystemExit("--set-idea-status requires --review-queue and --idea-name")
        payload = update_idea_status(
            Path(args.review_queue),
            idea_name=args.idea_name,
            status=args.set_idea_status,
            note=args.review_note,
            actor=args.review_actor,
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
            mark_configs_ran(Path(args.review_queue), config_paths, actor=args.review_actor)
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
            model=args.llm_model,
            api_url=args.llm_api_url,
            timeout_seconds=args.llm_timeout,
            control_policy=llm_control_policy,
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
                        "controls_path": str(provider_artifacts.controls_path),
                        "eval_path": str(provider_artifacts.eval_path),
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
            model=args.llm_model,
            api_url=args.llm_api_url,
            timeout_seconds=args.llm_timeout,
            control_policy=llm_control_policy,
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
            owner=args.registry_owner,
            minimum_retention_days=args.registry_retention_days,
            previous_governance_manifest=Path(args.previous_governance_manifest)
            if args.previous_governance_manifest
            else None,
        )
        print(json.dumps(registry_export_to_dict(export), indent=2, sort_keys=True))
        return 0

    if args.verify_registry_governance:
        verification = verify_registry_governance_pack(Path(args.verify_registry_governance))
        print(json.dumps(registry_governance_verification_to_dict(verification), indent=2, sort_keys=True))
        return 0 if verification.valid else 1

    if args.stage_managed_registry:
        if not args.registry_governance_dir:
            raise SystemExit("--stage-managed-registry requires --registry-governance-dir")
        deployment = stage_managed_registry_deployment(
            governance_dir=Path(args.registry_governance_dir),
            output_dir=Path(args.stage_managed_registry),
            owner=args.managed_registry_owner,
            postgres_schema=args.managed_registry_schema,
            postgres_table=args.managed_registry_table,
            object_prefix=args.managed_registry_object_prefix,
            retention_days=args.managed_registry_retention_days,
            legal_hold=args.managed_registry_legal_hold,
        )
        print(json.dumps(managed_registry_deployment_to_dict(deployment), indent=2, sort_keys=True))
        return 0

    if args.verify_managed_registry:
        verification = verify_managed_registry_deployment(Path(args.verify_managed_registry))
        print(json.dumps(managed_registry_verification_to_dict(verification), indent=2, sort_keys=True))
        return 0 if verification.valid else 1

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

    if args.compare_family:
        comparison = compare_experiment_family(
            Path(args.compare_family),
            family_id=args.family_id,
            fdr_alpha=args.family_fdr_alpha,
            limit=args.limit,
        )
        if args.json:
            rendered = json.dumps(family_comparison_to_dict(comparison), indent=2, sort_keys=True)
        else:
            rendered = family_comparison_to_markdown(comparison)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            print(f"Family comparison: {output_path}")
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


def _promotion_signing_key() -> str:
    signing_key = os.getenv("AIQRA_PROMOTION_LEDGER_HMAC_KEY", "")
    if len(signing_key) < 16:
        raise SystemExit(
            "family promotion commands require AIQRA_PROMOTION_LEDGER_HMAC_KEY with at least 16 characters"
        )
    return signing_key


def _install_worker_stop_handlers() -> Event:
    stop_event = Event()

    def request_stop(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    return stop_event


if __name__ == "__main__":
    raise SystemExit(main())
