# NIR Intelligence Platform - Update monitor service (roadmap S7, MO 15)
# Checks the open-source components used by the platform (pip requirements,
# Docker images) for available updates by comparing the declared versions in
# the local manifests against the locally installed/available versions.
# Produces a report (Quarto .qmd) - updates remain deliberate deployment
# decisions, no auto-update is performed.

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ComponentEntry:
    """One monitored open-source component"""

    name: str
    kind: str  # 'pip' or 'docker'
    declared: str  # specifier as written in the manifest (e.g. '>=1.9.0', 'latest')
    installed: Optional[str] = None
    update_available: Optional[bool] = None
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "declared": self.declared,
            "installed": self.installed,
            "update_available": self.update_available,
            "note": self.note,
        }


@dataclass
class UpdateReport:
    """Result of one update-monitoring run"""

    generated_at: str = ""
    components: List[ComponentEntry] = field(default_factory=list)
    pip_manifests_scanned: List[str] = field(default_factory=list)
    compose_files_scanned: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        total = len(self.components)
        pip_count = sum(1 for c in self.components if c.kind == "pip")
        docker_count = total - pip_count
        flagged = sum(1 for c in self.components if c.update_available)
        return {
            "total_components": total,
            "pip_components": pip_count,
            "docker_components": docker_count,
            "updates_flagged": flagged,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "summary": self.summary(),
            "components": [c.to_dict() for c in self.components],
            "pip_manifests_scanned": self.pip_manifests_scanned,
            "compose_files_scanned": self.compose_files_scanned,
        }


class UpdateMonitorService:
    """Scans local manifests and reports component update status (S7)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        project_root = Path(self.config.get("project_root", "."))
        self.project_root = project_root

    # ---------- manifest parsing ----------

    @staticmethod
    def parse_requirements(path: Path) -> List[ComponentEntry]:
        """Parse a pip requirements file into component entries."""
        entries: List[ComponentEntry] = []
        if not path.exists():
            return entries
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # strip environment markers and comments
            line = line.split(";")[0].strip()
            # strip inline comments
            line = re.split(r"\s+#", line)[0].strip()
            match = re.match(r"^([A-Za-z0-9._-]+)\s*(.*)$", line)
            if not match:
                continue
            name, specifier = match.group(1), match.group(2).strip()
            if not specifier:
                specifier = "latest"
            entries.append(ComponentEntry(name=name.lower(), kind="pip",
                                          declared=specifier))
        return entries

    @staticmethod
    def parse_compose_images(path: Path) -> List[ComponentEntry]:
        """Extract docker image references from a compose file."""
        entries: List[ComponentEntry] = []
        if not path.exists():
            return entries
        text = path.read_text()
        for match in re.finditer(r"image:\s*([A-Za-z0-9._/:@-]+)", text):
            reference = match.group(1)
            if "/" in reference and ":" in reference:
                name, _, tag = reference.rpartition(":")
            elif "/" in reference:
                name, tag = reference, "latest"
            else:
                name, _, tag = reference.rpartition(":")
                if not name:
                    name, tag = reference, "latest"
            entries.append(ComponentEntry(name=name, kind="docker", declared=tag))
        return entries

    # ---------- installed version detection ----------

    @staticmethod
    def installed_pip_version(name: str) -> Optional[str]:
        """Best-effort local installed version for a pip package (no network)."""
        try:
            import importlib.metadata as metadata

            return metadata.version(name)
        except Exception:
            return None

    # ---------- report generation ----------

    def scan(self) -> UpdateReport:
        """Scan manifests, detect local versions and flag potential updates."""
        report = UpdateReport(generated_at=datetime.now().isoformat())

        requirements_files = sorted(self.project_root.glob("requirements*.txt"))
        for req_path in requirements_files:
            entries = self.parse_requirements(req_path)
            report.pip_manifests_scanned.append(str(req_path.name))
            for entry in entries:
                if entry.kind == "pip":
                    entry.installed = self.installed_pip_version(entry.name)
                    if entry.installed is None:
                        entry.note = "not installed locally"
                    else:
                        entry.update_available = self._specifier_allows_update(
                            entry.declared, entry.installed)
                        if entry.update_available:
                            entry.note = "installed version outside declared range - review manifest"
                report.components.append(entry)

        for compose_name in self.config.get("compose_files", ["docker-compose.yml"]):
            compose_path = self.project_root / compose_name
            entries = self.parse_compose_images(compose_path)
            if entries:
                report.compose_files_scanned.append(compose_name)
            for entry in entries:
                if entry.declared == "latest":
                    entry.note = "uses 'latest' tag - pin a version for reproducibility"
                    entry.update_available = None
                else:
                    entry.note = "pinned tag - compare with upstream registry"
                    entry.update_available = None
                report.components.append(entry)

        return report

    @staticmethod
    def _specifier_allows_update(declared: str, installed: str) -> bool:
        """Flag when the installed version does not satisfy the declared spec.

        For 'latest' declarations nothing can be decided offline; for concrete
        specifiers the local version is checked against the constraint.
        """
        if declared in ("", "latest"):
            return False
        try:
            from packaging.requirements import Requirement

            requirement = Requirement(f"pkg{declared}")
            return not requirement.specifier.contains(installed, prereleases=True)
        except Exception:
            return False

    def render_quarto_report(self, report: UpdateReport, output_dir: Optional[Path] = None) -> Path:
        """Render the update report as a Quarto .qmd document."""
        output_dir = output_dir or self.project_root / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"update_report_{timestamp}.qmd"
        report_path.write_text(self._quarto_markdown(report))
        return report_path

    def _quarto_markdown(self, report: UpdateReport) -> str:
        summary = report.summary()
        lines: List[str] = [
            "---",
            "title: \"NIR-IP Update Report\"",
            f"date: \"{report.generated_at}\"",
            "format: html",
            "---",
            "",
            "# Component Update Report (S7)",
            "",
            f"Generated: {report.generated_at}",
            "",
            "## Summary",
            "",
            f"- Total components: {summary['total_components']}",
            f"- pip components: {summary['pip_components']}",
            f"- Docker components: {summary['docker_components']}",
            f"- Updates flagged: {summary['updates_flagged']}",
            "",
            "## pip components",
            "",
            "| Package | Declared | Installed | Update flagged | Note |",
            "|---|---|---|---|---|",
        ]
        for c in report.components:
            if c.kind == "pip":
                flagged = "yes" if c.update_available else ("n/a" if c.update_available is None else "no")
                lines.append(f"| {c.name} | {c.declared} | {c.installed or '-'} | {flagged} | {c.note or ''} |")
        lines += ["", "## Docker images", "",
                  "| Image | Tag | Note |", "|---|---|---|"]
        for c in report.components:
            if c.kind == "docker":
                lines.append(f"| {c.name} | {c.declared} | {c.note or ''} |")
        lines += [
            "",
            "## Handlungsempfehlungen",
            "",
            "- Flagged pip packages: manifest and installed version differ -",
            "  review the declared specifier before deployment.",
            "- Docker images with 'latest': pin an explicit version for",
            "  reproducible deployments.",
            "- Updates are deliberate deployment decisions (no auto-update).",
            "",
        ]
        return "\n".join(lines)


def create_update_monitor(config: Optional[Dict[str, Any]] = None) -> UpdateMonitorService:
    """Factory used by scripts/CI to get the update monitor"""
    return UpdateMonitorService(config=config)
