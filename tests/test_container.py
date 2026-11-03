"""Static checks for the container image and the GitHub Actions workflows.

Docker is never run locally, so these keep the files consistent with the project rules, the
documentation and the application code.
"""

import ast
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app import __version__

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = (ROOT / "Dockerfile").read_text()
DOCKERIGNORE = [
    line.strip()
    for line in (ROOT / ".dockerignore").read_text().splitlines()
    if line.strip() and not line.startswith("#")
]
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
DOCKER_WORKFLOW = (ROOT / ".github" / "workflows" / "docker.yml").read_text()


def instructions(name: str) -> list[str]:
    """Arguments of every `name` instruction (line continuations joined)."""
    joined = re.sub(r"\\\n\s*", " ", DOCKERFILE)
    return [
        line.split(None, 1)[1].strip()
        for line in joined.splitlines()
        if line.upper().startswith(name + " ")
    ]


# --- Dockerfile ---


def test_base_image_and_runtime_settings() -> None:
    assert instructions("FROM") == ["python:3.12-slim"]
    assert instructions("EXPOSE") == ["8000"]
    assert instructions("VOLUME") == ["/data"]
    assert "TRAKKO_DB_PATH=/data/trakko.db" in " ".join(instructions("ENV"))


def test_runs_as_a_non_root_user_after_installing() -> None:
    users = instructions("USER")
    assert users and users[-1] not in ("root", "0")
    assert DOCKERFILE.index("pip install") < DOCKERFILE.index("USER ")


def test_data_directory_is_owned_by_that_user_before_the_volume_is_declared() -> None:
    assert re.search(r"chown trakko:trakko /data", DOCKERFILE)
    assert DOCKERFILE.index("chown trakko:trakko /data") < DOCKERFILE.index("VOLUME /data")


def test_healthcheck_uses_the_health_endpoint() -> None:
    (healthcheck,) = instructions("HEALTHCHECK")
    assert "/health" in healthcheck and "8000" in healthcheck


def test_migrations_run_before_the_server_and_it_listens_on_all_interfaces() -> None:
    (command,) = instructions("CMD")
    assert command.index("alembic upgrade head") < command.index("uvicorn app.main:app")
    assert "--host 0.0.0.0" in command and "--port 8000" in command
    assert "exec uvicorn" in command, "Uvicorn must receive stop signals"


def test_only_runtime_dependencies_are_installed() -> None:
    assert "requirements.txt" in DOCKERFILE
    assert "requirements-dev" not in DOCKERFILE


def test_copied_paths_exist_and_are_not_ignored() -> None:
    copied = [arg.split()[0] for arg in instructions("COPY")]
    assert {"alembic.ini", "alembic", "app"} <= set(copied)
    for name in copied:
        assert (ROOT / name).exists(), f"COPY {name}: no such file"
        ignored = [pattern for pattern in DOCKERIGNORE if fnmatch.fnmatch(name, pattern)]
        assert not ignored, f"COPY {name} is excluded by .dockerignore ({ignored})"


def test_dockerignore_excludes_what_the_project_requires() -> None:
    for entry in (".venv", ".git", "__pycache__", ".env", "tests", "docs"):
        assert entry in DOCKERIGNORE, f"{entry} missing from .dockerignore"
    for entry in ("*.db", "data"):
        assert entry in DOCKERIGNORE, "database files must not enter the build context"


def test_every_third_party_import_is_a_runtime_requirement() -> None:
    requirements = {
        re.split(r"[<>=!~\[ ]", line.strip(), maxsplit=1)[0].lower()
        for line in (ROOT / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    imported: set[str] = set()
    for path in [*(ROOT / "app").rglob("*.py"), ROOT / "alembic" / "env.py"]:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
    third_party = imported - set(sys.stdlib_module_names) - {"app"}
    assert third_party <= requirements, f"not in requirements.txt: {third_party - requirements}"
    assert {"uvicorn", "jinja2"} <= requirements, "needed at runtime, imported indirectly"


# --- Workflows ---


def test_workflows_are_plain_yaml_without_tabs() -> None:
    for text in (CI, DOCKER_WORKFLOW):
        assert "\t" not in text
        assert re.search(r"^name: ", text, re.M) and re.search(r"^jobs:\n", text, re.M)


def test_ci_runs_lint_and_tests_on_pull_requests_and_pushes() -> None:
    assert re.search(r"^on:\n(?:.*\n)*?\s+pull_request:", CI, re.M)
    assert re.search(r"^\s+push:\n\s+branches: \[main\]", CI, re.M)
    assert 'python-version: "3.12"' in CI
    assert "pip install -r requirements.txt -r requirements-dev.txt" in CI
    assert "ruff check ." in CI and "ruff format --check ." in CI
    assert re.search(r"run: pytest\s*$", CI, re.M)
    assert "contents: read" in CI


def test_docker_workflow_publishes_on_main_and_version_tags_only() -> None:
    assert re.search(r"push:\n\s+branches: \[main\]\n\s+tags: \[\"v\*\"\]", DOCKER_WORKFLOW)
    assert "pull_request" not in DOCKER_WORKFLOW, "no registry login for untrusted code"


def test_docker_workflow_pushes_to_ghcr_with_the_workflow_token() -> None:
    assert "REGISTRY: ghcr.io" in DOCKER_WORKFLOW
    assert "secrets.GITHUB_TOKEN" in DOCKER_WORKFLOW
    assert "packages: write" in DOCKER_WORKFLOW
    assert "docker/setup-buildx-action" in DOCKER_WORKFLOW
    assert "docker/login-action" in DOCKER_WORKFLOW
    assert "docker/metadata-action" in DOCKER_WORKFLOW
    assert "docker/build-push-action" in DOCKER_WORKFLOW
    assert "${GITHUB_REPOSITORY,,}" in DOCKER_WORKFLOW, "image names must be lowercase"


def test_docker_workflow_tags_match_the_deployment_guide() -> None:
    for rule in (
        "type=ref,event=branch",
        "type=sha",
        "type=semver,pattern={{version}}",
        "type=semver,pattern={{major}}.{{minor}}",
        "type=raw,value=latest",
    ):
        assert rule in DOCKER_WORKFLOW, rule
    guide = (ROOT / "docs" / "DEPLOYMENT.md").read_text()
    for tag in ("latest", "sha-", "1.2.3", "1.2"):
        assert tag in guide


def test_image_is_smoke_tested_before_it_is_pushed() -> None:
    smoke = DOCKER_WORKFLOW.index("Smoke test")
    push = DOCKER_WORKFLOW.index("push: true")
    assert smoke < push
    assert "load: true" in DOCKER_WORKFLOW
    assert "/health" in DOCKER_WORKFLOW and "id -u" in DOCKER_WORKFLOW


def test_readme_badges_point_at_the_workflow_files() -> None:
    readme = (ROOT / "README.md").read_text()
    for workflow in ("ci.yml", "docker.yml"):
        assert (ROOT / ".github" / "workflows" / workflow).exists()
        assert f"/actions/workflows/{workflow}" in readme


# --- release tags and the app version ---


def tag_check_script() -> str:
    """The shell code of the workflow step that compares the tag with `__version__`."""
    step = re.search(
        r"- name: Check that the tag matches the app version\n(.*?)\n\n", DOCKER_WORKFLOW, re.S
    ).group(1)
    body = step.split("run: |\n", 1)[1]
    return "\n".join(line[10:] for line in body.splitlines())


def run_tag_check(tag: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-e", "-c", tag_check_script()],
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "GITHUB_REF_NAME": tag},
        capture_output=True,
        text=True,
    )


def test_release_tags_are_checked_against_the_app_version() -> None:
    assert "if: startsWith(github.ref, 'refs/tags/v')" in DOCKER_WORKFLOW
    assert DOCKER_WORKFLOW.index("Check that the tag matches") < DOCKER_WORKFLOW.index(
        "Compute image name"
    )


def test_a_matching_tag_passes_the_check() -> None:
    assert run_tag_check(f"v{__version__}").returncode == 0


@pytest.mark.parametrize(
    "tag", ["v9.9.9", "v0.1.0", "0.1.0", "v0.1", f"{__version__}", "vv" + __version__]
)
def test_a_tag_that_does_not_match_fails_the_check(tag: str) -> None:
    result = run_tag_check(tag)

    assert result.returncode == 1
    assert "does not match the app version" in result.stderr


def test_the_version_lives_in_one_place() -> None:
    source = (ROOT / "app" / "__init__.py").read_text()

    assert re.findall(r'^__version__ = "([^"]+)"$', source, re.M) == [__version__]
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
