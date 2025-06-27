"""
Quill MCP - Local-first Model Context Protocol server for authors.

Provides persistent memory and intelligent project management for creative writing
projects, optimized for Claude Code's 200K token context window.
"""

__version__ = "1.0.0"
__author__ = "Quill MCP Team"
__description__ = "Local-first MCP server for authors - persistent memory for creative writing"

# Import core components that don't require MCP
from .database import QuillDatabase, DatabaseError, ValidationError

# Try to import MCP server components (may fail if MCP not installed)
try:
    from .server import QuillMCPServer
    __all__ = ["QuillMCPServer", "QuillDatabase", "DatabaseError", "ValidationError"]
except ImportError:
    # MCP not available, only expose database components
    __all__ = ["QuillDatabase", "DatabaseError", "ValidationError"]