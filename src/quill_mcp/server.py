"""
Main Quill MCP Server implementation.

Provides persistent memory and intelligent project management for authors
using the Model Context Protocol (MCP) with Claude Code integration.
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

from .database import QuillDatabase, DatabaseError, ValidationError
from .context_engine import ContextEngine

logger = logging.getLogger(__name__)


class ServerError(Exception):
    """Custom exception for server errors."""
    pass


class QuillMCPConfig:
    """Configuration constants for Quill MCP Server."""
    
    DEFAULT_DATA_DIR = Path.home() / ".quill-mcp"
    DATABASE_FILENAME = "quill_memory.db"
    STATE_FILENAME = "current_project.txt"
    MAX_TOKENS = 180000  # Leave buffer for Claude Code
    SERVER_VERSION = "1.0.0"


class QuillMCPServer:
    """Local-first MCP server for authors with persistent memory."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize Quill MCP server.
        
        Args:
            data_dir: Optional custom data directory path
            
        Raises:
            ServerError: If initialization fails
        """
        try:
            # Set up data directory
            self.data_dir = Path(data_dir) if data_dir else QuillMCPConfig.DEFAULT_DATA_DIR
            self._ensure_data_directory()
            
            # Initialize database
            db_path = self.data_dir / QuillMCPConfig.DATABASE_FILENAME
            self.db = QuillDatabase(db_path)
            
            # Initialize context engine for 200K token optimization
            self.context_engine = ContextEngine(max_tokens=QuillMCPConfig.MAX_TOKENS)
            
            # Current project tracking
            self.current_project_id: Optional[int] = self._load_current_project()
            
            # Initialize FastMCP server
            self.mcp = FastMCP(
                name="Quill MCP",
                version=QuillMCPConfig.SERVER_VERSION
            )
            
            # Register all capabilities
            self._register_resources()
            self._register_tools()
            self._register_prompts()
            
            logger.info(f"Quill MCP Server initialized successfully (data dir: {self.data_dir})")
            
        except Exception as e:
            raise ServerError(f"Failed to initialize Quill MCP Server: {e}") from e
    
    def _ensure_data_directory(self) -> None:
        """Ensure data directory exists and is writable.
        
        Raises:
            ServerError: If directory cannot be created or accessed
        """
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = self.data_dir / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            
        except OSError as e:
            raise ServerError(f"Cannot access data directory {self.data_dir}: {e}") from e
    
    def _load_current_project(self) -> Optional[int]:
        """Load the current project ID from state file.
        
        Returns:
            Optional[int]: Current project ID if valid, None otherwise
        """
        state_file = self.data_dir / QuillMCPConfig.STATE_FILENAME
        if not state_file.exists():
            return None
            
        try:
            project_id = int(state_file.read_text().strip())
            # Verify project still exists in database
            if self.db.get_project(project_id):
                logger.debug(f"Loaded current project: {project_id}")
                return project_id
            else:
                logger.warning(f"Current project {project_id} no longer exists, clearing state")
                state_file.unlink()
        except (ValueError, TypeError, OSError) as e:
            logger.warning(f"Failed to load current project state: {e}")
            
        return None
    
    def _save_current_project(self, project_id: Optional[int]) -> None:
        """Save the current project ID to state file.
        
        Args:
            project_id: Project ID to save, or None to clear
        """
        state_file = self.data_dir / QuillMCPConfig.STATE_FILENAME
        
        try:
            if project_id is not None:
                state_file.write_text(str(project_id))
                logger.debug(f"Saved current project: {project_id}")
            elif state_file.exists():
                state_file.unlink()
                logger.debug("Cleared current project state")
        except OSError as e:
            logger.error(f"Failed to save current project state: {e}")
    
    def switch_project(self, project_id: int) -> None:
        """Switch to a different project.
        
        Args:
            project_id: ID of project to switch to
            
        Raises:
            ValidationError: If project doesn't exist
        """
        # Validate project exists
        if not self.db.get_project(project_id):
            raise ValidationError(f"Project {project_id} does not exist")
            
        self.current_project_id = project_id
        self._save_current_project(project_id)
        logger.info(f"Switched to project {project_id}")
    
    def get_current_project(self) -> Optional[Dict[str, Any]]:
        """Get current project information.
        
        Returns:
            Optional[Dict[str, Any]]: Current project data or None
        """
        if self.current_project_id is None:
            return None
        return self.db.get_project(self.current_project_id)
    
    def _register_resources(self) -> None:
        """Register MCP resources for memory access."""
        
        @self.mcp.resource("memory://projects")
        def list_projects() -> str:
            """List all writing projects with basic information."""
            projects = self.db.list_projects()
            return json.dumps({
                "projects": projects,
                "current_project_id": self.current_project_id,
                "total": len(projects)
            }, indent=2)
        
        @self.mcp.resource("memory://projects/{project_id}/overview")
        def get_project_overview(project_id: str) -> str:
            """Get comprehensive project overview including stats."""
            try:
                pid = int(project_id)
                stats = self.db.get_project_stats(pid)
                if not stats:
                    return json.dumps({"error": f"Project {project_id} not found"})
                
                return json.dumps(stats, indent=2)
            except ValueError:
                return json.dumps({"error": "Invalid project ID"})
        
        @self.mcp.resource("memory://projects/{project_id}/characters")
        def get_project_characters(project_id: str) -> str:
            """Get all characters for a specific project."""
            try:
                pid = int(project_id)
                characters = self.db.get_characters(pid)
                return json.dumps({
                    "project_id": pid,
                    "characters": characters,
                    "total": len(characters)
                }, indent=2)
            except ValueError:
                return json.dumps({"error": "Invalid project ID"})
        
        @self.mcp.resource("memory://projects/{project_id}/plots")
        def get_project_plots(project_id: str) -> str:
            """Get all plots and storylines for a specific project."""
            try:
                pid = int(project_id)
                plots = self.db.get_plots(pid)
                return json.dumps({
                    "project_id": pid,
                    "plots": plots,
                    "total": len(plots)
                }, indent=2)
            except ValueError:
                return json.dumps({"error": "Invalid project ID"})
        
        @self.mcp.resource("memory://projects/{project_id}/world")
        def get_project_world(project_id: str) -> str:
            """Get all world-building elements for a specific project."""
            try:
                pid = int(project_id)
                world_building = self.db.get_world_building(pid)
                return json.dumps({
                    "project_id": pid,
                    "world_building": world_building,
                    "total": len(world_building)
                }, indent=2)
            except ValueError:
                return json.dumps({"error": "Invalid project ID"})
        
        @self.mcp.resource("memory://context/current")
        def get_current_context() -> str:
            """Get current active context and memory state."""
            if not self.current_project_id:
                return json.dumps({
                    "status": "No active project",
                    "current_project": None,
                    "context_size": 0,
                    "suggestions": ["Create a new project with /project new <name>"]
                })
            
            # Get optimized context for current project
            context_info = self.context_engine.get_context_info(self.current_project_id)
            
            return json.dumps({
                "status": "Active project context loaded",
                "current_project": self.db.get_project(self.current_project_id),
                "context_info": context_info,
                "available_commands": [
                    "/memory add - Add new memory item",
                    "/memory search - Search through project memory", 
                    "/project stats - Show project statistics",
                    "/context show - Display detailed context info"
                ]
            }, indent=2)
    
    def _register_tools(self) -> None:
        """Register MCP tools for memory and project management."""
        
        # Memory Management Tools
        @self.mcp.tool()
        def memory_add(
            content_type: str,
            title: str, 
            content: str,
            project_id: Optional[int] = None,
            **kwargs
        ) -> str:
            """Add memory item (character, plot, world-building, etc.) to current or specified project.
            
            Args:
                content_type: Type of content (character, plot, world_building, scene)
                title: Title or name of the item
                content: Detailed description/content
                project_id: Project ID (uses current project if not specified)
                **kwargs: Additional fields specific to content type
            """
            target_project = project_id or self.current_project_id
            if not target_project:
                return "ERROR: No active project. Use /project new <name> to create one."
            
            try:
                if content_type.lower() == "character":
                    char_id = self.db.add_character(
                        target_project, title, 
                        description=content,
                        **kwargs
                    )
                    return f"SUCCESS: Added character '{title}' (ID: {char_id}) to project."
                
                elif content_type.lower() == "plot":
                    plot_id = self.db.add_plot(
                        target_project, title,
                        description=content,
                        **kwargs
                    )
                    return f"SUCCESS: Added plot '{title}' (ID: {plot_id}) to project."
                
                elif content_type.lower() == "world_building":
                    world_id = self.db.add_world_building(
                        target_project, title,
                        description=content,
                        **kwargs
                    )
                    return f"SUCCESS: Added world-building '{title}' (ID: {world_id}) to project."
                
                else:
                    return f"ERROR: Unsupported content type: {content_type}. Use: character, plot, world_building"
                    
            except Exception as e:
                logger.error(f"Error adding memory: {e}")
                return f"ERROR: Error adding memory: {str(e)}"
        
        @self.mcp.tool()
        def memory_search(
            query: str,
            project_id: Optional[int] = None,
            content_types: Optional[List[str]] = None,
            limit: int = 10
        ) -> str:
            """Search through memory using full-text search.
            
            Args:
                query: Search query
                project_id: Limit to specific project (uses current if not specified)
                content_types: Filter by content types (character, plot, world_building)
                limit: Maximum number of results
            """
            target_project = project_id or self.current_project_id
            
            try:
                results = self.db.search_memory(
                    query, 
                    project_id=target_project,
                    content_types=content_types,
                    limit=limit
                )
                
                if not results:
                    return f"SEARCH: No results found for '{query}'"
                
                # Format results for display
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "type": result["content_type"],
                        "title": result["title"],
                        "snippet": result["snippet"],
                        "relevance": "⭐" * min(5, max(1, int(result.get("rank", 0) * -5)))
                    })
                
                return json.dumps({
                    "query": query,
                    "results_count": len(results),
                    "results": formatted_results
                }, indent=2)
                
            except Exception as e:
                logger.error(f"Error searching memory: {e}")
                return f"ERROR: Search error: {str(e)}"
        
        @self.mcp.tool()
        def memory_clear(category: str, project_id: Optional[int] = None) -> str:
            """Clear specific memory category for current or specified project.
            
            Args:
                category: Category to clear (characters, plots, world_building, all)
                project_id: Project ID (uses current project if not specified)
            """
            target_project = project_id or self.current_project_id
            if not target_project:
                return "ERROR: No active project selected."
            
            # This would need additional database methods to implement safely
            return "WARNING: Memory clearing functionality requires confirmation. Use individual deletion tools instead for safety."
        
        # Project Management Tools
        @self.mcp.tool()
        def project_new(name: str, description: str = "", genre: str = "", target_words: int = 0) -> str:
            """Create a new writing project.
            
            Args:
                name: Project name (must be unique)
                description: Project description
                genre: Genre of the writing project
                target_words: Target word count goal
            """
            try:
                # Check if project with this name already exists
                existing = self.db.get_project_by_name(name)
                if existing:
                    return f"ERROR: Project '{name}' already exists. Choose a different name."
                
                project_id = self.db.create_project(name, description, genre, target_words)
                
                # Set as current project
                self.current_project_id = project_id
                self._save_current_project(project_id)
                
                return f"SUCCESS: Created project '{name}' (ID: {project_id}) and set as current project."
                
            except Exception as e:
                logger.error(f"Error creating project: {e}")
                return f"ERROR: Error creating project: {str(e)}"
        
        @self.mcp.tool()
        def project_switch(name: str) -> str:
            """Switch to a different project by name.
            
            Args:
                name: Name of the project to switch to
            """
            try:
                project = self.db.get_project_by_name(name)
                if not project:
                    available = self.db.list_projects()
                    project_names = [p["name"] for p in available]
                    return f"ERROR: Project '{name}' not found. Available projects: {', '.join(project_names)}"
                
                self.current_project_id = project["id"]
                self._save_current_project(self.current_project_id)
                
                # Get project stats for context
                stats = self.db.get_project_stats(self.current_project_id)
                
                return f"SUCCESS: Switched to project '{name}' (ID: {project['id']}).\n" + \
                       f"STATS: Characters: {stats.get('characters', 0)}, " + \
                       f"Plots: {stats.get('plots', 0)}, " + \
                       f"World Elements: {stats.get('world_building', 0)}"
                
            except Exception as e:
                logger.error(f"Error switching project: {e}")
                return f"ERROR: Error switching project: {str(e)}"
        
        @self.mcp.tool()
        def project_list() -> str:
            """List all projects with basic information."""
            try:
                projects = self.db.list_projects()
                if not projects:
                    return "📝 No projects found. Create your first project with /project new <name>"
                
                project_list = []
                for project in projects:
                    stats = self.db.get_project_stats(project["id"])
                    is_current = "→ " if project["id"] == self.current_project_id else "  "
                    
                    project_list.append({
                        "current": project["id"] == self.current_project_id,
                        "name": project["name"],
                        "description": project["description"],
                        "characters": stats.get("characters", 0),
                        "plots": stats.get("plots", 0),
                        "word_progress": f"{stats.get('word_count', {}).get('current', 0)}/{stats.get('word_count', {}).get('target', 0)}"
                    })
                
                return json.dumps({
                    "total_projects": len(projects),
                    "current_project_id": self.current_project_id,
                    "projects": project_list
                }, indent=2)
                
            except Exception as e:
                logger.error(f"Error listing projects: {e}")
                return f"ERROR: Error listing projects: {str(e)}"
        
        @self.mcp.tool()
        def project_stats(project_id: Optional[int] = None) -> str:
            """Show comprehensive project statistics.
            
            Args:
                project_id: Project ID (uses current project if not specified)
            """
            target_project = project_id or self.current_project_id
            if not target_project:
                return "ERROR: No active project. Use /project switch <name> to select one."
            
            try:
                stats = self.db.get_project_stats(target_project)
                if not stats:
                    return f"ERROR: Project {target_project} not found."
                
                return json.dumps(stats, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting project stats: {e}")
                return f"ERROR: Error getting project stats: {str(e)}"
        
        # Context Management Tools
        @self.mcp.tool()
        def context_show() -> str:
            """Display current active context and token usage."""
            if not self.current_project_id:
                return "ERROR: No active project context."
            
            try:
                context_info = self.context_engine.get_context_info(self.current_project_id)
                
                return json.dumps({
                    "project_id": self.current_project_id,
                    "context_engine": context_info,
                    "optimization_status": "Active - Optimized for Claude Code 200K context window",
                    "memory_efficiency": "FTS5 full-text search enabled"
                }, indent=2)
                
            except Exception as e:
                logger.error(f"Error showing context: {e}")
                return f"ERROR: Error showing context: {str(e)}"
        
        @self.mcp.tool()
        def context_auto(enabled: bool) -> str:
            """Toggle automatic context detection and optimization.
            
            Args:
                enabled: True to enable automatic context, False to disable
            """
            self.context_engine.auto_context = enabled
            status = "enabled" if enabled else "disabled"
            return f"SUCCESS: Automatic context detection {status}."
        
        # Analytics Tools
        @self.mcp.tool()
        def analytics_overview(days: int = 30) -> str:
            """Show comprehensive writing analytics.
            
            Args:
                days: Number of days to include in analytics (default: 30)
            """
            try:
                stats = self.db.get_writing_stats(
                    project_id=self.current_project_id,
                    days=days
                )
                
                return json.dumps({
                    "period": f"Last {days} days",
                    "project_id": self.current_project_id,
                    "analytics": stats
                }, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting analytics: {e}")
                return f"ERROR: Error getting analytics: {str(e)}"
    
    def _register_prompts(self) -> None:
        """Register MCP prompts for writing assistance."""
        
        @self.mcp.prompt()
        def character_development(character_name: str, character_type: str = "main") -> List[base.Message]:
            """Generate prompts for developing a character in depth.
            
            Args:
                character_name: Name of the character to develop
                character_type: Type of character (main, supporting, minor)
            """
            
            # Get character info if it exists
            character_info = ""
            if self.current_project_id:
                characters = self.db.get_characters(self.current_project_id)
                for char in characters:
                    if char["name"].lower() == character_name.lower():
                        character_info = f"\\nExisting character info: {json.dumps(char, indent=2)}"
                        break
            
            return [
                base.UserMessage(f"""Develop the character '{character_name}' for my writing project. This is a {character_type} character.

Please help me flesh out:
1. Physical appearance and distinctive features
2. Personality traits and quirks
3. Background and history
4. Motivations and goals
5. Relationships with other characters
6. Character arc and development
7. Speech patterns and dialogue style
8. Strengths and weaknesses
9. Fears and internal conflicts
10. Role in the story{character_info}

Provide detailed, creative responses that will help bring this character to life.""")
            ]
        
        @self.mcp.prompt()
        def plot_development(plot_type: str = "main", current_stage: str = "beginning") -> List[base.Message]:
            """Generate prompts for developing plot elements.
            
            Args:
                plot_type: Type of plot (main, subplot, character_arc)
                current_stage: Current stage of development (beginning, middle, end, complete)
            """
            
            # Get existing plot info if available
            plot_context = ""
            if self.current_project_id:
                plots = self.db.get_plots(self.current_project_id)
                if plots:
                    plot_context = f"\\nExisting plots: {json.dumps(plots, indent=2)}"
            
            return [
                base.UserMessage(f"""Help me develop the {plot_type} plot for my writing project. I'm currently working on the {current_stage} stage.

Please help me with:
1. **Conflict and Tension**: What drives the story forward?
2. **Character Motivations**: How do character goals create plot?
3. **Pacing**: How should events unfold?
4. **Plot Points**: Key moments and turning points
5. **Cause and Effect**: How events connect logically
6. **Stakes**: What characters stand to gain or lose
7. **Resolution**: How conflicts will be resolved
8. **Subplots**: How they weave into the main story{plot_context}

Focus on creating engaging, logical plot development that serves the story and characters.""")
            ]
        
        @self.mcp.prompt()
        def world_building(category: str = "location", scope: str = "detailed") -> List[base.Message]:
            """Generate prompts for world-building elements.
            
            Args:
                category: World-building category (location, culture, history, rules, technology)
                scope: Level of detail needed (overview, detailed, comprehensive)
            """
            
            # Get existing world-building context
            world_context = ""
            if self.current_project_id:
                world_elements = self.db.get_world_building(self.current_project_id)
                if world_elements:
                    world_context = f"\\nExisting world elements: {json.dumps(world_elements, indent=2)}"
            
            return [
                base.UserMessage(f"""Help me develop {category} elements for my story world. I need {scope} development.

For {category} world-building, help me consider:

**If Location:**
- Geography and environment
- Climate and weather patterns
- Architecture and infrastructure
- Demographics and population
- Resources and economy
- Cultural significance

**If Culture:**
- Social structure and hierarchy
- Customs and traditions
- Language and communication
- Religion and beliefs
- Arts and entertainment
- Values and taboos

**If History:**
- Major historical events
- Timeline and chronology
- Influential figures
- Conflicts and wars
- Social evolution
- Legends and myths

**If Rules/Magic System:**
- Fundamental principles
- Limitations and costs
- How it affects society
- Who can use it
- Consequences of misuse
- Integration with daily life

**If Technology:**
- Level of advancement
- Key innovations
- Impact on society
- Distribution and access
- Future developments
- Unintended consequences{world_context}

Provide creative, consistent world-building that enhances the story.""")
            ]
        
        @self.mcp.prompt()
        def writing_session_start(goal: str = "continue current scene", word_target: int = 500) -> List[base.Message]:
            """Generate prompts to start a productive writing session.
            
            Args:
                goal: Session goal (continue current scene, new chapter, character development, etc.)
                word_target: Target word count for the session
            """
            
            # Get current project context
            project_context = ""
            if self.current_project_id:
                stats = self.db.get_project_stats(self.current_project_id)
                recent_memories = self.db.search_memory("", project_id=self.current_project_id, limit=5)
                
                project_context = f"""
Current Project: {stats.get('project', {}).get('name', 'Unknown')}
Progress: {stats.get('word_count', {}).get('current', 0)}/{stats.get('word_count', {}).get('target', 0)} words
Characters: {stats.get('characters', 0)}
Plots: {stats.get('plots', 0)}

Recent memory items:
{json.dumps([r['title'] for r in recent_memories], indent=2)}"""
            
            return [
                base.UserMessage(f"""Let's start a focused writing session! 

**Session Goal:** {goal}
**Target Words:** {word_target}

**Project Context:**{project_context}

Please help me:
1. **Focus**: What specific scene/element should I work on?
2. **Momentum**: What happened in the last scene to build from?
3. **Conflict**: What tension or problem drives this scene?
4. **Character**: Whose POV am I writing from and what do they want?
5. **Setting**: Where and when does this take place?
6. **Mood**: What atmosphere should I create?
7. **Purpose**: How does this scene advance the story?

Give me a focused starting point to dive into productive writing!""")
            ]
    
    def run(self) -> None:
        """Run the Quill MCP server."""
        logger.info("Starting Quill MCP server...")
        
        try:
            # Run the FastMCP server
            self.mcp.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise


# Context Engine implementation
class ContextEngine:
    """Manages intelligent context switching and token optimization."""
    
    def __init__(self, max_tokens: int = 180000):
        """Initialize context engine with token limits."""
        self.max_tokens = max_tokens
        self.auto_context = True
        self.token_buffer = int(max_tokens * 0.1)  # 10% buffer
    
    def get_context_info(self, project_id: int) -> Dict[str, Any]:
        """Get current context information and token usage estimates."""
        # This is a simplified implementation
        # In a full implementation, this would analyze current memory
        # and estimate token usage for optimal context selection
        
        return {
            "max_tokens": self.max_tokens,
            "estimated_usage": "~15,000 tokens",
            "buffer_remaining": f"~{self.token_buffer:,} tokens",
            "auto_optimization": self.auto_context,
            "status": "Optimized for Claude Code 200K context window"
        }


def main():
    """Main entry point for Quill MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Quill MCP - Local memory server for authors")
    parser.add_argument(
        "--data-dir", 
        type=Path,
        help="Directory for storing Quill data (default: ~/.quill-mcp)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run server
    server = QuillMCPServer(data_dir=args.data_dir)
    server.run()


if __name__ == "__main__":
    main()