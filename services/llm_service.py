"""
LLM service for generating responses and functions using Claude with tools.
"""

import os
import json
from typing import Dict, Any, Optional
from anthropic import AsyncAnthropic

class LLMService:
    """Service for interacting with Claude with function calling."""
    
    def __init__(self):
        self.anthropic_client = None
        self._setup_anthropic()
    
    def _setup_anthropic(self):
        """Initialize Anthropic client if API key is available."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.anthropic_client = AsyncAnthropic(api_key=api_key)
    
    async def generate_response(
        self, 
        user_message: str, 
        context: str = "", 
        conversation_id: str = None,
        function_manager=None
    ) -> str:
        """Generate a response to user message with optional context and tools."""
        
        if not self.anthropic_client:
            return self._fallback_response(user_message)
        
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(context)
            
            # Define tools for Claude
            tools = [
                {
                    "name": "save_function",
                    "description": "Save a generated function to the database for future use",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The function name (without 'def' keyword)"
                            },
                            "code": {
                                "type": "string", 
                                "description": "The complete function code including docstring"
                            },
                            "description": {
                                "type": "string",
                                "description": "A brief description of what the function does"
                            },
                            "language": {
                                "type": "string",
                                "description": "Programming language (default: python)"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional tags for categorizing the function"
                            }
                        },
                        "required": ["name", "code", "description"]
                    }
                },
                {
                    "name": "search_functions",
                    "description": "Search for existing functions in the database based on keywords or functionality",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search terms or keywords to find relevant functions"
                            },
                            "language": {
                                "type": "string",
                                "description": "Optional: filter by programming language"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of functions to return (default: 5)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
            
            # Generate response with tools
            response = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1200,
                temperature=0.7,
                system=system_prompt,
                tools=tools,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Process response and handle tool calls
            result_text = ""
            
            for content_block in response.content:
                if content_block.type == "text":
                    result_text += content_block.text
                elif content_block.type == "tool_use":
                    if content_block.name == "save_function":
                        # Handle function saving
                        if function_manager:
                            tool_input = content_block.input
                            function_id = await function_manager.store_function(
                                name=tool_input.get("name"),
                                code=tool_input.get("code"),
                                description=tool_input.get("description"),
                                language=tool_input.get("language", "python"),
                                tags=tool_input.get("tags", [])
                            )
                            result_text += f"\n\n✅ **Function saved to database!** (ID: {function_id})"
                        else:
                            result_text += f"\n\n⚠️ **Function generated but not saved** (function_manager not available)"
                    
                    elif content_block.name == "search_functions":
                        # Handle function search
                        if function_manager:
                            tool_input = content_block.input
                            functions = await function_manager.search_functions(
                                query=tool_input.get("query"),
                                language=tool_input.get("language"),
                                limit=tool_input.get("limit", 5)
                            )
                            
                            if functions:
                                result_text += f"\n\n🔍 **Found {len(functions)} existing functions:**\n"
                                for func in functions:
                                    result_text += f"\n**{func.name}** ({func.language})\n"
                                    result_text += f"_{func.description}_\n"
                                    result_text += f"```{func.language}\n{func.code}\n```\n"
                            else:
                                result_text += f"\n\n🔍 **No existing functions found for:** {tool_input.get('query')}"
                        else:
                            result_text += f"\n\n⚠️ **Cannot search functions** (function_manager not available)"
            
            return result_text.strip()
            
        except Exception as e:
            print(f"Claude error: {e}")
            return self._fallback_response(user_message)
    
    def _build_system_prompt(self, context: str) -> str:
        """Build system prompt with context."""
        base_prompt = """You are MemCode, an intelligent coding assistant that helps users generate, find, and use functions.

You can:
- Generate code functions based on descriptions
- Help with programming questions  
- Search for existing functions in the database
- Save new functions to the database
- Remember and learn from conversations

When users ask about functions:
1. First use search_functions to check if similar functions already exist
2. If relevant functions exist, show them to the user
3. If no relevant functions exist or user wants something new, create a new function
4. Always use save_function to store new functions in the database
5. Provide the code in your response for the user to see

When users ask to "find", "search", or "look for" functions, use the search_functions tool.

Always write clean, well-documented code with docstrings and examples.
Be helpful, concise, and focus on practical coding solutions."""
        
        if context:
            base_prompt += f"\n\nRelevant context from previous conversations and functions:\n{context}"
        
        return base_prompt
    
    def _fallback_response(self, user_message: str) -> str:
        """Fallback response when Claude is not available."""
        if any(keyword in user_message.lower() for keyword in ['function', 'def', 'create', 'generate']):
            return "I'd love to help you generate a function!\n\nTo use the full AI capabilities, please:\n1. Get an Anthropic API key from https://console.anthropic.com/\n2. Add it to your .env file as ANTHROPIC_API_KEY=your_key_here\n3. Restart MemCode\n\nFor now, I can help with basic questions about the functions you want to create."
        
        return f"Thanks for your message: \"{user_message}\"\n\nMemCode is running in basic mode. To unlock full AI capabilities:\n- Add your ANTHROPIC_API_KEY to the .env file\n- I'll be able to generate functions, remember conversations, and provide intelligent responses!\n\nWhat kind of function would you like me to help you create?"
    
    # Keep the old method for backward compatibility, but it's no longer needed
    async def generate_function(self, description: str, language: str = "python") -> Dict[str, Any]:
        """Legacy method - now handled by generate_response with tools."""
        return {
            "name": "placeholder_function",
            "code": f"def placeholder_function():\n    \"\"\"{description}\"\"\"\n    # Use generate_response with tools instead\n    pass",
            "description": description,
            "language": language
        }
