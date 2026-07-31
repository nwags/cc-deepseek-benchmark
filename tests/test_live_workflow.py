from pathlib import Path


WORKFLOW_DIR = Path(".github/workflows")
TARGET_WORKFLOWS = (
    "phase3-arm-dispatch-v2.yml",
    "phase3-arm-dispatch.yml",
    "phase3-dispatch-probe.yml",
    "phase3-remote-db-r2-doctor.yml",
    "phase3-remote-runner-doctor.yml",
)
OBSOLETE_LABELS = (
    "phase3-vps2",
    "phase3-slot-2",
    "phase3-slot-3",
    "phase3-slot4",
    "phase3-slot5",
    "phase3-slot6",
)


def test_all_runner_workflows_use_phase_neutral_pool() -> None:
    for name in TARGET_WORKFLOWS:
        text = (WORKFLOW_DIR / name).read_text()
        assert "cc-bench" in text
        for obsolete in OBSOLETE_LABELS:
            assert obsolete not in text


def test_primary_workflow_exposes_only_approved_runner_choices() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    expected = [
        "cc-bench",
        "cc-bench-vps1",
        "cc-bench-vps2",
        *(f"cc-bench-slot-{index}" for index in range(1, 7)),
    ]
    runner_input = text.split("runner_label:", 1)[1].split("\nenv:", 1)[0]
    for label in expected:
        assert f"- {label}" in runner_input
    assert "- phase3" not in runner_input
    assert "- ${{ inputs.runner_label }}" in text


def test_workflow_uses_runner_name_only_as_opaque_metadata() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    assert '--runner-name "$RUNNER_NAME"' in text
    assert "RUNNER_NAME#" not in text
    assert "RUNNER_NAME%" not in text
    assert "case \"$RUNNER_NAME\"" not in text


def test_dry_run_cannot_publish_canonical_results_or_r2() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    assert 'if [[ "$DRY_RUN" == "true" ]]; then\n            cmd+=(--dry-run)' in text
    assert "--dry-run-metadata --no-scored --no-progressive-artifacts" in text
    assert "scripts/publish_phase3_run.py" in text


def test_live_wrapper_provisions_database_and_r2_dependencies() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    supervisor = text.split("supervisor=(", 1)[1].split("\n            )", 1)[0]
    assert "uv run --with boto3 --with 'psycopg[binary]'" in supervisor
    assert "python scripts/run_arm_live.py" in supervisor


def test_workflow_context_omits_full_workspace_paths_and_shows_failure_logs() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    context = text.split('context = {', 1)[1].split("\n          }", 1)[0]
    assert '"workspace": workspace.as_posix()' not in context
    assert "path.relative_to(workspace).as_posix()" in context
    assert "steps.benchmark.outcome == 'failure'" in text


def test_final_publication_live_link_depends_on_supervision() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    publication = text.split("- name: Publish final canonical run", 1)[1].split(
        "- name: List generated run files",
        1,
    )[0]
    command = publication.split("cmd=(", 1)[1].split("\n          )", 1)[0]
    assert '--live-run-id "$LIVE_RUN_ID"' not in command
    assert '--expected-trial-count "$EXPECTED_TRIAL_COUNT"' in command
    assert (
        'if [[ "$SUPERVISE_LIVE" == "true" ]]; then\n'
        '            cmd+=(--live-run-id "$LIVE_RUN_ID")'
    ) in publication


def test_discovery_context_is_available_without_supervision() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    context_step = text.split("- name: Prepare live execution context", 1)[1].split(
        "- name: Run configured arm",
        1,
    )[0]
    assert ".run\" / \"publish\"" in context_step
    assert ".discovery-context.json" in context_step
    assert 'if [[ "$SUPERVISE_LIVE" != "true" ]]; then' not in context_step
    publication = text.split("- name: Publish final canonical run", 1)[1]
    assert (
        '--discovery-context ".run/publish/${LIVE_RUN_ID}.discovery-context.json"'
        in publication
    )
    assert (
        '"$PROGRESSIVE_ARTIFACTS" == "true" && "$SUPERVISE_LIVE" != "true"'
        in text
    )
    assert (
        '"$PROGRESSIVE_ARTIFACTS" == "true" && "$PUBLISH_RESULTS" != "true"'
        in text
    )


def test_post_closeout_workflow_defaults_to_live_only() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    publish_input = text.split("      publish_results:", 1)[1].split(
        "      progressive_artifacts:",
        1,
    )[0]
    progressive_input = text.split("      progressive_artifacts:", 1)[1].split(
        "      authorize_phase3_repair:",
        1,
    )[0]
    repair_input = text.split("      authorize_phase3_repair:", 1)[1].split(
        "      runner_label:",
        1,
    )[0]
    assert "default: false" in publish_input
    assert "default: false" in progressive_input
    assert "default: false" in repair_input
    assert "default: true" in text.split("      supervise_live:", 1)[1].split(
        "      publish_results:",
        1,
    )[0]


def test_closed_phase3_publication_requires_explicit_repair_input() -> None:
    text = (WORKFLOW_DIR / "phase3-arm-dispatch-v2.yml").read_text()
    assert "requires authorize_phase3_repair" in text
    assert 'cmd+=(--authorize-phase3-repair)' in text
    assert "--allow-dependent-trial-replacement" not in text


def test_remote_db_r2_doctor_never_enables_xtrace() -> None:
    text = (
        WORKFLOW_DIR / "phase3-remote-db-r2-doctor.yml"
    ).read_text()
    assert "set -euxo pipefail" not in text
    assert "set -x" not in text


def test_dry_runs_use_only_synthetic_selected_provider_secrets() -> None:
    workflow_names = (
        "phase3-arm-dispatch-v2.yml",
        "phase3-arm-dispatch.yml",
    )
    provider_mappings = {
        "ANTHROPIC_API_KEY": "anthropic.env",
        "DEEPSEEK_API_KEY": "deepseek.env",
        "OPENAI_API_KEY": "openai.env",
        "GEMINI_API_KEY": "gemini.env",
        "XAI_API_KEY": "xai.env",
        "MOONSHOT_API_KEY": "kimi.env",
        "DASHSCOPE_API_KEY": "dashscope.env",
        "ZAI_API_KEY": "zai.env",
    }

    for name in workflow_names:
        workflow_text = (WORKFLOW_DIR / name).read_text()

        dry_step = workflow_text.split(
            "- name: Create dry-run placeholder env files",
            1,
        )[1].split(
            "- name: Create paid runtime secret env files",
            1,
        )[0]

        assert "if: ${{ inputs.dry_run }}" in dry_step
        assert "ARM_ID: ${{ inputs.arm_id }}" in dry_step
        assert "${{ secrets." not in dry_step
        assert "dry-run-placeholder-litellm-master-key" in dry_step
        assert "write_text(content, encoding=\"utf-8\")" in dry_step
        assert "provider_file: (" in dry_step

        for secret_name, provider_file in provider_mappings.items():
            assert secret_name in dry_step
            assert provider_file in dry_step
            assert (
                f"dry-run-placeholder-{{provider_key.lower()}}"
                in dry_step
            )


def test_paid_runs_receive_only_the_selected_provider_secret() -> None:
    workflow_names = (
        "phase3-arm-dispatch-v2.yml",
        "phase3-arm-dispatch.yml",
    )
    provider_mappings = {
        "ANTHROPIC_API_KEY": "router-anthropic",
        "DEEPSEEK_API_KEY": "router-deepseek",
        "OPENAI_API_KEY": "router-gpt",
        "GEMINI_API_KEY": "router-gemini",
        "XAI_API_KEY": "router-grok",
        "MOONSHOT_API_KEY": "router-kimi",
        "DASHSCOPE_API_KEY": "router-qwen",
        "ZAI_API_KEY": "router-glm",
    }

    for name in workflow_names:
        text = (WORKFLOW_DIR / name).read_text()

        paid_step = text.split(
            "- name: Create paid runtime secret env files",
            1,
        )[1].split(
            "- name: Create runtime LiteLLM config",
            1,
        )[0]

        assert "if: ${{ inputs.dry_run == false }}" in paid_step

        for secret_name, arm_prefix in provider_mappings.items():
            conditional = (
                secret_name
                + ": ${{ startsWith(inputs.arm_id, '"
                + arm_prefix
                + "') && secrets."
                + secret_name
                + " || '' }}"
            )
            unconditional = (
                secret_name
                + ": ${{ secrets."
                + secret_name
                + " }}"
            )

            assert conditional in paid_step
            assert unconditional not in paid_step
