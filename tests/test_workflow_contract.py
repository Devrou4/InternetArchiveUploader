from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "build-linux.yml"


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_triggers_cover_pr_push_tags_and_dispatch(workflow):
    triggers = workflow["on"] if "on" in workflow else workflow[True]

    assert "pull_request" in triggers
    assert "push" in triggers
    assert "workflow_dispatch" in triggers
    assert "v*" in triggers["push"]["tags"]


def test_default_permissions_are_read_only(workflow):
    assert workflow["permissions"]["contents"] == "read"


def test_release_only_runs_for_tags(workflow):
    assert workflow["jobs"]["release"]["if"] == "startsWith(github.ref, 'refs/tags/v')"
    assert workflow["jobs"]["release"]["permissions"]["contents"] == "write"


def test_build_matrix_covers_supported_ubuntu(workflow):
    assert workflow["jobs"]["build"]["strategy"]["matrix"]["os"] == [
        "ubuntu-22.04",
        "ubuntu-24.04",
    ]


def test_no_secrets_are_used(workflow):
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")


def test_workflow_does_not_use_pull_request_target(workflow):
    triggers = workflow["on"] if "on" in workflow else workflow[True]

    assert "pull_request_target" not in triggers


def test_artifact_is_checksummed_before_release(workflow):
    steps = workflow["jobs"]["build"]["steps"]
    run_blocks = "\n".join(step.get("run", "") for step in steps)

    assert "sha256sum" in run_blocks
    assert "packaging_contract" in run_blocks