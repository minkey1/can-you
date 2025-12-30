import litellm
import yaml
import json
import os
import time
from pathlib import Path

class LLMClient:
    def __init__(self, config_path='config.yaml'):
        """Initialize LiteLLM client with configuration"""
        config_file = Path(__file__).parent.parent / config_path
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        self.model = config.get('model', 'gpt-4o-mini')
        self.temperature = config.get('temperature', 0.2)
        self.max_tokens = config.get('max_tokens', 4096)
        self.rate_limit_seconds = config.get('rate_limit_seconds', 7)
        self.tool_call_delay_seconds = config.get('tool_call_delay_seconds', 0.5)
        
        # Set API key from config or environment
        api_key = config.get('api_key')
        if api_key and api_key != 'YOUR_API_KEY_HERE':
            litellm.api_key = api_key
        
        # Load system prompt
        prompt_file = Path(__file__).parent.parent / 'prompts' / 'system_prompt.txt'
        with open(prompt_file, 'r') as f:
            self.system_prompt = f.read()
        
        self.conversation_history = []
    
    def chat(self, user_message, tools=None, use_planning_mode=False):
        """Send message to LLM with optional tool definitions"""
        if use_planning_mode:
            # Load planning prompt
            prompt_file = Path(__file__).parent.parent / 'prompts' / 'planner_prompt.txt'
            with open(prompt_file, 'r') as f:
                system_prompt = f.read()
        else:
            system_prompt = self.system_prompt
        
        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history,
            {"role": "user", "content": user_message}
        ]
        
        try:
            # Rate limiting: wait before API request to avoid rate limiting
            time.sleep(self.rate_limit_seconds)
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            response = litellm.completion(**kwargs)
            
            # Store in conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            
            assistant_message = response.choices[0].message
            self.conversation_history.append({
                "role": "assistant", 
                "content": assistant_message.content or "",
                "tool_calls": assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') else None
            })
            
            return response
        
        except Exception as e:
            raise Exception(f"LiteLLM error: {str(e)}")
    
    def add_tool_response(self, tool_call_id, function_name, result):
        """Add tool execution result to conversation"""
        self.conversation_history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": function_name,
            "content": json.dumps(result)
        })
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
