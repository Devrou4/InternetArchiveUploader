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
    assert workflow["jobs"]["build-linux"]["strategy"]["matrix"]["os"] == [
        "ubuntu-22.04",
        "ubuntu-24.04",
    ]


def test_build_matrix_covers_supported_windows(workflow):
    assert workflow["jobs"]["build-windows"]["strategy"]["matrix"]["os"] == [
        "windows-2022",
        "windows-2025",
    ]


def test_windows_job_builds_an_exe_bundle(workflow):
    steps = workflow["jobs"]["build-windows"]["steps"]
    run_blocks = "\n".join(step.get("run", "") for step in steps)

    assert "packaging/windows.spec" in run_blocks
    assert "smoke_dist.py" in run_blocks
    assert "Compress-Archive" in run_blocks


def test_windows_artifact_is_verified_on_windows(workflow):
    job = workflow["jobs"]["verify-windows"]
    run_blocks = "\n".join(step.get("run", "") for step in job["steps"])

    assert job["strategy"]["matrix"]["os"] == ["windows-2022", "windows-2025"]
    assert "Expand-Archive" in run_blocks
    assert "--smoke-test" in run_blocks


def test_release_waits_for_both_platforms(workflow):
    needs = workflow["jobs"]["release"]["needs"]

    assert "build-linux" in needs
    assert "build-windows" in needs


def test_release_publishes_windows_zip(workflow):
    steps = workflow["jobs"]["release"]["steps"]
    files = "\n".join(str(step.get("with", {}).get("files", "")) for step in steps)

    assert "*.zip" in files
    assert "*.tar.gz" in files


def test_no_secrets_are_used(workflow):
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")


def test_workflow_does_not_use_pull_request_target(workflow):
    triggers = workflow["on"] if "on" in workflow else workflow[True]

    assert "pull_request_target" not in triggers


def test_artifact_is_checksummed_before_release(workflow):
    for job in ("build-linux", "build-windows"):
        run_blocks = "\n".join(
            step.get("run", "") for step in workflow["jobs"][job]["steps"]
        )
        assert "packaging_contract" in run_blocks
        assert "SHA256" in run_blocks or "sha256sum" in run_blocks

def test_build_inputs_are_tracked_by_git():
    """A spec ignored by .gitignore silently breaks CI packaging."""
    import subprocess

    root = Path(__file__).resolve().parent.parent
    tracked = subprocess.run(
        ["git", "ls-files", "packaging", ".github", "scripts"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert "packaging/linux.spec" in tracked
    assert ".github/workflows/build-linux.yml" in tracked
    assert "scripts/smoke_dist.py" in tracked
