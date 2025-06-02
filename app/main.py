"""
MemCode - Main Chainlit application entry point.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chainlit as cl
from services.llm_service import LLMService
from services.memory_manager import MemoryManager
from services.function_manager import FunctionManager

# Initialize services
llm_service = LLMService()
memory_manager = MemoryManager()
function_manager = FunctionManager()

@cl.on_chat_start
async def start():
    import uuid
    conversation_id = str(uuid.uuid4())
    cl.user_session.set("conversation_id", conversation_id)
    
    welcome = cl.Message(
        content="🧠💻 **Welcome to MemCode!**\n\nI'm your intelligent coding assistant with memory! I can:\n\n• Generate and save functions automatically\n• Remember our conversations\n• Search through saved functions\n• Learn from previous interactions\n\nTry asking me to create a function - I'll generate it and save it to the database automatically!"
    )
    await welcome.send()

@cl.on_message
async def main(message: cl.Message):
    conversation_id = cl.user_session.get("conversation_id")
    user_input = message.content
    
    try:
        # Retrieve relevant context from memory
        relevant_memories = await memory_manager.retrieve_relevant_memory(
            query=user_input,
            conversation_id=conversation_id,
            limit=3
        )
        
        # Search for relevant functions
        relevant_functions = await function_manager.search_functions(
            query=user_input,
            limit=3
        )
        
        # Build context string
        context = ""
        if relevant_memories:
            context += "Previous relevant conversations:\n"
            for memory in relevant_memories:
                context += f"- User asked: {memory.user_message[:100]}...\n"
        
        if relevant_functions:
            context += "\nRelevant existing functions:\n"
            for func in relevant_functions:
                context += f"- {func.name}: {func.description[:100]}...\n"
        
        # Generate response with tools
        response_text = await llm_service.generate_response(
            user_message=user_input,
            context=context,
            conversation_id=conversation_id,
            function_manager=function_manager
        )
        
        # Store this exchange in memory
        await memory_manager.store_exchange(
            user_message=user_input,
            assistant_response=response_text,
            conversation_id=conversation_id
        )
        
        # Add context indicators
        context_info = []
        if relevant_memories:
            context_info.append(f"{len(relevant_memories)} relevant memories")
        if relevant_functions:
            context_info.append(f"{len(relevant_functions)} relevant functions")
        
        if context_info:
            response_text += f"\n\n💡 *Used: {', '.join(context_info)}*"
        
        response = cl.Message(content=response_text)
        await response.send()
        
    except Exception as e:
        print(f"Error: {e}")
        error_msg = cl.Message(content="I encountered an error. Please try again!")
        await error_msg.send()
