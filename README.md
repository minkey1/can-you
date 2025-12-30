# AI-Powered Linux Command Helper

An intelligent command-line utility that generates and executes Linux commands based on natural language descriptions. The AI assistant gathers information about your system before suggesting commands, minimizing assumptions and ensuring safe, accurate command generation.

## Features

- **Natural Language Interface**: Describe what you want in plain English
- **Tool-Based Context Gathering**: LLM requests system information (man pages, file trees, configs) before generating commands
- **Two Modes**:
  - **Quick Mode** (default): Single command generation for simple tasks
  - **Long Mode** (`-l`): Multi-step planning for complex tasks
- **Safety First**: Validates commands, warns about destructive operations, requires confirmation
- **Flexible Execution**: Dry-run mode, auto-confirm, and interactive modes

## Installation

1. Clone or download this project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your LLM API key in `config.yaml`:
   ```yaml
      model: "gpt-5.1-codex-max"
   api_key: "YOUR_API_KEY_HERE"
   ```

## Usage

### Quick Mode (Single Commands)

```bash
python main.py find all pdf files in current directory
python main.py show disk usage for home directory
python main.py compress all log files older than 30 days
```

### Long Mode (Multi-Step Tasks)

```bash
python main.py -l set up a python web server with nginx
python main.py -l backup database and upload to s3
```

### Flags

- `-l, --long`: Enable long-form planning mode for multi-step tasks
- `-y, --yes`: Auto-confirm all prompts (use with caution)
- `--dry-run`: Show commands without executing them

### Examples

```bash
# Simple task
python main.py list all processes using more than 100MB of memory

# Dry run mode
python main.py --dry-run delete all .tmp files in /var/log

# Long task with auto-confirm
python main.py -l -y set up docker and run nginx container
```

### Streamlit UI

```bash
pip install -r requirements.txt
streamlit run ui/app.py
```
Use the toggles to switch between quick and long modes, auto-confirm prompts, and dry-run execution.

## Making it Executable (Linux)

To run without typing "python":

1. The shebang is already added to `main.py`
2. Make it executable:
   ```bash
   chmod +x main.py
   ```
3. Copy to your PATH (optional):
   ```bash
   sudo cp main.py /usr/local/bin/cmdhelper
   ```
4. Now run it anywhere:
   ```bash
   cmdhelper find large files
   ```

## Project Structure

```
Final Sem Project/
├── main.py                 # CLI entry point
├── config.yaml            # LLM configuration
├── requirements.txt       # Python dependencies
├── core/
│   ├── llm_client.py      # LiteLLM integration
│   ├── executor.py        # Command execution with tool support
│   └── planner.py         # Multi-step task planning
├── tools/
│   ├── system_info.py     # System queries (file trees, disk space, etc.)
│   ├── man_pages.py       # Man page and help retrieval
│   ├── file_ops.py        # File operations and config reading
│   └── validation.py      # Command safety validation
└── prompts/
    ├── system_prompt.txt  # Main AI instructions
    └── planner_prompt.txt # Long-form planning instructions
```

## How It Works

1. **You describe a task** in natural language
2. **The LLM analyzes** the request and determines what information it needs
3. **Tools are called** to gather system data (man pages, file existence, configs, etc.)
4. **Commands are generated** based on real system state, not assumptions
5. **Safety checks** validate the commands before execution
6. **Confirmation prompt** (unless `-y` flag is used)
7. **Commands execute** and output is shown

## Configuration

Edit `config.yaml` to customize:

```yaml
# Model selection
model: "gpt-5.1-codex-max"  # or "claude-3-5-sonnet-20241022", etc.

# API key (or set as environment variable)
api_key: "YOUR_API_KEY_HERE"

# Generation parameters
temperature: 0.2
max_tokens: 4096

# Planning mode (for -l flag)
planning_model: "gpt-5.1-codex-max"
planning_temperature: 0.3
```

## Supported LLM Providers

Via LiteLLM, supports:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- DeepSeek
- Ollama (local models)
- And many more...

## Safety Features

- Command validation for dangerous patterns (rm -rf /, fork bombs, etc.)
- Requires confirmation for destructive operations
- Checks file existence before operations
- Validates write permissions
- Warns about system directory modifications

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

MIT License - Feel free to use and modify as needed.
