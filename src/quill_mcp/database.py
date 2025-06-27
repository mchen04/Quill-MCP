"""
Database layer for Quill MCP - SQLite with FTS5 full-text search.

Handles all persistent storage for projects, characters, plots, world-building,
and other writing-related data with efficient search capabilities.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from contextlib import contextmanager
from enum import Enum

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content types for memory search."""
    CHARACTER = "character"
    PLOT = "plot" 
    WORLD_BUILDING = "world_building"
    SCENE = "scene"


class Importance(Enum):
    """Character importance levels."""
    MAIN = "main"
    SUPPORTING = "supporting"
    MINOR = "minor"


class PlotType(Enum):
    """Plot types."""
    MAIN = "main"
    SUBPLOT = "subplot"
    ARC = "arc"


class Status(Enum):
    """General status for plots and scenes."""
    PLANNED = "planned"
    ACTIVE = "active"
    DRAFT = "draft"
    COMPLETE = "complete"


class WorldCategory(Enum):
    """World building categories."""
    LOCATION = "location"
    CULTURE = "culture"
    HISTORY = "history"
    RULES = "rules"
    TECHNOLOGY = "technology"


class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class QuillDatabase:
    """Local SQLite database with FTS5 search for writing project memory."""
    
    # Database constants
    SCHEMA_VERSION = 1
    MAX_PROJECT_NAME_LENGTH = 255
    MAX_TITLE_LENGTH = 255
    CONNECTION_TIMEOUT = 30.0
    
    def __init__(self, db_path: Path):
        """Initialize database connection and ensure schema exists.
        
        Args:
            db_path: Path to SQLite database file
            
        Raises:
            DatabaseError: If database initialization fails
            ValidationError: If db_path is invalid
        """
        if not isinstance(db_path, Path):
            raise ValidationError("db_path must be a Path object")
            
        self.db_path = db_path
        self._ensure_directory_exists()
        self._check_fts5_support()
        self._init_schema()
        
        logger.info(f"QuillDatabase initialized at {db_path}")
    
    def _ensure_directory_exists(self) -> None:
        """Ensure the database directory exists."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise DatabaseError(f"Failed to create database directory: {e}") from e
    
    def _check_fts5_support(self) -> None:
        """Verify FTS5 extension is available.
        
        Raises:
            DatabaseError: If FTS5 is not available
        """
        try:
            with self._get_connection() as conn:
                conn.execute("SELECT fts5_version()").fetchone()
            logger.debug("FTS5 support confirmed")
        except sqlite3.OperationalError as e:
            raise DatabaseError(
                "SQLite FTS5 extension not available. "
                "Please ensure SQLite was compiled with FTS5 support."
            ) from e
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling and configuration.
        
        Yields:
            sqlite3.Connection: Configured database connection
            
        Raises:
            DatabaseError: If connection fails
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path, 
                timeout=self.CONNECTION_TIMEOUT,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
            conn.execute("PRAGMA synchronous = NORMAL")  # Good balance of safety/speed
            conn.execute("PRAGMA temp_store = MEMORY")  # Faster temp operations
            conn.execute("PRAGMA mmap_size = 268435456")  # 256MB memory mapping
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {e}") from e
        except Exception as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Unexpected error during database operation: {e}") from e
        finally:
            if conn:
                try:
                    conn.close()
                except sqlite3.Error:
                    logger.warning("Failed to close database connection properly")
    
    def _validate_project_name(self, name: str) -> None:
        """Validate project name.
        
        Args:
            name: Project name to validate
            
        Raises:
            ValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise ValidationError("Project name cannot be empty")
        if len(name) > self.MAX_PROJECT_NAME_LENGTH:
            raise ValidationError(f"Project name too long (max {self.MAX_PROJECT_NAME_LENGTH} characters)")
    
    def _validate_title(self, title: str) -> None:
        """Validate title fields.
        
        Args:
            title: Title to validate
            
        Raises:
            ValidationError: If title is invalid
        """
        if not title or not title.strip():
            raise ValidationError("Title cannot be empty")
        if len(title) > self.MAX_TITLE_LENGTH:
            raise ValidationError(f"Title too long (max {self.MAX_TITLE_LENGTH} characters)")
    
    def _validate_project_id(self, project_id: int) -> None:
        """Validate project ID exists.
        
        Args:
            project_id: Project ID to validate
            
        Raises:
            ValidationError: If project ID is invalid or doesn't exist
        """
        if not isinstance(project_id, int) or project_id <= 0:
            raise ValidationError("Project ID must be a positive integer")
        
        with self._get_connection() as conn:
            exists = conn.execute(
                "SELECT 1 FROM projects WHERE id = ? LIMIT 1", (project_id,)
            ).fetchone()
            if not exists:
                raise ValidationError(f"Project {project_id} does not exist")
    
    def _init_schema(self) -> None:
        """Initialize database schema with all required tables.
        
        Raises:
            DatabaseError: If schema initialization fails
        """
        try:
            with self._get_connection() as conn:
                # Projects table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    genre TEXT DEFAULT '',
                    target_words INTEGER DEFAULT 0,
                    current_words INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Characters table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    personality TEXT DEFAULT '',
                    backstory TEXT DEFAULT '',
                    appearance TEXT DEFAULT '',
                    relationships TEXT DEFAULT '{}',  -- JSON
                    importance TEXT DEFAULT 'minor',  -- main, supporting, minor
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            
            # Plots table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    plot_type TEXT DEFAULT 'main',  -- main, subplot, arc
                    status TEXT DEFAULT 'planned',  -- planned, active, completed
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            
            # World building table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS world_building (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT 'location',  -- location, culture, history, rules, technology
                    description TEXT DEFAULT '',
                    details TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            
            # Scenes table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    chapter_number INTEGER DEFAULT 1,
                    scene_number INTEGER DEFAULT 1,
                    title TEXT DEFAULT '',
                    summary TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    word_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'planned',  -- planned, draft, complete
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            
            # Writing sessions table (for analytics)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS writing_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    words_written INTEGER DEFAULT 0,
                    duration_minutes INTEGER DEFAULT 0,
                    session_date DATE DEFAULT (date('now')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            
            # Create FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_search USING fts5(
                    content_type,
                    project_id UNINDEXED,
                    entity_id UNINDEXED,
                    title,
                    content,
                    metadata
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_characters_project ON characters(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plots_project ON plots(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_world_building_project ON world_building(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scenes_project ON scenes(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project_date ON writing_sessions(project_id, session_date)")
            
            # Create triggers to update FTS5 table when content changes
            self._create_fts_triggers(conn)
            
            conn.commit()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database schema: {e}") from e
    
    def _create_fts_triggers(self, conn: sqlite3.Connection) -> None:
        """Create triggers to automatically update FTS5 index."""
        
        # Character triggers
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_characters_insert
            AFTER INSERT ON characters
            BEGIN
                INSERT INTO memory_search(content_type, project_id, entity_id, title, content, metadata)
                VALUES ('character', NEW.project_id, NEW.id, NEW.name, 
                        NEW.description || ' ' || NEW.personality || ' ' || NEW.backstory || ' ' || NEW.appearance,
                        json_object('importance', NEW.importance, 'relationships', NEW.relationships));
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_characters_update
            AFTER UPDATE ON characters
            BEGIN
                UPDATE memory_search 
                SET title = NEW.name,
                    content = NEW.description || ' ' || NEW.personality || ' ' || NEW.backstory || ' ' || NEW.appearance,
                    metadata = json_object('importance', NEW.importance, 'relationships', NEW.relationships)
                WHERE content_type = 'character' AND entity_id = NEW.id;
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_characters_delete
            AFTER DELETE ON characters
            BEGIN
                DELETE FROM memory_search WHERE content_type = 'character' AND entity_id = OLD.id;
            END
        """)
        
        # Plot triggers
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_plots_insert
            AFTER INSERT ON plots
            BEGIN
                INSERT INTO memory_search(content_type, project_id, entity_id, title, content, metadata)
                VALUES ('plot', NEW.project_id, NEW.id, NEW.title, NEW.description,
                        json_object('plot_type', NEW.plot_type, 'status', NEW.status));
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_plots_update
            AFTER UPDATE ON plots
            BEGIN
                UPDATE memory_search 
                SET title = NEW.title,
                    content = NEW.description,
                    metadata = json_object('plot_type', NEW.plot_type, 'status', NEW.status)
                WHERE content_type = 'plot' AND entity_id = NEW.id;
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_plots_delete
            AFTER DELETE ON plots
            BEGIN
                DELETE FROM memory_search WHERE content_type = 'plot' AND entity_id = OLD.id;
            END
        """)
        
        # World building triggers
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_world_building_insert
            AFTER INSERT ON world_building
            BEGIN
                INSERT INTO memory_search(content_type, project_id, entity_id, title, content, metadata)
                VALUES ('world_building', NEW.project_id, NEW.id, NEW.name, NEW.description || ' ' || NEW.details,
                        json_object('category', NEW.category));
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_world_building_update
            AFTER UPDATE ON world_building
            BEGIN
                UPDATE memory_search 
                SET title = NEW.name,
                    content = NEW.description || ' ' || NEW.details,
                    metadata = json_object('category', NEW.category)
                WHERE content_type = 'world_building' AND entity_id = NEW.id;
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_world_building_delete
            AFTER DELETE ON world_building
            BEGIN
                DELETE FROM memory_search WHERE content_type = 'world_building' AND entity_id = OLD.id;
            END
        """)
    
    # Project methods
    def create_project(self, name: str, description: str = "", genre: str = "", target_words: int = 0) -> int:
        """Create a new writing project.
        
        Args:
            name: Project name (must be unique)
            description: Optional project description
            genre: Optional genre
            target_words: Target word count (must be non-negative)
            
        Returns:
            int: ID of created project
            
        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If creation fails
        """
        self._validate_project_name(name)
        
        if target_words < 0:
            raise ValidationError("Target words must be non-negative")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO projects (name, description, genre, target_words) 
                       VALUES (?, ?, ?, ?)""",
                    (name.strip(), description, genre, target_words)
                )
                project_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created project '{name}' with ID {project_id}")
                return project_id
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValidationError(f"Project '{name}' already exists") from e
            raise DatabaseError(f"Failed to create project: {e}") from e
    
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project by ID.
        
        Args:
            project_id: Project ID to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Project data or None if not found
            
        Raises:
            ValidationError: If project_id is invalid
            DatabaseError: If query fails
        """
        if not isinstance(project_id, int) or project_id <= 0:
            raise ValidationError("Project ID must be a positive integer")
            
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM projects WHERE id = ?", (project_id,)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve project {project_id}: {e}") from e
    
    def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get project by name.
        
        Args:
            name: Project name to search for
            
        Returns:
            Optional[Dict[str, Any]]: Project data or None if not found
            
        Raises:
            ValidationError: If name is invalid
            DatabaseError: If query fails
        """
        if not name or not name.strip():
            raise ValidationError("Project name cannot be empty")
            
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM projects WHERE name = ?", (name.strip(),)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve project '{name}': {e}") from e
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects ordered by last update.
        
        Returns:
            List[Dict[str, Any]]: List of all projects
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM projects ORDER BY updated_at DESC"
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to list projects: {e}") from e
    
    def update_project(self, project_id: int, **kwargs) -> bool:
        """Update project fields."""
        if not kwargs:
            return False
        
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.now().isoformat()
        
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [project_id]
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE projects SET {fields} WHERE id = ?", values
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_project(self, project_id: int) -> bool:
        """Delete project and all associated data."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            success = cursor.rowcount > 0
            if success:
                logger.info(f"Deleted project {project_id}")
            return success
    
    # Character methods
    def add_character(self, project_id: int, name: str, **kwargs) -> int:
        """Add character to project.
        
        Args:
            project_id: Project to add character to
            name: Character name
            **kwargs: Additional character fields
            
        Returns:
            int: Character ID
            
        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If addition fails
        """
        self._validate_project_id(project_id)
        self._validate_title(name)
        
        # Validate importance if provided
        if 'importance' in kwargs:
            if kwargs['importance'] not in [e.value for e in Importance]:
                raise ValidationError(f"Invalid importance level: {kwargs['importance']}")
        
        fields = ["project_id", "name"] + list(kwargs.keys())
        placeholders = "?, ?" + ", ?" * len(kwargs)
        values = [project_id, name.strip()] + list(kwargs.values())
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    f"INSERT INTO characters ({', '.join(fields)}) VALUES ({placeholders})",
                    values
                )
                character_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Added character '{name}' to project {project_id}")
                return character_id
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to add character '{name}': {e}") from e
    
    def get_characters(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all characters for a project."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM characters WHERE project_id = ? ORDER BY importance DESC, name",
                (project_id,)
            ).fetchall()
            characters = []
            for row in rows:
                char = dict(row)
                # Parse JSON relationships
                try:
                    char['relationships'] = json.loads(char['relationships'])
                except (json.JSONDecodeError, TypeError):
                    char['relationships'] = {}
                characters.append(char)
            return characters
    
    # Plot methods
    def add_plot(self, project_id: int, title: str, **kwargs) -> int:
        """Add plot/storyline to project."""
        fields = ["project_id", "title"] + list(kwargs.keys())
        placeholders = "?, ?" + ", ?" * len(kwargs)
        values = [project_id, title] + list(kwargs.values())
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"INSERT INTO plots ({', '.join(fields)}) VALUES ({placeholders})",
                values
            )
            plot_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added plot '{title}' to project {project_id}")
            return plot_id
    
    def get_plots(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all plots for a project."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM plots WHERE project_id = ? ORDER BY plot_type, title",
                (project_id,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    # World building methods
    def add_world_building(self, project_id: int, name: str, **kwargs) -> int:
        """Add world building element to project."""
        fields = ["project_id", "name"] + list(kwargs.keys())
        placeholders = "?, ?" + ", ?" * len(kwargs)
        values = [project_id, name] + list(kwargs.values())
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"INSERT INTO world_building ({', '.join(fields)}) VALUES ({placeholders})",
                values
            )
            world_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added world building '{name}' to project {project_id}")
            return world_id
    
    def get_world_building(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all world building for a project."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM world_building WHERE project_id = ? ORDER BY category, name",
                (project_id,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    # Search methods
    def search_memory(self, query: str, project_id: Optional[int] = None, 
                     content_types: Optional[List[str]] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search through all memory using FTS5."""
        
        # Build FTS5 query
        fts_query = query
        
        # Add content type filter if specified
        where_conditions = []
        params = [fts_query]
        
        if project_id:
            where_conditions.append("project_id = ?")
            params.append(project_id)
        
        if content_types:
            placeholders = ", ".join("?" * len(content_types))
            where_conditions.append(f"content_type IN ({placeholders})")
            params.extend(content_types)
        
        where_clause = ""
        if where_conditions:
            where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        with self._get_connection() as conn:
            rows = conn.execute(f"""
                SELECT content_type, project_id, entity_id, title, 
                       snippet(memory_search, 4, '<mark>', '</mark>', '...', 32) as snippet,
                       rank
                FROM memory_search
                {where_clause}
                ORDER BY rank
                LIMIT ?
            """, params + [limit]).fetchall()
            
            return [dict(row) for row in rows]
    
    # Analytics methods
    def record_writing_session(self, project_id: int, words_written: int, duration_minutes: int) -> None:
        """Record a writing session for analytics."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO writing_sessions (project_id, words_written, duration_minutes)
                   VALUES (?, ?, ?)""",
                (project_id, words_written, duration_minutes)
            )
            conn.commit()
    
    def get_writing_stats(self, project_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """Get writing statistics."""
        where_clause = "WHERE session_date >= date('now', '-{} days')".format(days)
        if project_id:
            where_clause += f" AND project_id = {project_id}"
        
        with self._get_connection() as conn:
            # Daily stats
            daily_stats = conn.execute(f"""
                SELECT session_date, SUM(words_written) as words, SUM(duration_minutes) as minutes
                FROM writing_sessions
                {where_clause}
                GROUP BY session_date
                ORDER BY session_date DESC
            """).fetchall()
            
            # Total stats
            total_stats = conn.execute(f"""
                SELECT COUNT(DISTINCT session_date) as writing_days,
                       SUM(words_written) as total_words,
                       SUM(duration_minutes) as total_minutes,
                       AVG(words_written) as avg_words_per_session,
                       MAX(words_written) as best_session
                FROM writing_sessions
                {where_clause}
            """).fetchone()
            
            return {
                "daily_stats": [dict(row) for row in daily_stats],
                "total_stats": dict(total_stats) if total_stats else {},
                "period_days": days
            }
    
    def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """Get comprehensive project statistics."""
        with self._get_connection() as conn:
            # Basic project info
            project = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            
            if not project:
                return {}
            
            # Character count
            char_count = conn.execute(
                "SELECT COUNT(*) as count FROM characters WHERE project_id = ?", (project_id,)
            ).fetchone()[0]
            
            # Plot count
            plot_count = conn.execute(
                "SELECT COUNT(*) as count FROM plots WHERE project_id = ?", (project_id,)
            ).fetchone()[0]
            
            # World building count
            world_count = conn.execute(
                "SELECT COUNT(*) as count FROM world_building WHERE project_id = ?", (project_id,)
            ).fetchone()[0]
            
            # Scene count and progress
            scene_stats = conn.execute(
                """SELECT COUNT(*) as total_scenes, 
                          SUM(word_count) as total_words,
                          COUNT(CASE WHEN status = 'complete' THEN 1 END) as completed_scenes
                   FROM scenes WHERE project_id = ?""", (project_id,)
            ).fetchone()
            
            return {
                "project": dict(project),
                "characters": char_count,
                "plots": plot_count,
                "world_building": world_count,
                "scenes": {
                    "total": scene_stats[0],
                    "completed": scene_stats[2],
                    "completion_rate": (scene_stats[2] / scene_stats[0] * 100) if scene_stats[0] > 0 else 0
                },
                "word_count": {
                    "current": scene_stats[1] or 0,
                    "target": project["target_words"],
                    "progress": (scene_stats[1] / project["target_words"] * 100) if project["target_words"] > 0 else 0
                }
            }