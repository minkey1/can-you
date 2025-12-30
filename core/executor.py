import json
import subprocess
import time
from core.llm_client import LLMClient
from tools.system_info import (
    get_file_tree,
    check_port_in_use,
    get_disk_space,
    check_file_exists,
    get_platform_info,
    build_shell_command,
)
from tools.man_pages import get_man_page, get_command_help
from tools.file_ops import read_config_file, check_write_permission
from tools.validation import validate_command_safety

# Tool function mapping
TOOL_FUNCTIONS = {
    "get_man_page": get_man_page,
    "get_command_help": get_command_help,
    "get_file_tree": get_file_tree,
    "check_file_exists": check_file_exists,
    "read_config_file": read_config_file,
    "check_port_in_use": check_port_in_use,
    "get_disk_space": get_disk_space,
    "check_write_permission": check_write_permission,
}

# Tool definitions for LLM
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_man_page",
            "description": "Fetch the man page documentation for a Linux command. Use this to understand command syntax and options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command name (e.g., 'grep', 'find', 'systemctl')"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_command_help",
            "description": "Get the --help output for a command. Faster alternative to man pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command name"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_tree",
            "description": "Get the directory structure of a path to understand what files/folders exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to explore"},
                    "max_depth": {"type": "integer", "description": "Maximum depth to traverse (default: 3)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_file_exists",
            "description": "Check if a file or directory exists before operating on it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File or directory path"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_config_file",
            "description": "Read contents of a configuration file to understand current settings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to config file"},
                    "max_lines": {"type": "integer", "description": "Maximum lines to read (default: 100)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_port_in_use",
            "description": "Check if a network port is already in use to avoid conflicts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "Port number to check"}
                },
                "required": ["port"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_disk_space",
            "description": "Get available disk space for a path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to check (default: '/')"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_write_permission",
            "description": "Check if the current user has write permission to a path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to check"}
                },
                "required": ["path"]
            }
        }
    }
]


class CommandExecutor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.max_iterations = 10  # Prevent infinite loops
    
    def execute_quick_task(self, task_description, auto_confirm=False, dry_run=False):
        """Execute a single-step task"""
        print(f"\n🎯 Task: {task_description}\n")
        
        # Get platform information
        platform_info = get_platform_info()
        
        # Build context message for first iteration
        if platform_info:
            context = f"""System Context:
- Platform: {platform_info.get('platform', 'Unknown')}
- OS: {platform_info.get('distro', platform_info.get('os', 'Unknown'))}
- Architecture: {platform_info.get('architecture', 'Unknown')}
- Shell: {platform_info.get('shell', 'Unknown')} ({platform_info.get('shell_version', platform_info.get('shell_type', ''))})

User Task: {task_description}

IMPORTANT: Generate commands appropriate for the {platform_info.get('platform', 'current')} platform and {platform_info.get('shell', 'shell')}."""
        else:
            context = task_description
        
        # Start conversation with LLM
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # Get LLM response
            try:
                response = self.llm_client.chat(
                    context if iteration == 1 else "Continue with the task.",
                    tools=TOOL_DEFINITIONS
                )
            except Exception as e:
                print(f"❌ Error communicating with LLM: {e}")
                return
            
            message = response.choices[0].message
            
            # Check if LLM wants to use tools
            if hasattr(message, 'tool_calls') and message.tool_calls:
                self._handle_tool_calls(message.tool_calls)
                continue
            
            # Check if LLM has a final answer
            if message.content:
                result = self._parse_llm_response(message.content)
                
                if result and 'commands' in result:
                    self._execute_commands(result, auto_confirm, dry_run)
                    return
                else:
                    print(f"💬 {message.content}")
                    return
        
        print("⚠️  Maximum iterations reached. Task may be incomplete.")
    
    def _handle_tool_calls(self, tool_calls):
        """Execute tool calls and add results to conversation"""
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            # Rate limiting: small delay between tool calls to avoid overwhelming the API
            delay = getattr(self.llm_client, 'tool_call_delay_seconds', 0.5)
            time.sleep(delay)
            
            print(f"🔧 Calling tool: {function_name}({json.dumps(arguments, indent=2)})")
            
            # Execute the tool
            if function_name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[function_name](**arguments)
                    print(f"✅ Tool result received\n")
                    
                    # Add tool result to conversation
                    self.llm_client.add_tool_response(
                        tool_call.id,
                        function_name,
                        result
                    )
                except Exception as e:
                    error_result = {"error": str(e)}
                    print(f"❌ Tool error: {e}\n")
                    self.llm_client.add_tool_response(
                        tool_call.id,
                        function_name,
                        error_result
                    )
            else:
                print(f"⚠️  Unknown tool: {function_name}")
    
    def _parse_llm_response(self, content):
        """Parse LLM response for commands"""
        # Try to extract JSON from the response
        try:
            # Look for JSON code block
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                # Try parsing the whole content as JSON
                return json.loads(content)
        except:
            return None
    
    def _execute_commands(self, result, auto_confirm, dry_run):
        """Execute the commands from LLM response"""
        commands = result.get('commands', [])
        explanation = result.get('explanation', '')
        warnings = result.get('warnings', [])
        requires_confirmation = result.get('requires_confirmation', True)
        
        if explanation:
            print(f"📋 Explanation:\n{explanation}\n")
        
        if warnings:
            print("⚠️  Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
            print()
        
        print("📝 Commands to execute:")
        for i, cmd in enumerate(commands, 1):
            print(f"  {i}. {cmd}")
        print()
        
        if dry_run:
            print("🔍 Dry run mode - not executing commands")
            return
        
        # Validate command safety
        for cmd in commands:
            safety_check = validate_command_safety(cmd)
            if not safety_check['safe']:
                print(f"🛑 Safety check failed: {safety_check['reason']}")
                return
        
        # Ask for confirmation
        if requires_confirmation and not auto_confirm:
            response = input("Execute these commands? (y/N): ")
            if response.lower() != 'y':
                print("❌ Cancelled by user")
                return
        
        # Execute commands
        print("\n🚀 Executing commands...\n")
        # Show shell being used for transparency
        pi = get_platform_info()
        print(f"Using shell: {pi.get('shell', 'unknown')} ({pi.get('shell_type', '')}) on {pi.get('platform', 'unknown platform')}\n")
        for i, cmd in enumerate(commands, 1):
            print(f"[{i}/{len(commands)}] Running: {cmd}")
            try:
                # Build proper shell command based on platform/shell
                run_cmd = build_shell_command(cmd)
                result = subprocess.run(
                    run_cmd,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(f"stderr: {result.stderr}")
                
                if result.returncode != 0:
                    print(f"⚠️  Command exited with code {result.returncode}")
                else:
                    print(f"✅ Success\n")
                    
            except subprocess.TimeoutExpired:
                print(f"⏱️  Command timed out after 300 seconds")
            except Exception as e:
                print(f"❌ Error: {e}")
