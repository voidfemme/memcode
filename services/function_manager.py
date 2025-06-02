"""
Function management service for storing and retrieving generated functions.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.database import AsyncSessionLocal
from data.models import Function
from sqlalchemy import select, desc, or_

class FunctionManager:
    """Manages function storage and retrieval."""
    
    def __init__(self):
        pass
    
    async def store_function(
        self,
        name: str,
        code: str,
        description: str,
        language: str = "python",
        parameters_schema: Dict = None,
        usage_examples: List[str] = None,
        tags: List[str] = None
    ) -> str:
        """Store a generated function in the database."""
        
        async with AsyncSessionLocal() as session:
            try:
                # Create function entry
                function = Function(
                    name=name,
                    description=description,
                    code=code,
                    language=language,
                    parameters_schema=json.dumps(parameters_schema) if parameters_schema else None,
                    usage_examples=json.dumps(usage_examples) if usage_examples else None,
                    tags=json.dumps(tags) if tags else None,
                    created_at=datetime.utcnow()
                )
                
                session.add(function)
                await session.commit()
                await session.refresh(function)
                
                print(f"Stored function: {function.name} (ID: {function.id})")
                return function.id
                
            except Exception as e:
                await session.rollback()
                print(f"Error storing function: {e}")
                return ""
    
    async def search_functions(
        self,
        query: str,
        language: str = None,
        limit: int = 5
    ) -> List[Function]:
        """Search for functions based on query."""
        
        async with AsyncSessionLocal() as session:
            try:
                # Simple keyword-based search
                stmt = select(Function).where(Function.is_active == True)
                
                if language:
                    stmt = stmt.where(Function.language == language)
                
                # Search in name and description
                search_terms = query.lower().split()
                conditions = []
                for term in search_terms:
                    conditions.extend([
                        Function.name.ilike(f"%{term}%"),
                        Function.description.ilike(f"%{term}%")
                    ])
                
                if conditions:
                    stmt = stmt.where(or_(*conditions))
                
                stmt = stmt.order_by(desc(Function.created_at)).limit(limit)
                
                result = await session.execute(stmt)
                return result.scalars().all()
                
            except Exception as e:
                print(f"Error searching functions: {e}")
                return []
    
    async def get_function_by_id(self, function_id: str) -> Optional[Function]:
        """Get a specific function by ID."""
        
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Function).where(Function.id == function_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
                
            except Exception as e:
                print(f"Error getting function: {e}")
                return None
    
    async def get_recent_functions(self, limit: int = 10) -> List[Function]:
        """Get recently created functions."""
        
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Function).where(
                    Function.is_active == True
                ).order_by(desc(Function.created_at)).limit(limit)
                
                result = await session.execute(stmt)
                return result.scalars().all()
                
            except Exception as e:
                print(f"Error getting recent functions: {e}")
                return []
