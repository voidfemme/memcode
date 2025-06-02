"""
Memory management service for storing and retrieving conversations.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.database import AsyncSessionLocal
from data.models import ConversationMemory, Conversation
from sqlalchemy import select, desc

class MemoryManager:
    """Manages conversation memory storage and retrieval."""
    
    def __init__(self):
        pass
    
    async def store_exchange(
        self,
        user_message: str,
        assistant_response: str,
        conversation_id: str,
        user_id: str = None
    ) -> str:
        """Store a user-assistant exchange in memory."""
        
        async with AsyncSessionLocal() as session:
            try:
                # Create memory entry
                memory = ConversationMemory(
                    conversation_id=conversation_id,
                    user_message=user_message,
                    assistant_response=assistant_response,
                    user_id=user_id,
                    timestamp=datetime.utcnow()
                )
                
                session.add(memory)
                await session.commit()
                await session.refresh(memory)
                
                print(f"Stored memory: {memory.id}")
                return memory.id
                
            except Exception as e:
                await session.rollback()
                print(f"Error storing memory: {e}")
                return ""
    
    async def retrieve_relevant_memory(
        self,
        query: str,
        conversation_id: str = None,
        limit: int = 5
    ) -> List[ConversationMemory]:
        """Retrieve relevant memories based on query."""
        
        async with AsyncSessionLocal() as session:
            try:
                # For now, simple keyword-based retrieval
                stmt = select(ConversationMemory).where(
                    ConversationMemory.conversation_id != conversation_id
                ).order_by(desc(ConversationMemory.timestamp)).limit(limit * 2)
                
                result = await session.execute(stmt)
                all_memories = result.scalars().all()
                
                # Simple keyword matching for now
                relevant_memories = []
                query_words = set(query.lower().split())
                
                for memory in all_memories:
                    memory_text = (memory.user_message + " " + memory.assistant_response).lower()
                    if any(word in memory_text for word in query_words):
                        relevant_memories.append(memory)
                        if len(relevant_memories) >= limit:
                            break
                
                return relevant_memories
                
            except Exception as e:
                print(f"Error retrieving memories: {e}")
                return []
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[ConversationMemory]:
        """Get recent history for a specific conversation."""
        
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(ConversationMemory).where(
                    ConversationMemory.conversation_id == conversation_id
                ).order_by(desc(ConversationMemory.timestamp)).limit(limit)
                
                result = await session.execute(stmt)
                return result.scalars().all()
                
            except Exception as e:
                print(f"Error getting conversation history: {e}")
                return []
    
    async def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get summary statistics for a conversation."""
        
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(ConversationMemory).where(
                    ConversationMemory.conversation_id == conversation_id
                ).order_by(ConversationMemory.timestamp)
                
                result = await session.execute(stmt)
                memories = result.scalars().all()
                
                return {
                    "total_exchanges": len(memories),
                    "first_message": memories[0].timestamp if memories else None,
                    "last_message": memories[-1].timestamp if memories else None,
                    "recent_topics": self._extract_topics(memories[-5:]) if memories else []
                }
                
            except Exception as e:
                print(f"Error getting conversation summary: {e}")
                return {"total_exchanges": 0, "recent_topics": []}
    
    def _extract_topics(self, memories: List[ConversationMemory]) -> List[str]:
        """Extract key topics from recent memories."""
        # Simple keyword extraction for now
        topics = []
        for memory in memories:
            words = memory.user_message.lower().split()
            # Look for coding-related keywords
            coding_keywords = ['function', 'class', 'variable', 'loop', 'array', 'object', 'method']
            for word in words:
                if word in coding_keywords and word not in topics:
                    topics.append(word)
        return topics[:5]
