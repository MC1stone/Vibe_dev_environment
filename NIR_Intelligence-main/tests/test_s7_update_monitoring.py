"""S7 verification: update monitoring and calibration optimization protocol.

Tests the update monitor (requirements parsing, compose image extraction,
installed-version flagging, Quarto report rendering), the CLI script, and
the Optuna-based calibration optimization protocol (deferred gracefully when
Optuna is not installed). No network access required.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.update_monitor import (
    ComponentEntry,
    UpdateMonitorService,
    create_update_monitor,
)
from services.calibration_optimization import (
    OPTUNA_AVAILABLE,
    CalibrationOptimizationService,
    OptimizationProtocol,
    TrialRecord,
    create_calibration_optimization,
)

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


PROJECT = Path(__file__).resolve().parent.parent


# T1: requirements parsing (all three manifests, comments/markers skipped)
entries = UpdateMonitorService.parse_requirements(PROJECT / 'requirements.txt')
names = [e.name for e in entries]
check('T1a requirements.txt parsed', len(entries) > 30 and 'numpy' in names
      and 'qdrant-client' in names and 'optuna' in names, f'n={len(entries)}')
check('T1b comments and options skipped',
      all(not n.startswith('-') and not n.startswith('#') for n in names))
spec_sample = {e.name: e.declared for e in entries}
check('T1c specifiers preserved', spec_sample['numpy'].startswith('>='),
      f'numpy={spec_sample["numpy"]}')
check('T1d all parsed entries are pip components',
      all(e.kind == 'pip' for e in entries))


# T2: compose image extraction
images = UpdateMonitorService.parse_compose_images(PROJECT / 'docker-compose.yml')
image_names = [e.name for e in images]
check('T2a compose images extracted',
      'qdrant/qdrant' in image_names and 'ollama/ollama' in image_names
      and 'postgres' in image_names, f'n={len(images)}')
qdrant_entry = next(e for e in images if e.name == 'qdrant/qdrant')
check('T2b latest tag detected', qdrant_entry.declared == 'latest')


# T3: full scan against the real project (installed versions detected)
monitor = create_update_monitor(config={'project_root': str(PROJECT),
                                        'compose_files': ['docker-compose.yml']})
report = monitor.scan()
summary = report.summary()
check('T3a scan covers pip and docker components',
      summary['pip_components'] > 30 and summary['docker_components'] >= 3,
      f'total={summary["total_components"]} pip={summary["pip_components"]} docker={summary["docker_components"]}')
numpy_entry = next(c for c in report.components if c.name == 'numpy')
check('T3b installed version detected for numpy',
      numpy_entry.installed is not None, f'installed={numpy_entry.installed}')
flagged = [c for c in report.components if c.update_available]
check('T3c flagging logic produces a defined set',
      all(c.installed is not None for c in flagged), f'flagged={len(flagged)}')


# T4: specifier check semantics
check('T4a satisfied specifier -> no flag',
      UpdateMonitorService._specifier_allows_update('>=1.0.0', '2.5.3') is False)
check('T4b violated specifier -> flag',
      UpdateMonitorService._specifier_allows_update('<=1.0.0', '2.5.3') is True)
check('T4c latest declaration -> no offline decision',
      UpdateMonitorService._specifier_allows_update('latest', '2.5.3') is False)


# T5: Quarto report rendering
with tempfile.TemporaryDirectory() as tmp:
    out_dir = Path(tmp)
    report_path = monitor.render_quarto_report(report, output_dir=out_dir)
    text = report_path.read_text()
    check('T5a Quarto .qmd report written', report_path.suffix == '.qmd' and '---' in text.split('\n')[0])
    check('T5b report contains component tables',
          '| Package | Declared | Installed | Update flagged |' in text
          and '| Image | Tag |' in text)
    check('T5c report contains summary and recommendations',
          '## Summary' in text and 'Handlungsempfehlungen' in text
          and 'numpy' in text)


# T6: report to_dict is JSON-serializable
try:
    json.dumps(report.to_dict())
    check('T6 report JSON-serializable', True)
except Exception as exc:
    check('T6 report JSON-serializable', False, str(exc))


# T7: CLI script runs end to end (no network)
cli = subprocess.run(
    [sys.executable, str(PROJECT / 'scripts' / 'check_updates.py'),
     '--project-root', str(PROJECT), '--no-report'],
    capture_output=True, text=True, timeout=120,
)
check('T7a CLI exit code 0', cli.returncode == 0, f'stderr={cli.stderr[:200] if cli.returncode else ""}')
check('T7b CLI prints summary', 'total components' in cli.stdout and 'updates flagged' in cli.stdout)
cli_json = subprocess.run(
    [sys.executable, str(PROJECT / 'scripts' / 'check_updates.py'),
     '--project-root', str(PROJECT), '--json', '--no-report'],
    capture_output=True, text=True, timeout=120,
)
try:
    parsed = json.loads(cli_json.stdout)
    check('T7c CLI --json produces valid JSON report',
          'summary' in parsed and 'components' in parsed)
except Exception as exc:
    check('T7c CLI --json produces valid JSON report', False, str(exc)[:200])


# T8: calibration optimization protocol - Optuna or graceful deferral
opt_service = CalibrationOptimizationService(config={'n_trials': 5})
search_space = {'n_components': [2, 3, 4, 5], 'scale': [True, False],
                'method': ['PLS', 'PCR', 'SVM']}


def dummy_objective(params):
    return 0.5 + (params.get('n_components', 2) or 2) * 0.1


protocol = opt_service.optimize(dummy_objective, search_space)
if OPTUNA_AVAILABLE:
    check('T8a optuna study completed',
          protocol.status == 'complete' and protocol.optuna_used is True
          and protocol.n_trials == 5,
          f'trials={protocol.n_trials} best={protocol.best_score}')
    check('T8b best params recorded',
          protocol.best_method in ('PLS', 'PCR', 'SVM') and 'n_components' in protocol.best_params)
    check('T8c trial records kept', len(protocol.trials) == 5
          and all(isinstance(t, TrialRecord) for t in protocol.trials))
else:
    check('T8a optuna deferred gracefully (not installed)',
          protocol.status == 'deferred' and protocol.optuna_used is False
          and protocol.n_trials == 0)
    check('T8b deferred protocol still summarizes', isinstance(protocol.summary(), dict))
    check('T8c protocol dataclass intact', isinstance(protocol, OptimizationProtocol))


# T9: optimization service status + factory
status = opt_service.status()
check('T9 service status reports optuna availability',
      status['optuna_available'] == OPTUNA_AVAILABLE and status['n_trials'] == 5)
factory = create_calibration_optimization(config={'n_trials': 3})
check('T9b factory', isinstance(factory, CalibrationOptimizationService) and factory.n_trials == 3)


# T10: default search space includes the mission statement methods
from services.calibration_optimization import DEFAULT_METHODS
check('T10 default methods match mission statement calibration methods',
      set(DEFAULT_METHODS) == {'PLS', 'PCR', 'SVM', 'RandomForest', 'XGBoost', 'CNN'})


# T11: regressions spot checks (S5 engine, S6 chatbot)
from services.spectrum_similarity import SpectrumSimilarityEngine
import pandas as pd
engine = SpectrumSimilarityEngine()
engine.add_references([{'data': pd.DataFrame({'wavelength': [1, 2], 'intensity': [1.0, 2.0]}),
                        'wavelength_column': 'wavelength', 'intensity_column': 'intensity'}])
m = engine.find_similar({'data': pd.DataFrame({'wavelength': [1, 2], 'intensity': [1.0, 2.0]}),
                         'wavelength_column': 'wavelength', 'intensity_column': 'intensity'})
check('T11a S5 similarity regression spot check', len(m) == 1 and m[0].distance < 1e-6)
from services.chatbot_service import ChatbotService
svc = ChatbotService()
msgs, rag = svc.build_messages('Q?')
check('T11b S6 chatbot regression spot check',
      len(msgs) == 2 and msgs[0]['role'] == 'system' and rag['sources'] == [])


failed = [r for r in results if not r[1]]
print(f'\n{len(results) - len(failed)}/{len(results)} tests passed')
sys.exit(1 if failed else 0)
