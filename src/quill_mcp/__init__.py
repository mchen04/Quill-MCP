"""
Quill MCP - Local-first Model Context Protocol server for authors.

Provides persistent memory and intelligent project management for creative writing
projects, optimized for Claude Code's 200K token context window.
"""

__version__ = "1.0.0"
__author__ = "Quill MCP Team"
__description__ = "Local-first MCP server for authors - persistent memory for creative writing"

from .server import QuillMCPServer

__all__ = ["QuillMCPServer"]