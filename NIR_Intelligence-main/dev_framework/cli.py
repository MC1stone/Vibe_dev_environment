#!/usr/bin/env python3
"""
DeveloperAgent Framework - Command Line Interface

Provides CLI commands for agent development workflow
"""

import argparse
import sys
import logging
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DevFrameworkCLI')


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser"""
    parser = argparse.ArgumentParser(
        description='NIR Intelligence Platform - Developer Agent Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate a new agent
  python -m dev_framework generate agent SensorQualityAgent

  # Generate agent with specific template
  python -m dev_framework generate agent CalibrationAgent --template ml

  # Validate all agents
  python -m dev_framework validate

  # Validate specific agent
  python -m dev_framework validate --agent data_preparation_agent

  # Run tests for all agents
  python -m dev_framework test

  # Run tests for specific agent
  python -m dev_framework test --agent neural_network_agent

  # Start development server
  python -m dev_framework serve

  # Check code quality
  python -m dev_framework quality

  # Generate documentation
  python -m dev_framework docs
        '''
    )
    
    # Main subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        title='Available Commands',
        required=True
    )
    
    # Generate command
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generate new agents, tests, or documentation'
    )
    generate_subparsers = generate_parser.add_subparsers(
        dest='generate_type',
        required=True
    )
    
    # Generate agent
    agent_parser = generate_subparsers.add_parser(
        'agent',
        help='Generate a new agent'
    )
    agent_parser.add_argument(
        'name',
        type=str,
        help='Name of the agent (e.g., SensorQualityAgent)'
    )
    agent_parser.add_argument(
        '--template',
        type=str,
        default='default',
        choices=['default', 'data', 'ml', 'db', 'api', 'analysis'],
        help='Template type for the agent'
    )
    agent_parser.add_argument(
        '--no-python',
        action='store_true',
        help='Skip Python file generation'
    )
    agent_parser.add_argument(
        '--no-json',
        action='store_true',
        help='Skip JSON configuration generation'
    )
    agent_parser.add_argument(
        '--no-tests',
        action='store_true',
        help='Skip test file generation'
    )
    agent_parser.add_argument(
        '--no-docs',
        action='store_true',
        help='Skip documentation generation'
    )
    agent_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files'
    )
    
    # Generate tests
    tests_parser = generate_subparsers.add_parser(
        'tests',
        help='Generate test files'
    )
    tests_parser.add_argument(
        '--agent',
        type=str,
        help='Generate tests for specific agent'
    )
    tests_parser.add_argument(
        '--all',
        action='store_true',
        help='Generate tests for all agents'
    )
    tests_parser.add_argument(
        '--type',
        type=str,
        default='all',
        choices=['unit', 'integration', 'e2e', 'all'],
        help='Type of tests to generate'
    )
    
    # Generate docs
    docs_parser = generate_subparsers.add_parser(
        'docs',
        help='Generate documentation'
    )
    docs_parser.add_argument(
        '--agent',
        type=str,
        help='Generate docs for specific agent'
    )
    docs_parser.add_argument(
        '--all',
        action='store_true',
        help='Generate docs for all agents'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate agents and configuration'
    )
    validate_parser.add_argument(
        '--agent',
        type=str,
        help='Validate specific agent'
    )
    validate_parser.add_argument(
        '--all',
        action='store_true',
        default=True,
        help='Validate all agents'
    )
    validate_parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict validation (fail on warnings)'
    )
    validate_parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to auto-fix issues'
    )
    
    # Test command
    test_parser = subparsers.add_parser(
        'test',
        help='Run agent tests'
    )
    test_parser.add_argument(
        '--agent',
        type=str,
        help='Test specific agent'
    )
    test_parser.add_argument(
        '--all',
        action='store_true',
        default=True,
        help='Test all agents'
    )
    test_parser.add_argument(
        '--type',
        type=str,
        default='all',
        choices=['unit', 'integration', 'e2e', 'all'],
        help='Type of tests to run'
    )
    test_parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run with coverage reporting'
    )
    test_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    test_parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch for changes and re-run tests'
    )
    
    # Quality command
    quality_parser = subparsers.add_parser(
        'quality',
        help='Check and enforce code quality'
    )
    quality_parser.add_argument(
        '--check',
        action='store_true',
        help='Check quality without fixing'
    )
    quality_parser.add_argument(
        '--fix',
        action='store_true',
        help='Auto-fix quality issues'
    )
    quality_parser.add_argument(
        '--agent',
        type=str,
        help='Check specific agent'
    )
    quality_parser.add_argument(
        '--all',
        action='store_true',
        default=True,
        help='Check all agents'
    )
    
    # Serve command
    serve_parser = subparsers.add_parser(
        'serve',
        help='Start development server with hot-reload'
    )
    serve_parser.add_argument(
        '--port',
        type=int,
        default=8001,
        help='Port to run server on'
    )
    serve_parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='Host to bind to'
    )
    serve_parser.add_argument(
        '--agent',
        type=str,
        help='Serve specific agent in isolation'
    )
    serve_parser.add_argument(
        '--no-reload',
        action='store_true',
        help='Disable hot-reload'
    )
    
    # Info command
    subparsers.add_parser(
        'info',
        help='Show framework and project information'
    )
    
    # Clean command
    clean_parser = subparsers.add_parser(
        'clean',
        help='Clean build artifacts and cache'
    )
    clean_parser.add_argument(
        '--all',
        action='store_true',
        help='Clean everything including node_modules, __pycache__, etc.'
    )
    clean_parser.add_argument(
        '--tests',
        action='store_true',
        help='Clean test artifacts'
    )
    clean_parser.add_argument(
        '--docs',
        action='store_true',
        help='Clean documentation artifacts'
    )
    
    return parser


def run_generate(args: argparse.Namespace) -> int:
    """Handle generate command"""
    from .generator import AgentGenerator, TestGenerator, DocsGenerator
    
    if args.generate_type == 'agent':
        generator = AgentGenerator()
        result = generator.generate_agent(
            name=args.name,
            template=args.template,
            generate_python=not args.no_python,
            generate_json=not args.no_json,
            generate_tests=not args.no_tests,
            generate_docs=not args.no_docs,
            force=args.force
        )
        if result.success:
            logger.info(f"Agent '{args.name}' generated successfully!")
            for file in result.files_created:
                logger.info(f"  Created: {file}")
            return 0
        else:
            logger.error(f"Failed to generate agent: {result.error}")
            return 1
            
    elif args.generate_type == 'tests':
        generator = TestGenerator()
        if args.all:
            result = generator.generate_all_tests(test_type=args.type)
        elif args.agent:
            result = generator.generate_agent_tests(
                agent_name=args.agent,
                test_type=args.type
            )
        else:
            logger.error("Please specify --agent or --all")
            return 1
            
        if result['success']:
            logger.info(f"Tests generated successfully!")
            for file in result['files_created']:
                logger.info(f"  Created: {file}")
            return 0
        else:
            logger.error(f"Failed to generate tests: {result['error']}")
            return 1
            
    elif args.generate_type == 'docs':
        generator = DocsGenerator()
        if args.all:
            result = generator.generate_all_docs()
        elif args.agent:
            result = generator.generate_agent_docs(agent_name=args.agent)
        else:
            logger.error("Please specify --agent or --all")
            return 1
            
        # Handle both dictionary and object results
        if isinstance(result, dict):
            if result['success']:
                logger.info(f"Documentation generated successfully!")
                for file in result['files_created']:
                    logger.info(f"  Created: {file}")
                return 0
            else:
                logger.error(f"Failed to generate docs: {result.get('error', 'Unknown error')}")
                return 1
        else:
            if result.success:
                logger.info(f"Documentation generated successfully!")
                for file in result.files_created:
                    logger.info(f"  Created: {file}")
                return 0
            else:
                logger.error(f"Failed to generate docs: {result.error if hasattr(result, 'error') else 'Unknown error'}")
                return 1
    
    return 0


def run_validate(args: argparse.Namespace) -> int:
    """Handle validate command"""
    from .validator import AgentValidator
    
    validator = AgentValidator(strict=args.strict)
    
    if args.all:
        result = validator.validate_all()
    elif args.agent:
        result = validator.validate_agent(args.agent)
    else:
        logger.error("Please specify --agent or --all")
        return 1
    
    if result.valid:
        logger.info("Validation passed!")
        if result.warnings:
            logger.warning(f"Warnings: {len(result.warnings)}")
            for warning in result.warnings:
                logger.warning(f"  - {warning.message}")
        return 0
    else:
        logger.error("Validation failed!")
        for error in result.errors:
            logger.error(f"  - {error.message}")
        if args.fix:
            logger.info("Attempting to auto-fix issues...")
            fix_result = validator.fix_issues(result.errors)
            if fix_result['success']:
                logger.info(f"Fixed {fix_result['fixed_count']} issues")
                return 0
            else:
                logger.error(f"Failed to fix: {fix_result['error']}")
        return 1


def run_test(args: argparse.Namespace) -> int:
    """Handle test command"""
    from .tester import AgentTester
    
    tester = AgentTester(verbose=args.verbose)
    
    if args.all:
        result = tester.run_all_tests(
            test_type=args.type,
            with_coverage=args.coverage
        )
    elif args.agent:
        result = tester.run_agent_tests(
            agent_name=args.agent,
            test_type=args.type,
            with_coverage=args.coverage
        )
    else:
        logger.error("Please specify --agent or --all")
        return 1
    
    # Handle both dictionary and object results
    if isinstance(result, dict):
        if result['success']:
            logger.info(f"Tests passed! {result['passed']} passed, {result['failed']} failed")
            if args.coverage:
                logger.info(f"Coverage: {result['coverage']}%")
            return 0 if result['failed'] == 0 else 1
        else:
            logger.error(f"Test execution failed: {result.get('error_message', result.get('error', 'Unknown error'))}")
            return 1
    else:
        if result.success:
            logger.info(f"Tests passed! {result.passed} passed, {result.failed} failed")
            if args.coverage:
                logger.info(f"Coverage: {result.coverage}%")
            return 0 if result.failed == 0 else 1
        else:
            logger.error(f"Test execution failed: {result.error_message or 'Unknown error'}")
            return 1


def run_quality(args: argparse.Namespace) -> int:
    """Handle quality command"""
    from .quality import QualityEnforcer
    
    enforcer = QualityEnforcer()
    
    if args.all:
        if args.check:
            result = enforcer.check_all()
        elif args.fix:
            result = enforcer.fix_all()
        else:
            result = enforcer.check_all()
    elif args.agent:
        if args.check:
            result = enforcer.check_agent(args.agent)
        elif args.fix:
            result = enforcer.fix_agent(args.agent)
        else:
            result = enforcer.check_agent(args.agent)
    else:
        logger.error("Please specify --agent or --all")
        return 1
    
    if result.success:
        if hasattr(result, 'issues') and result.issues:
            for issue in result.issues:
                logger.info(f"{issue.severity}: {issue.message} ({issue.file}:{issue.line})")
        return 0
    else:
        logger.error(f"Quality check failed with {len(result.issues) if hasattr(result, 'issues') else 0} issues")
        return 1


def run_serve(args: argparse.Namespace) -> int:
    """Handle serve command"""
    from .server import DevelopmentServer
    
    server = DevelopmentServer(
        port=args.port,
        host=args.host,
        hot_reload=not args.no_reload
    )
    
    try:
        if args.agent:
            server.serve_agent(args.agent)
        else:
            server.serve_all()
        return 0
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return 1


def run_info(args: argparse.Namespace) -> int:
    """Handle info command"""
    import os
    import json
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    
    print("=" * 60)
    print("NIR Intelligence Platform - Developer Framework")
    print("=" * 60)
    print()
    
    # Framework info
    print("Framework:")
    print(f"  Version: {__import__('dev_framework').__version__}")
    print(f"  Location: {project_root / 'dev_framework'}")
    print()
    
    # Project info
    print("Project:")
    print(f"  Root: {project_root}")
    print(f"  Name: NIR Intelligence Platform")
    print()
    
    # Agent count
    agents_dir = project_root / 'agents'
    if agents_dir.exists():
        python_files = list(agents_dir.glob('*_agent.py'))
        print(f"Agents: {len(python_files)} implemented")
        for f in sorted(python_files):
            print(f"  - {f.stem}")
    print()
    
    # Test count
    tests_dir = project_root / 'tests'
    if tests_dir.exists():
        test_files = list(tests_dir.rglob('test_*.py'))
        print(f"Tests: {len(test_files)} test files")
    else:
        print("Tests: No test directory found")
    print()
    
    # Docker status
    docker_compose = project_root / 'docker-compose.yml'
    if docker_compose.exists():
        print("Docker: Configured")
        try:
            import yaml
            with open(docker_compose) as f:
                services = yaml.safe_load(f)
                if services and 'services' in services:
                    print(f"  Services: {len(services['services'])}")
        except ImportError:
            print("  (yaml module not available)")
        except Exception:
            print("  (unable to parse docker-compose.yml)")
    print()
    
    # Framework commands
    print("Available Commands:")
    print("  generate - Generate new agents, tests, or docs")
    print("  validate - Validate agents and configuration")
    print("  test     - Run agent tests")
    print("  quality  - Check and enforce code quality")
    print("  serve    - Start development server")
    print("  info     - Show project information")
    print("  clean    - Clean build artifacts")
    print()
    
    return 0


def run_clean(args: argparse.Namespace) -> int:
    """Handle clean command"""
    import shutil
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    cleaned = []
    
    if args.all or args.tests:
        # Clean test artifacts
        test_dirs = [
            project_root / 'tests' / '__pycache__',
            project_root / '.pytest_cache',
            project_root / 'htmlcov',
            project_root / '.coverage',
        ]
        for d in test_dirs:
            if d.exists():
                if d.is_dir():
                    shutil.rmtree(d)
                else:
                    d.unlink()
                cleaned.append(str(d))
    
    if args.all or args.docs:
        # Clean docs artifacts
        docs_dirs = [
            project_root / 'docs' / '_build',
            project_root / 'site',
        ]
        for d in docs_dirs:
            if d.exists():
                shutil.rmtree(d)
                cleaned.append(str(d))
    
    if args.all:
        # Clean everything
        all_dirs = [
            project_root / '__pycache__',
            project_root / '*.pyc',
            project_root / '*.egg-info',
            project_root / '.mypy_cache',
            project_root / '.vscode' / '*.code-workspace',
        ]
        for pattern in all_dirs:
            if isinstance(pattern, Path):
                if pattern.exists():
                    if pattern.is_dir():
                        shutil.rmtree(pattern)
                    else:
                        pattern.unlink()
                    cleaned.append(str(pattern))
            else:
                for p in project_root.glob(str(pattern)):
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                    cleaned.append(str(p))
    
    if cleaned:
        logger.info(f"Cleaned {len(cleaned)} directories/files")
        for item in cleaned:
            logger.info(f"  - {item}")
    else:
        logger.info("Nothing to clean")
    
    return 0


def main() -> int:
    """Main entry point for CLI"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if hasattr(args, 'verbose') and args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Route to appropriate handler
    handlers = {
        'generate': run_generate,
        'validate': run_validate,
        'test': run_test,
        'quality': run_quality,
        'serve': run_serve,
        'info': run_info,
        'clean': run_clean,
    }
    
    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)
