"""
Context Engine for Quill MCP - Intelligent context switching and token optimization.

Optimizes memory selection and context management for Claude Code's 200K token window,
ensuring authors get the most relevant information without exceeding limits.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContextItem:
    """Represents a memory item with relevance scoring."""
    content_type: str
    entity_id: int
    title: str
    content: str
    relevance_score: float
    token_estimate: int
    importance: str = "normal"


class ContextEngine:
    """Manages intelligent context switching and token optimization for authors."""
    
    def __init__(self, max_tokens: int = 180000):
        """Initialize context engine.
        
        Args:
            max_tokens: Maximum tokens for context (leave buffer for Claude Code)
        """
        self.max_tokens = max_tokens
        self.working_tokens = int(max_tokens * 0.8)  # Use 80% for safety
        self.auto_context = True
        self.current_context: List[ContextItem] = []
        
        # Weights for relevance scoring
        self.scoring_weights = {
            "exact_match": 2.0,
            "name_match": 1.5,
            "semantic_similarity": 1.0,
            "recency": 0.5,
            "importance": 1.2,
            "relationship": 0.8
        }
        
        logger.info(f"ContextEngine initialized with {max_tokens:,} max tokens")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimate: 1 token ≈ 4 characters for English text
        # This is a simplified estimation; real tokenization would be more accurate
        return max(1, len(text) // 4)
    
    def extract_entities(self, text: str) -> Set[str]:
        """Extract potential entity names from text."""
        # Simple entity extraction - looks for capitalized words and proper nouns
        # In a full implementation, this could use NER or more sophisticated methods
        
        entities = set()
        
        # Find capitalized words (potential names)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities.update(capitalized_words)
        
        # Find quoted text (potential dialogue or titles)
        quoted_text = re.findall(r'"([^"]+)"', text)
        for quote in quoted_text:
            words = quote.split()
            entities.update(word.strip('.,!?') for word in words if len(word) > 2)
        
        # Find potential location/place names (Title Case phrases)
        title_case_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.update(title_case_phrases)
        
        return entities
    
    def calculate_relevance_score(self, memory_item: Dict[str, Any], 
                                current_text: str, entities: Set[str]) -> float:
        """Calculate relevance score for a memory item."""
        score = 0.0
        title = memory_item.get('title', '').lower()
        content = memory_item.get('content', '').lower()
        current_lower = current_text.lower()
        
        # Exact title match in current text
        if title in current_lower:
            score += self.scoring_weights["exact_match"]
        
        # Name mentions in current text
        for entity in entities:
            if entity.lower() in title or entity.lower() in content:
                score += self.scoring_weights["name_match"]
        
        # Content similarity (simple keyword overlap)
        current_words = set(re.findall(r'\b\w+\b', current_lower))
        memory_words = set(re.findall(r'\b\w+\b', content))
        
        if current_words and memory_words:
            overlap = len(current_words.intersection(memory_words))
            total_unique = len(current_words.union(memory_words))
            similarity = overlap / total_unique if total_unique > 0 else 0
            score += similarity * self.scoring_weights["semantic_similarity"]
        
        # Importance boost
        importance = memory_item.get('metadata', {})
        if isinstance(importance, str):
            try:
                importance = json.loads(importance)
            except (json.JSONDecodeError, TypeError):
                importance = {}
        
        if importance.get('importance') == 'main':
            score += self.scoring_weights["importance"]
        elif importance.get('plot_type') == 'main':
            score += self.scoring_weights["importance"]
        
        # Character relationship boost
        if memory_item.get('content_type') == 'character':
            relationships = importance.get('relationships', {})
            if isinstance(relationships, str):
                try:
                    relationships = json.loads(relationships)
                except (json.JSONDecodeError, TypeError):
                    relationships = {}
            
            if relationships and any(rel.lower() in current_lower for rel in relationships.keys()):
                score += self.scoring_weights["relationship"]
        
        return score
    
    def optimize_context_for_tokens(self, candidate_items: List[ContextItem]) -> List[ContextItem]:
        """Select optimal context items within token limits."""
        # Sort by relevance score descending
        sorted_items = sorted(candidate_items, key=lambda x: x.relevance_score, reverse=True)
        
        selected_items = []
        total_tokens = 0
        
        # Prioritize high-importance items first
        high_importance = [item for item in sorted_items if item.importance in ['main', 'high']]
        medium_importance = [item for item in sorted_items if item.importance == 'medium']
        low_importance = [item for item in sorted_items if item.importance not in ['main', 'high', 'medium']]
        
        # Add items by priority, respecting token limits
        for priority_group in [high_importance, medium_importance, low_importance]:
            for item in priority_group:
                if total_tokens + item.token_estimate <= self.working_tokens:
                    selected_items.append(item)
                    total_tokens += item.token_estimate
                else:
                    # If we can't fit the whole item, check if we should truncate
                    remaining_tokens = self.working_tokens - total_tokens
                    if remaining_tokens > 100:  # Only truncate if meaningful space left
                        # Create truncated version
                        truncated_content = item.content[:remaining_tokens * 4]  # Rough char estimate
                        truncated_item = ContextItem(
                            content_type=item.content_type,
                            entity_id=item.entity_id,
                            title=item.title,
                            content=truncated_content + "... [truncated]",
                            relevance_score=item.relevance_score,
                            token_estimate=remaining_tokens,
                            importance=item.importance
                        )
                        selected_items.append(truncated_item)
                        total_tokens = self.working_tokens
                    break
            
            if total_tokens >= self.working_tokens:
                break
        
        logger.info(f"Selected {len(selected_items)} context items using {total_tokens:,} tokens")
        return selected_items
    
    def get_relevant_context(self, current_text: str, db, project_id: int) -> List[ContextItem]:
        """Get relevant context for current writing, optimized for token limits."""
        if not current_text.strip():
            return []
        
        # Extract entities from current text
        entities = self.extract_entities(current_text)
        logger.debug(f"Extracted entities: {entities}")
        
        # Get all memory items for the project
        all_memory = []
        
        # Get characters
        characters = db.get_characters(project_id)
        for char in characters:
            all_memory.append({
                'content_type': 'character',
                'entity_id': char['id'],
                'title': char['name'],
                'content': f"{char.get('description', '')} {char.get('personality', '')} {char.get('backstory', '')}",
                'metadata': {
                    'importance': char.get('importance', 'minor'),
                    'relationships': char.get('relationships', {})
                }
            })
        
        # Get plots
        plots = db.get_plots(project_id)
        for plot in plots:
            all_memory.append({
                'content_type': 'plot',
                'entity_id': plot['id'],
                'title': plot['title'],
                'content': plot.get('description', ''),
                'metadata': {
                    'plot_type': plot.get('plot_type', 'subplot'),
                    'status': plot.get('status', 'planned')
                }
            })
        
        # Get world building
        world_building = db.get_world_building(project_id)
        for world in world_building:
            all_memory.append({
                'content_type': 'world_building',
                'entity_id': world['id'],
                'title': world['name'],
                'content': f"{world.get('description', '')} {world.get('details', '')}",
                'metadata': {
                    'category': world.get('category', 'location')
                }
            })
        
        # Calculate relevance scores and create ContextItem objects
        candidate_items = []
        for memory in all_memory:
            relevance_score = self.calculate_relevance_score(memory, current_text, entities)
            
            if relevance_score > 0:  # Only include items with some relevance
                content_text = f"{memory['title']}: {memory['content']}"
                token_estimate = self.estimate_tokens(content_text)
                
                # Determine importance level
                metadata = memory.get('metadata', {})
                importance = 'normal'
                if metadata.get('importance') == 'main' or metadata.get('plot_type') == 'main':
                    importance = 'high'
                elif metadata.get('importance') == 'supporting' or metadata.get('plot_type') == 'subplot':
                    importance = 'medium'
                
                candidate_items.append(ContextItem(
                    content_type=memory['content_type'],
                    entity_id=memory['entity_id'],
                    title=memory['title'],
                    content=content_text,
                    relevance_score=relevance_score,
                    token_estimate=token_estimate,
                    importance=importance
                ))
        
        # Optimize selection for token limits
        if candidate_items:
            return self.optimize_context_for_tokens(candidate_items)
        
        return []
    
    def format_context_for_display(self, context_items: List[ContextItem]) -> str:
        """Format context items for display to the user."""
        if not context_items:
            return "No relevant context items found."
        
        formatted = []
        total_tokens = sum(item.token_estimate for item in context_items)
        
        formatted.append(f"📋 **Active Context** ({len(context_items)} items, ~{total_tokens:,} tokens)")
        formatted.append("")
        
        # Group by content type
        by_type = {}
        for item in context_items:
            if item.content_type not in by_type:
                by_type[item.content_type] = []
            by_type[item.content_type].append(item)
        
        type_emojis = {
            'character': '👤',
            'plot': 'BOOK:',
            'world_building': '🌍'
        }
        
        for content_type, items in by_type.items():
            emoji = type_emojis.get(content_type, '📝')
            formatted.append(f"## {emoji} {content_type.replace('_', ' ').title()}")
            
            for item in sorted(items, key=lambda x: x.relevance_score, reverse=True):
                relevance_stars = "⭐" * min(5, max(1, int(item.relevance_score)))
                formatted.append(f"- **{item.title}** {relevance_stars}")
                formatted.append(f"  _{item.token_estimate} tokens, {item.importance} importance_")
            
            formatted.append("")
        
        return "\n".join(formatted)
    
    def get_context_info(self, project_id: int) -> Dict[str, Any]:
        """Get comprehensive context information."""
        total_estimated_tokens = sum(item.token_estimate for item in self.current_context)
        
        return {
            "max_tokens": self.max_tokens,
            "working_limit": self.working_tokens,
            "current_items": len(self.current_context),
            "estimated_usage": f"~{total_estimated_tokens:,} tokens",
            "remaining_capacity": f"~{self.working_tokens - total_estimated_tokens:,} tokens",
            "auto_optimization": self.auto_context,
            "optimization_status": "Active for Claude Code 200K context",
            "efficiency_features": [
                "FTS5 full-text search",
                "Relevance scoring",
                "Token estimation",
                "Smart truncation",
                "Priority-based selection"
            ]
        }
    
    def clear_context(self):
        """Clear current context."""
        self.current_context.clear()
        logger.info("Context cleared")
    
    def update_context(self, current_text: str, db, project_id: int):
        """Update context based on current writing."""
        if self.auto_context:
            self.current_context = self.get_relevant_context(current_text, db, project_id)
            logger.debug(f"Auto-updated context with {len(self.current_context)} items")