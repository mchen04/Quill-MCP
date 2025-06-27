#  Quill MCP - Local-First Memory Server for Authors

**The external brain for your creative writing projects.**

Quill MCP is a free, local-first Model Context Protocol server optimized for Claude Code's 200K token context window. It provides persistent memory and intelligent project management for authors, solving the critical problem of context loss between AI writing sessions.

##  Key Features

- ** 100% Local & Private** - All your manuscripts stay on your machine
- ** Persistent Memory** - Characters, plots, world-building never forgotten
- ** Claude Code Optimized** - Intelligent 200K token context management
- ** Full-Text Search** - Find anything across your projects instantly
- ** Writing Analytics** - Track progress, word counts, and productivity
- ** Multi-Project Support** - Manage multiple books simultaneously
- ** Instant Context Switching** - Switch between projects in <1 second

##  Quick Start

### Prerequisites

- Python 3.11+ 
- Claude Code or Claude Desktop
- SQLite with FTS5 support (usually included)

### Installation

#### Option 1: Install with uv (Recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install Quill MCP
git clone https://github.com/quill-mcp/quill-mcp.git
cd quill-mcp
uv sync
```

#### Option 2: Install with pip

```bash
git clone https://github.com/quill-mcp/quill-mcp.git
cd quill-mcp
pip install -e .
```

### Configure Claude Desktop

Add Quill MCP to your Claude Desktop configuration:

**macOS/Linux**: Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: Edit `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "quill-mcp": {
      "command": "python",
      "args": ["-m", "quill_mcp.server"],
      "env": {}
    }
  }
}
```

Or if using uv:

```json
{
  "mcpServers": {
    "quill-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/quill-mcp", "python", "-m", "quill_mcp.server"],
      "env": {}
    }
  }
}
```

### First Use

1. **Restart Claude Desktop** to load Quill MCP
2. **Create your first project**:
   ```
   /project new "My Novel" "A thrilling adventure story" --genre fantasy --target-words 80000
   ```
3. **Add characters**:
   ```
   /memory add character "Elena Brightblade" "A brave knight with a mysterious past" --importance main
   ```
4. **Start writing** - Quill MCP will automatically provide relevant context!

## 📚 Core Commands

### Memory Management

```bash
# Add memory items
/memory add character "Character Name" "Description..."
/memory add plot "Plot Name" "Description..."
/memory add world_building "Location Name" "Description..."

# Search through memory
/memory search "dragons"
/memory search "Elena relationship"

# View memory
/memory show
```

### Project Management

```bash
# Create new project
/project new "Project Name" "Description" --genre fantasy --target-words 50000

# Switch projects
/project switch "Project Name"

# List all projects
/project list

# View project statistics
/project stats
```

### Context Management

```bash
# View current context
/context show

# Toggle automatic context
/context auto true
/context auto false
```

### Analytics

```bash
# View writing analytics
/analytics overview --days 30

# View project progress
/project stats
```

##  MCP Resources

Quill MCP exposes these resources for Claude Code to access:

- `memory://projects` - List all projects
- `memory://projects/{id}/overview` - Project overview with stats
- `memory://projects/{id}/characters` - All characters in project
- `memory://projects/{id}/plots` - All plots and storylines
- `memory://projects/{id}/world` - World-building elements
- `memory://context/current` - Current active context

## 🛠️ Advanced Configuration

### Custom Data Directory

```bash
# Run with custom data directory
python -m quill_mcp.server --data-dir /path/to/your/writing/data
```

### Debug Mode

```bash
# Enable debug logging
python -m quill_mcp.server --debug
```

### Environment Variables

```bash
# Set via environment variables
export QUILL_DATA_DIR=/path/to/data
export QUILL_DEBUG=true
```

##  Database Schema

Quill MCP stores data locally in SQLite with these main tables:

- **projects** - Writing projects with metadata
- **characters** - Character profiles and relationships
- **plots** - Main plots and subplots
- **world_building** - Locations, cultures, rules
- **scenes** - Chapter/scene content and progress
- **writing_sessions** - Analytics and progress tracking
- **memory_search** - FTS5 full-text search index

##  Search Capabilities

Quill MCP provides powerful search using SQLite FTS5:

- **Full-text search** across all content
- **Semantic relevance** scoring
- **Content type filtering** (characters, plots, world)
- **Project-specific** or global search
- **Snippet highlighting** in results

## 🎨 Writing Prompts

Quill MCP includes intelligent prompts for:

- **Character Development** - `character_development("Elena", "main")`
- **Plot Development** - `plot_development("main", "middle")`
- **World Building** - `world_building("location", "detailed")`
- **Writing Sessions** - `writing_session_start("continue scene", 500)`

##  Token Optimization

Optimized for Claude Code's 200K context window:

- **Smart prioritization** - Important content first
- **Relevance scoring** - Most relevant to current writing
- **Token estimation** - Efficient memory usage
- **Auto-truncation** - Graceful handling of large content
- **Buffer management** - Leaves space for generation

## 📈 Analytics Features

Track your writing progress:

- **Daily/weekly word counts**
- **Writing streak tracking**
- **Project completion percentages**
- **Character usage statistics**
- **Time spent writing**
- **Productivity trends**

##  Multi-Project Management

- **Unlimited projects** - No limits on number of books
- **Instant switching** - Change context in <1 second
- **Shared characters** - Characters can appear across projects
- **Series support** - Manage book series with shared world
- **Project comparison** - Compare stats across projects

##  Privacy & Security

- **100% local** - No cloud storage, no data transmission
- **SQLite database** - Industry-standard local storage
- **No telemetry** - Zero data collection
- **Manuscript privacy** - Your IP stays yours
- **Offline capable** - Works without internet

##  Troubleshooting

### Common Issues

**"FTS5 not available"**
```bash
# Check SQLite version and FTS5 support
python -c "import sqlite3; print(sqlite3.sqlite_version)"
python -c "import sqlite3; sqlite3.connect(':memory:').execute('SELECT fts5_version()')"
```

**Claude Desktop not finding server**
- Verify configuration file path and syntax
- Check that Python path is correct
- Restart Claude Desktop after config changes

**Permission errors**
- Ensure write permissions to data directory
- Check that Python can create files in `~/.quill-mcp/`

### Debug Mode

```bash
# Run with detailed logging
python -m quill_mcp.server --debug
```

##  Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repository
git clone https://github.com/quill-mcp/quill-mcp.git
cd quill-mcp

# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run ruff format .
uv run ruff check .
```

##  License

MIT License - see [LICENSE](LICENSE) for details.

##  Acknowledgments

- Built with [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- Uses [FastMCP](https://github.com/modelcontextprotocol/python-sdk) for rapid development
- SQLite FTS5 for powerful local search
- Inspired by the needs of the writing community

##  Support

- **Issues**: [GitHub Issues](https://github.com/quill-mcp/quill-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/quill-mcp/quill-mcp/discussions)
- **Documentation**: [Wiki](https://github.com/quill-mcp/quill-mcp/wiki)

---

**Made with  for authors who want to focus on writing, not remembering.**