from __future__ import annotations

from dataclasses import dataclass

from pipeline_inspector.integrations.readiness.engine import run_readiness_checks
from pipeline_inspector.studio_config import ReadinessCheckRequirements, ReadinessSettings


@dataclass(frozen=True)
class FakeProbes:
    plugins: frozenset[str] = frozenset()
    maya_version_text: str = ""
    env: dict[str, str] | None = None
    paths: frozenset[str] = frozenset()
    drives: frozenset[str] = frozenset()
    versions: dict[str, str] | None = None

    def loaded_maya_plugins(self) -> frozenset[str]:
        return self.plugins

    def maya_version(self) -> str:
        return self.maya_version_text

    def env_var_value(self, name: str) -> str | None:
        env = self.env or {}
        value = env.get(name)
        if value is None:
            return None
        text = value.strip()
        return text or None

    def path_exists(self, path: str) -> bool:
        return path in self.paths

    def drive_mapped(self, drive: str) -> bool:
        return drive.upper() in self.drives or drive in self.drives

    def software_version(self, product: str) -> str | None:
        versions = self.versions or {}
        return versions.get(product)


def test_run_readiness_checks_reports_all_categories():
    readiness = ReadinessSettings(
        checks=ReadinessCheckRequirements(
            maya_plugins=("mtoa",),
            mapped_drives=("Z",),
            env_vars=("PIPELINE_ROOT",),
            network_paths=("\\\\farm\\textures",),
            software_versions={"maya": "2025"},
        )
    )
    probes = FakeProbes(
        plugins=frozenset({"mtoa"}),
        maya_version_text="Maya 2025.3",
        env={"PIPELINE_ROOT": "D:/pipeline"},
        paths=frozenset({"\\\\farm\\textures"}),
        drives=frozenset({"Z"}),
    )

    report = run_readiness_checks(
        readiness,
        probes=probes,
        host_name="ws-01",
        maya_version="Maya 2025.3",
    )

    assert report.ok is True
    assert len(report.results) == 5
    assert report.summary == "All 5 readiness checks passed."


def test_run_readiness_checks_marks_missing_plugin_env_and_path_failures():
    readiness = ReadinessSettings(
        checks=ReadinessCheckRequirements(
            maya_plugins=("vrayformaya",),
            env_vars=("STUDIO_TEXTURE_ROOT",),
            network_paths=("\\\\farm\\missing",),
        )
    )
    probes = FakeProbes(plugins=frozenset(), env={}, paths=frozenset())

    report = run_readiness_checks(readiness, probes=probes, host_name="ws-02")

    assert report.ok is False
    assert sum(1 for result in report.results if not result.ok) == 3
    assert any(result.category == "maya_plugin" for result in report.results)
    assert any(result.category == "env_var" for result in report.results)
    assert any(result.category == "network_path" for result in report.results)


def test_run_readiness_checks_with_no_configuration_is_passing_idle_state():
    report = run_readiness_checks(ReadinessSettings(), probes=FakeProbes())

    assert report.ok is True
    assert report.results == ()
    assert report.summary == "No readiness checks are configured."
