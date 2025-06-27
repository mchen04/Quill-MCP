#!/usr/bin/env python3
"""
Fix the database initialization by creating a working minimal version.
"""

import sys
import tempfile
import sqlite3
from pathlib import Path

sys.path.insert(0, 'src')

def create_minimal_database():
    """Create a minimal working database to test our QuillDatabase class."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        # Test direct SQL execution like QuillDatabase does
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Test FTS5 support
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts5_test USING fts5(content)")
            conn.execute("DROP TABLE fts5_test")
            print("✓ FTS5 support confirmed")
            
            # Create projects table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ Projects table created")
            
            # Test inserting data
            cursor = conn.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                ("Test Project", "A test project")
            )
            project_id = cursor.lastrowid
            print(f"✓ Inserted project with ID: {project_id}")
            
            # Test retrieving data
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            assert row is not None
            assert row["name"] == "Test Project"
            print("✓ Retrieved project successfully")
            
            conn.commit()
            conn.close()
            
            print("✓ Database operations completed successfully")
            return True
            
        except Exception as e:
            print(f"✗ Database test failed: {e}")
            if 'conn' in locals():
                conn.close()
            return False

def test_quill_database_minimal():
    """Test QuillDatabase with minimal functionality."""
    
    # Let's create a version that bypasses the problematic initialization
    from quill_mcp.database import QuillDatabase, DatabaseError
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        try:
            # Create database manually first
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            # Test our database class initialization
            db = QuillDatabase.__new__(QuillDatabase)  # Create without __init__
            db.db_path = db_path
            db.CONNECTION_TIMEOUT = 30.0
            
            # Test connection method
            with db._get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            
            print("✓ QuillDatabase connection method works")
            return True
            
        except Exception as e:
            print(f"✗ QuillDatabase test failed: {e}")
            return False

if __name__ == "__main__":
    print("=== Database Fix Testing ===\n")
    
    if not create_minimal_database():
        print("✗ Minimal database test failed")
        sys.exit(1)
        
    if not test_quill_database_minimal():
        print("✗ QuillDatabase test failed")
        sys.exit(1)
    
    print("\n✓ Database functionality verified - ready to fix the full class!")