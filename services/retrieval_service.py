"""
Enhanced retrieval service with semantic search capabilities.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

# For semantic search
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from core.database import AsyncSessionLocal
from data.models import Function
from sqlalchemy import select, desc, or_, and_

logger = logging.getLogger(__name__)

class RetrievalService:
    """Enhanced function retrieval with semantic search and categorization."""
    
    def __init__(self):
        self.embedding_model = None
        self.tfidf_vectorizer = None
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize embedding models for semantic search."""
        try:
            # Use a lightweight model for embeddings
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            logger.info("Successfully initialized embedding models")
        except Exception as e:
            logger.warning(f"Could not initialize embedding models: {e}")
            self.embedding_model = None
            self.tfidf_vectorizer = None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a text string."""
        if not self.embedding_model:
            return None
            
        try:
            embedding = self.embedding_model.encode([text])
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def calculate_semantic_similarity(
        self, 
        query_embedding: List[float], 
        function_embedding: List[float]
    ) -> float:
        """Calculate cosine similarity between embeddings."""
        try:
            query_vec = np.array(query_embedding).reshape(1, -1)
            func_vec = np.array(function_embedding).reshape(1, -1)
            similarity = cosine_similarity(query_vec, func_vec)[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    async def update_function_embedding(self, function_id: str, text: str) -> bool:
        """Update the embedding for a function."""
        embedding = self.generate_embedding(text)
        if not embedding:
            return False
            
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Function).where(Function.id == function_id)
                result = await session.execute(stmt)
                function = result.scalar_one_or_none()
                
                if function:
                    function.description_embedding = json.dumps(embedding)
                    await session.commit()
                    return True
                    
            except Exception as e:
                logger.error(f"Error updating function embedding: {e}")
                await session.rollback()
                
        return False
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        language: str = None,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Perform semantic search on functions."""
        if not self.embedding_model:
            logger.warning("Semantic search not available - falling back to keyword search")
            return await self.keyword_search(query, limit, language)
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        if not query_embedding:
            return await self.keyword_search(query, limit, language)
        
        async with AsyncSessionLocal() as session:
            try:
                # Get functions with embeddings
                stmt = select(Function).where(
                    and_(
                        Function.is_active == True,
                        Function.description_embedding.is_not(None)
                    )
                )
                
                if language:
                    stmt = stmt.where(Function.language == language)
                
                result = await session.execute(stmt)
                functions = result.scalars().all()
                
                # Calculate similarities
                similarities = []
                for func in functions:
                    try:
                        func_embedding = json.loads(func.description_embedding)
                        similarity = self.calculate_semantic_similarity(
                            query_embedding, func_embedding
                        )
                        
                        if similarity >= min_similarity:
                            similarities.append({
                                'function': func,
                                'similarity': similarity,
                                'match_type': 'semantic'
                            })
                            
                    except Exception as e:
                        logger.warning(f"Error processing function {func.id}: {e}")
                        continue
                
                # Sort by similarity
                similarities.sort(key=lambda x: x['similarity'], reverse=True)
                
                return similarities[:limit]
                
            except Exception as e:
                logger.error(f"Error in semantic search: {e}")
                return await self.keyword_search(query, limit, language)
    
    async def keyword_search(
        self,
        query: str,
        limit: int = 10,
        language: str = None
    ) -> List[Dict[str, Any]]:
        """Fallback keyword-based search."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Function).where(Function.is_active == True)
                
                if language:
                    stmt = stmt.where(Function.language == language)
                
                # Search in name, description, and tags
                search_terms = query.lower().split()
                conditions = []
                
                for term in search_terms:
                    conditions.extend([
                        Function.name.ilike(f"%{term}%"),
                        Function.description.ilike(f"%{term}%"),
                        Function.tags.ilike(f"%{term}%")
                    ])
                
                if conditions:
                    stmt = stmt.where(or_(*conditions))
                
                stmt = stmt.order_by(desc(Function.created_at)).limit(limit)
                
                result = await session.execute(stmt)
                functions = result.scalars().all()
                
                return [
                    {
                        'function': func,
                        'similarity': 1.0,  # No similarity score for keyword search
                        'match_type': 'keyword'
                    }
                    for func in functions
                ]
                
            except Exception as e:
                logger.error(f"Error in keyword search: {e}")
                return []
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        language: str = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Combine semantic and keyword search with weighted scoring."""
        
        # Get results from both search methods
        semantic_results = await self.semantic_search(query, limit * 2, language)
        keyword_results = await self.keyword_search(query, limit * 2, language)
        
        # Create a combined scoring system
        function_scores = {}
        
        # Process semantic results
        for item in semantic_results:
            func_id = item['function'].id
            score = item['similarity'] * semantic_weight
            function_scores[func_id] = {
                'function': item['function'],
                'score': score,
                'semantic_similarity': item['similarity'],
                'match_types': ['semantic']
            }
        
        # Process keyword results and combine scores
        for item in keyword_results:
            func_id = item['function'].id
            keyword_score = keyword_weight  # Give full weight for keyword matches
            
            if func_id in function_scores:
                # Combine scores
                function_scores[func_id]['score'] += keyword_score
                function_scores[func_id]['match_types'].append('keyword')
            else:
                function_scores[func_id] = {
                    'function': item['function'],
                    'score': keyword_score,
                    'semantic_similarity': 0.0,
                    'match_types': ['keyword']
                }
        
        # Sort by combined score
        sorted_results = sorted(
            function_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        return sorted_results[:limit]
    
    async def categorize_function(self, function: Function) -> List[str]:
        """Automatically categorize a function based on its content."""
        categories = []
        
        code_lower = function.code.lower()
        desc_lower = function.description.lower()
        name_lower = function.name.lower()
        
        # Programming categories
        if any(keyword in code_lower for keyword in ['def ', 'class ', 'import ', 'from ']):
            categories.append('python')
        
        if any(keyword in code_lower for keyword in ['async ', 'await ', 'asyncio']):
            categories.append('async')
        
        if any(keyword in code_lower for keyword in ['requests', 'http', 'api', 'fetch']):
            categories.append('web')
        
        if any(keyword in code_lower for keyword in ['pandas', 'numpy', 'matplotlib', 'data']):
            categories.append('data-science')
        
        if any(keyword in code_lower for keyword in ['sql', 'database', 'db', 'query']):
            categories.append('database')
        
        if any(keyword in code_lower for keyword in ['file', 'open', 'read', 'write', 'io']):
            categories.append('file-operations')
        
        if any(keyword in code_lower for keyword in ['test', 'assert', 'unittest', 'pytest']):
            categories.append('testing')
        
        # Functional categories based on description
        if any(keyword in desc_lower for keyword in ['sort', 'search', 'find', 'filter']):
            categories.append('algorithms')
        
        if any(keyword in desc_lower for keyword in ['validate', 'check', 'verify']):
            categories.append('validation')
        
        if any(keyword in desc_lower for keyword in ['convert', 'transform', 'parse']):
            categories.append('data-transformation')
        
        if any(keyword in desc_lower for keyword in ['calculate', 'compute', 'math']):
            categories.append('math')
        
        if any(keyword in desc_lower for keyword in ['string', 'text', 'format']):
            categories.append('string-manipulation')
        
        return categories if categories else ['utility']
    
    async def get_function_recommendations(
        self,
        function_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get function recommendations based on a given function."""
        async with AsyncSessionLocal() as session:
            try:
                # Get the reference function
                stmt = select(Function).where(Function.id == function_id)
                result = await session.execute(stmt)
                ref_function = result.scalar_one_or_none()
                
                if not ref_function:
                    return []
                
                # Get categories for the reference function
                categories = await self.categorize_function(ref_function)
                
                # Find similar functions
                if ref_function.description_embedding:
                    # Use semantic similarity
                    query_text = f"{ref_function.name} {ref_function.description}"
                    recommendations = await self.semantic_search(
                        query_text,
                        limit + 1,  # +1 to exclude the reference function
                        ref_function.language
                    )
                    
                    # Remove the reference function from results
                    recommendations = [
                        rec for rec in recommendations 
                        if rec['function'].id != function_id
                    ]
                    
                    return recommendations[:limit]
                else:
                    # Fallback to category-based recommendations
                    return await self.get_functions_by_categories(categories, limit, function_id)
                    
            except Exception as e:
                logger.error(f"Error getting recommendations: {e}")
                return []
    
    async def get_functions_by_categories(
        self,
        categories: List[str],
        limit: int = 10,
        exclude_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get functions that match given categories."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Function).where(Function.is_active == True)
                
                if exclude_id:
                    stmt = stmt.where(Function.id != exclude_id)
                
                # Search for category matches in tags
                category_conditions = []
                for category in categories:
                    category_conditions.append(Function.tags.ilike(f"%{category}%"))
                
                if category_conditions:
                    stmt = stmt.where(or_(*category_conditions))
                
                stmt = stmt.order_by(desc(Function.created_at)).limit(limit)
                
                result = await session.execute(stmt)
                functions = result.scalars().all()
                
                return [
                    {
                        'function': func,
                        'similarity': 0.8,  # Category match score
                        'match_type': 'category'
                    }
                    for func in functions
                ]
                
            except Exception as e:
                logger.error(f"Error getting functions by categories: {e}")
                return []
    
    async def update_all_embeddings(self) -> Dict[str, int]:
        """Update embeddings for all functions that don't have them."""
        if not self.embedding_model:
            return {'updated': 0, 'failed': 0}
        
        updated = 0
        failed = 0
        
        async with AsyncSessionLocal() as session:
            try:
                # Get functions without embeddings
                stmt = select(Function).where(
                    and_(
                        Function.is_active == True,
                        Function.description_embedding.is_(None)
                    )
                )
                
                result = await session.execute(stmt)
                functions = result.scalars().all()
                
                for func in functions:
                    try:
                        # Create embedding text
                        embedding_text = f"{func.name} {func.description}"
                        if func.tags:
                            try:
                                tags = json.loads(func.tags)
                                embedding_text += " " + " ".join(tags)
                            except:
                                pass
                        
                        # Generate and store embedding
                        embedding = self.generate_embedding(embedding_text)
                        if embedding:
                            func.description_embedding = json.dumps(embedding)
                            updated += 1
                        else:
                            failed += 1
                            
                    except Exception as e:
                        logger.error(f"Error updating embedding for {func.id}: {e}")
                        failed += 1
                
                await session.commit()
                
            except Exception as e:
                logger.error(f"Error in bulk embedding update: {e}")
                await session.rollback()
        
        return {'updated': updated, 'failed': failed}

# Global service instance
retrieval_service = RetrievalService()