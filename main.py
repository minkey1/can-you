#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.llm_client import LLMClient
from core.executor import CommandExecutor
from core.planner import LongTaskPlanner


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered Linux command helper - generates commands based on natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s find all pdf files in current directory
  %(prog)s -l set up a python web server with nginx
  %(prog)s --dry-run show disk usage for home directory
  %(prog)s -y compress all log files older than 30 days

Modes:
  Default mode: Quick single-command generation
  -l mode: Multi-step planning for complex tasks
        """
    )
    
    parser.add_argument(
        'task',
        nargs='+',
        help='Describe what you want to do in natural language'
    )
    
    parser.add_argument(
        '-l', '--long',
        action='store_true',
        help='Enable long-form planning mode for multi-step tasks'
    )
    
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Auto-confirm all prompts (use with caution)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show commands without executing them'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed tool calls, planning, and execution logs'
    )
    
    args = parser.parse_args()
    
    # Combine task words into description
    task_description = ' '.join(args.task)
    
    try:
        # Initialize LLM client
        llm_client = LLMClient()
        
        if args.long:
            # Use planner for complex tasks
            planner = LongTaskPlanner(llm_client, verbose=args.verbose)
            planner.execute_long_task(task_description, args.yes, args.dry_run)
        else:
            # Use executor for quick tasks
            executor = CommandExecutor(llm_client, verbose=args.verbose)
            executor.execute_quick_task(task_description, args.yes, args.dry_run)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

