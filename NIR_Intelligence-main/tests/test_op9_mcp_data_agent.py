#!/usr/bin/env python3
# OP9: MCP data agent - interface registry + dataset ingestion
# Offline test matrix (no network, no containers). Style: repo check() suites.

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

results = []


def check(name, ok, detail=''):
    status = 'PASS' if ok else 'FAIL'
    print(f'[{status}] {name}' + (f' {detail}' if detail else ''))
    results.append((name, bool(ok)))


# ---------------------------------------------------------------- T1: interfaces
from agents.mcp_agent import MCPAgent

mcp = MCPAgent()
check('T1a mcp agent instantiates with data operations',
      hasattr(mcp, '_interfaces') and hasattr(mcp, '_ingest'))

out = mcp.execute({'operation': 'interfaces'})
check('T1b interfaces operation succeeds',
      out.data.get('status') == 'ok' and out.data.get('operation') == 'interfaces')

names = [i.get('name') for i in out.data.get('interfaces', [])]
check('T1c interface registry lists upload, crew analysis, report, ingest',
      {'upload_file', 'crew_analysis', 'analysis_report', 'ingest_dataset'}
      <= set(names), f'names={names}')

# ---------------------------------------------------------------- T2: ingest
tmp_dir = Path(tempfile.mkdtemp(prefix='op9_ingest_'))

german_csv = tmp_dir / 'diy_spectrum.csv'
german_csv.write_text(
    'Messung;Intensität (counts, ADU)\n'
    'Daten;Rohwerte\n'
    '900;15.200,00\n'
    '925;18.450,00\n'
    '950;22.100,00\n'
    '975;25.800,00\n'
    '1000;29.400,00\n'
    '1025;33.100,00\n'
    '1050;36.800,00\n'
    '1075;40.200,00\n'
    '1100;43.500,00\n'
    '1125;44.800,00\n'
    '1150;42.900,00\n'
    '1175;39.100,00\n'
    '1200;33.500,00\n'
    '1225;26.900,00\n'
    '1250;20.200,00\n'
    '1275;15.800,00\n'
    '1300;46.000,00\n'
    '1325;21.000,00\n', encoding='utf-8')

out = mcp.execute({'operation': 'ingest', 'file_path': str(german_csv)})
data = out.data
check('T2a ingest of German DIY CSV succeeds',
      data.get('status') == 'ok', f'status={data.get("status")} error={data.get("error")}')

prepared = data.get('prepared_dataset') or {}
check('T2b prepared dataset has 18 bands with the 46k spike intact',
      prepared.get('num_points') == 18
      and prepared.get('intensities', [])[16] == 46000.0
      and prepared.get('ready_for') == 'statistical_analysis',
      f'num_points={prepared.get("num_points")}')

check('T2c metadata extracted from non-spectral rows',
      isinstance(data.get('metadata'), dict), f'metadata={data.get("metadata")}')

# format-agnostic check: JSON input goes through the same path
json_file = tmp_dir / 'spectrum.json'
json_file.write_text(json.dumps({
    'wavelength': [900, 925, 950, 1300],
    'intensity': [15200, 18450, 22100, 46000],
}))
out = mcp.execute({'operation': 'ingest', 'file_path': str(json_file)})
check('T2d ingest is format-agnostic (JSON parses too)',
      out.data.get('status') == 'ok'
      and out.data['prepared_dataset']['num_points'] == 4,
      f'status={out.data.get("status")}')

out = mcp.execute({'operation': 'ingest', 'file_path': ''})
check('T2e ingest without file_path fails loudly',
      str(out.status) == 'AgentStatus.ERROR' and out.errors != [],
      f'status={out.status} errors={[e.message for e in out.errors]}')

out = mcp.execute({'operation': 'ingest', 'file_path': str(tmp_dir / 'missing.csv')})
check('T2f ingest of missing file reports error, no crash',
      out.data.get('status') == 'error'
      and out.data.get('error') == 'file not found')

# ---------------------------------------------------------------- T3: prepared data feeds statistics
from agents.statistical_analysis_agent import StatisticalAnalysisAgent

prepared_spectrum = prepared.get('intensities') or []
stat = StatisticalAnalysisAgent()
stat_out = stat.execute({'spectra': [prepared_spectrum],
                         'wavelengths': prepared.get('wavelengths') or []})
methods = (stat_out.data or {}).get('methods_applied', [])
ds = (stat_out.data or {}).get('method_results', {}).get('DescriptiveStatistics', {})
check('T3a prepared dataset runs through statistical analysis',
      stat_out.data.get('status') == 'ok' and 'DescriptiveStatistics' in methods,
      f'methods={methods}')
check('T3b outlier spike at band 16 detected in the prepared data',
      (ds.get('outliers') or {}).get('indices') == [16],
      f'outliers={(ds.get("outliers") or {}).get("indices")}')

# ---------------------------------------------------------------- T4: stdio MCP server
server = PROJECT / 'services' / 'mcp_data_server.py'
check('T4a mcp data server file exists', server.is_file())

proc = subprocess.run(
    [sys.executable, str(server)],
    input='\n'.join([
        json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                    'params': {}}),
        json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}),
        json.dumps({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                    'params': {'name': 'ingest_dataset',
                               'arguments': {'file_path': str(german_csv)}}}),
    ]),
    capture_output=True, text=True, timeout=120,
)

lines = [l for l in proc.stdout.strip().splitlines() if l.strip()]
responses = [json.loads(l) for l in lines]
by_id = {r.get('id'): r for r in responses}

check('T4b server initializes with protocol version',
      by_id.get(1, {}).get('result', {}).get('protocolVersion') == '2024-11-05',
      proc.stderr[-200:] if proc.returncode else '')

tool_names = [t.get('name') for t in
              by_id.get(2, {}).get('result', {}).get('tools', [])]
check('T4c tools/list exposes the three data tools',
      {'list_interfaces', 'ingest_dataset', 'tool_status'} <= set(tool_names),
      f'tools={tool_names}')

ingest_content = (by_id.get(3, {}).get('result', {})
                  .get('content', [{}])[0].get('text', ''))
ingest_payload = json.loads(ingest_content) if ingest_content else {}
check('T4d ingest_dataset tool returns the prepared 18-band dataset',
      ingest_payload.get('status') == 'ok'
      and (ingest_payload.get('prepared_dataset') or {}).get('num_points') == 18,
      f'keys={sorted(ingest_payload.keys())[:6]}')

# ---------------------------------------------------------------- summary
print()
failed = [name for name, ok in results if not ok]
print(f'{len(results) - len(failed)}/{len(results)} tests passed')
if failed:
    print('FAILED:', failed)
    sys.exit(1)
