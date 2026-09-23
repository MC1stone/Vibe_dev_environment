"""Django management command: start the dev server on a free port.

Uses the existing Port Management Agent (port_manager app, agents/port_agent)
to find a free port in the given range and starts the development server on
it. Replaces the hard-coded 'runserver 127.0.0.1:8080' workflow where a busy
port aborts the start.

Usage:
    python manage.py runserver_free
    python manage.py runserver_free --port 8080
    python manage.py runserver_free --range 8000-8100 --host 127.0.0.1
"""
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from path_config import setup_project_paths  # noqa: E402

setup_project_paths()

from agents.port_agent import PortManagementAgentCrewAI  # noqa: E402


class Command(BaseCommand):
    help = ('Start the Django development server on a free port found by '
            'the Port Management Agent')

    def add_arguments(self, parser):
        parser.add_argument(
            '--port', type=int,
            help='Preferred port; falls back to the next free port in range when taken',
        )
        parser.add_argument(
            '--range', type=str, default='8000-8100',
            help='Port range to search when the preferred port is taken (start-end)',
        )
        parser.add_argument(
            '--host', type=str, default='127.0.0.1',
            help='Host address to bind (default: 127.0.0.1, loopback only)',
        )
        parser.add_argument(
            '--noreload', action='store_true',
            help='Disable the auto-reloader',
        )

    def handle(self, *args, **options):
        host = options['host']
        port = options['port']
        start, end = 8000, 8100
        if options['range']:
            parts = options['range'].split('-')
            start = int(parts[0]) if len(parts) > 0 else 8000
            end = int(parts[1]) if len(parts) > 1 else 8100

        agent = PortManagementAgentCrewAI()
        if not agent.initialize().get('success'):
            raise CommandError('Port Management Agent could not be initialized')

        if port is not None:
            check = agent.check_port(port, host=host)
            if check.get('available'):
                chosen = port
            else:
                self.stdout.write(self.style.WARNING(
                    f'Port {port} is already in use - searching {start}-{end}'))
                chosen = None
        if port is None or chosen is None:
            found = agent.find_free_port(start, end, host=host)
            if not found.get('success'):
                raise CommandError(f'No free port found in range {start}-{end}')
            chosen = found['port']

        self.stdout.write(self.style.SUCCESS(
            f'Starting development server on {host}:{chosen} '
            f'(port found by the Port Management Agent)'))

        from django.core.management import call_command
        call_command(
            'runserver',
            f'{host}:{chosen}',
            noreload=options['noreload'],
        )
