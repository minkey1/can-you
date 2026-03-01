import json
from core.llm_client import LLMClient
from core.executor import CommandExecutor, TOOL_DEFINITIONS
from core.progress import LiveProgress
from tools.system_info import get_platform_info


class LongTaskPlanner:
    def __init__(self, llm_client: LLMClient, verbose: bool = False, show_progress: bool = True):
        self.llm_client = llm_client
        self.verbose = verbose
        self.progress = LiveProgress(enabled=(show_progress and not verbose))
        self.executor = CommandExecutor(llm_client, verbose=verbose, show_progress=show_progress)

    def _vprint(self, message=""):
        if self.verbose:
            print(message)
    
    def execute_long_task(self, task_description, auto_confirm=False, dry_run=False):
        """Execute a multi-step task with planning"""
        self._vprint(f"\n🎯 Long Task Mode: {task_description}\n")
        self._vprint("📊 Planning phase...\n")
        
        # Phase 1: Planning
        plan = self._create_plan(task_description)
        
        if not plan:
            print("❌ Failed to create a plan")
            return
        
        self._vprint("📋 Execution Plan:")
        steps = plan.get('steps', [])
        if self.verbose:
            for i, step in enumerate(steps, 1):
                print(f"  {i}. {step['description']}")
                if 'validation' in step:
                    print(f"     Validation: {step['validation']}")
            print()
        
        # Ask for plan approval
        if not auto_confirm:
            response = input("Proceed with this plan? (y/N): ")
            if response.lower() != 'y':
                print("❌ Plan rejected by user")
                return
        
        # Phase 2: Execute each step
        self._vprint("\n🚀 Executing plan...\n")
        if self.progress.enabled:
            self.progress.snapshot(0, len(steps), f"Executing plan steps (0/{len(steps)})")
        for i, step in enumerate(steps, 1):
            if self.progress.enabled:
                self.progress.snapshot(i - 1, len(steps), f"Executing plan steps ({i}/{len(steps)})")
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"Step {i}/{len(steps)}: {step['description']}")
                print(f"{'='*60}\n")
            
            # Execute the step
            success = self._execute_step(step, auto_confirm, dry_run)
            
            if not success and not dry_run:
                print(f"\n❌ Step {i} failed. Aborting remaining steps.")
                if self.progress.enabled:
                    self.progress.snapshot(i, len(steps), f"Executing plan steps ({i}/{len(steps)})")
                break
            
            if i < len(steps):
                self._vprint(f"\n✅ Step {i} completed. Moving to next step...\n")
            if self.progress.enabled:
                self.progress.snapshot(i, len(steps), f"Executing plan steps ({i}/{len(steps)})")
        
        # Clear progress bar after all steps are executed
        self.progress.clear()
        self._vprint("\n✨ Long task completed!")
    
    def _create_plan(self, task_description):
        """Ask LLM to create a multi-step plan"""
        # Get platform information
        platform_info = get_platform_info()
        
        planning_prompt = f"""
System Context:
- Platform: {platform_info.get('platform', 'Unknown')}
- OS: {platform_info.get('distro', platform_info.get('os', 'Unknown'))}
- Architecture: {platform_info.get('architecture', 'Unknown')}
- Shell: {platform_info.get('shell', 'Unknown')} ({platform_info.get('shell_version', platform_info.get('shell_type', ''))})

Task: {task_description}

Create a detailed multi-step plan to accomplish this task on the {platform_info.get('platform', 'current')} platform. For each step:
1. Describe what needs to be done
2. Specify what information/validation is needed before executing
3. List potential risks or conflicts

IMPORTANT: All commands should be appropriate for {platform_info.get('platform', 'the current platform')} and {platform_info.get('shell', 'the shell')}.

Output your plan in this JSON format:
```json
{{
  "steps": [
    {{
      "description": "Step description",
      "validation": "What to check before executing",
      "risks": ["potential risk 1", "potential risk 2"]
    }}
  ],
  "overall_risks": ["overall risk 1"],
  "estimated_duration": "time estimate"
}}
```
"""
        
        try:
            with self.progress.activity("AI is creating execution plan"):
                response = self.llm_client.chat(
                    planning_prompt,
                    use_planning_mode=True
                )
            
            content = response.choices[0].message.content
            
            # Parse the plan
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                plan = json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                plan = json.loads(json_str)
            else:
                plan = json.loads(content)
            
            return plan
            
        except Exception as e:
            print(f"❌ Planning error: {e}")
            return None
    
    def _execute_step(self, step, auto_confirm, dry_run):
        """Execute a single step from the plan"""
        step_description = step['description']
        
        # Show validation requirements
        if 'validation' in step:
            self._vprint(f"🔍 Validation: {step['validation']}\n")
        
        if 'risks' in step and step['risks']:
            if self.verbose:
                print("⚠️  Risks for this step:")
                for risk in step['risks']:
                    print(f"  - {risk}")
                print()
        
        # Reset conversation for this step
        self.llm_client.reset_conversation()
        
        # Use the executor to handle this step
        self.executor.execute_quick_task(step_description, auto_confirm, dry_run)
        
        return True  # Assume success unless explicitly failed
