#!/usr/bin/env python3
# NIR Intelligence Platform - Update check CLI (roadmap S7, MO 15)
# Scans pip manifests and docker-compose images for component status and
# renders a Quarto report. Intended for CI jobs or manual runs:
#   python3 scripts/check_updates.py [--project-root .] [--json]
# No network access required: all checks are local-manifest based.

import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from services.update_monitor import create_update_monitor


def main() -> int:
    parser = argparse.ArgumentParser(description="NIR-IP component update monitor")
    parser.add_argument("--project-root", default=str(project_root),
                        help="project root containing requirements*.txt and compose files")
    parser.add_argument("--compose-files", nargs="*",
                        default=["docker-compose.yml", "docker-compose.prod.yml"],
                        help="compose files to scan for images")
    parser.add_argument("--json", action="store_true", help="print report as JSON")
    parser.add_argument("--no-report", action="store_true",
                        help="skip Quarto report rendering")
    args = parser.parse_args()

    monitor = create_update_monitor(config={
        "project_root": args.project_root,
        "compose_files": args.compose_files,
    })
    report = monitor.scan()

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        summary = report.summary()
        print(f"Update report generated: {report.generated_at}")
        print(f"  pip manifests scanned:  {', '.join(report.pip_manifests_scanned)}")
        print(f"  compose files scanned:  {', '.join(report.compose_files_scanned) or '-'}")
        print(f"  total components: {summary['total_components']} "
              f"(pip: {summary['pip_components']}, docker: {summary['docker_components']})")
        print(f"  updates flagged:   {summary['updates_flagged']}")
        for component in report.components:
            if component.update_available:
                print(f"  [FLAG] {component.name}: declared {component.declared}, "
                      f"installed {component.installed}")

    if not args.no_report:
        report_path = monitor.render_quarto_report(report)
        if not args.json:
            print(f"Quarto report written to: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
