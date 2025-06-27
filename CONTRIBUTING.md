# Contributing to Quill MCP

Thank you for your interest in contributing to Quill MCP! We welcome contributions from developers and writers who want to improve the experience for authors using AI writing tools.

##  Ways to Contribute

### For Developers
- **Bug fixes** - Fix issues in the core MCP server
- **Feature additions** - Add new tools, resources, or prompts
- **Performance improvements** - Optimize database queries, context engine
- **Documentation** - Improve code documentation and user guides
- **Testing** - Add test coverage for new features

### For Writers/Authors
- **Feature requests** - Tell us what memory features you need
- **Bug reports** - Report issues you encounter while writing
- **Prompt templates** - Contribute writing prompts that help authors
- **Use case documentation** - Share how you use Quill MCP
- **Beta testing** - Try new features and provide feedback

##  Getting Started

### Development Environment Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/quill-mcp.git
   cd quill-mcp
   ```

2. **Set up development environment**
   ```bash
   # Using uv (recommended)
   uv sync --dev
   
   # Or using pip
   pip install -e ".[dev]"
   ```

3. **Run tests to verify setup**
   ```bash
   uv run pytest
   # or
   pytest
   ```

4. **Run the server locally**
   ```bash
   uv run python -m quill_mcp.server --debug
   ```

### Code Quality Tools

We use several tools to maintain code quality:

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy src/quill_mcp/

# Run all quality checks
uv run pytest && uv run ruff check . && uv run mypy src/quill_mcp/
```

##  Development Guidelines

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and small (< 50 lines when possible)

### Database Changes
- Always use migrations for schema changes
- Test with existing data to ensure backward compatibility
- Update both the schema and any related triggers
- Document any breaking changes

### MCP Protocol
- Follow the official MCP specification
- Use FastMCP patterns for consistency
- Ensure all tools return proper error messages
- Test resources, tools, and prompts thoroughly

### Testing
- Write tests for all new features
- Include both unit and integration tests
- Test database operations with real SQLite
- Mock external dependencies appropriately

##  Adding New Features

### Adding a New Tool

1. **Define the tool logic** in `src/quill_mcp/tools/`
2. **Add database operations** if needed in `database.py`
3. **Register the tool** in `server.py`
4. **Write tests** for the tool functionality
5. **Update documentation** with examples

Example tool structure:
```python
@self.mcp.tool()
def my_new_tool(param1: str, param2: int = 0) -> str:
    """Brief description of what the tool does.
    
    Args:
        param1: Description of parameter
        param2: Optional parameter with default
    """
    try:
        # Tool implementation
        result = do_something(param1, param2)
        return f"✅ Success: {result}"
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return f"❌ Error: {str(e)}"
```

### Adding a New Resource

1. **Define the resource** in `server.py`
2. **Add database queries** if needed
3. **Format as JSON** for MCP consumption
4. **Test with Claude Code**

### Adding Writing Prompts

1. **Create prompt function** in `server.py`
2. **Use clear argument descriptions**
3. **Return structured messages**
4. **Test with actual writing scenarios**

##  Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_database.py

# Run with coverage
uv run pytest --cov=quill_mcp

# Run integration tests
uv run pytest tests/integration/
```

### Test Structure

- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests with real database
- `tests/fixtures/` - Test data and fixtures
- `tests/conftest.py` - Shared test configuration

### Writing Tests

```python
import pytest
from quill_mcp.database import QuillDatabase

def test_add_character():
    """Test adding a character to a project."""
    db = QuillDatabase(":memory:")  # Use in-memory DB for tests
    
    # Create test project
    project_id = db.create_project("Test Project")
    
    # Add character
    char_id = db.add_character(
        project_id, 
        "Test Character", 
        description="A test character"
    )
    
    # Verify character was added
    characters = db.get_characters(project_id)
    assert len(characters) == 1
    assert characters[0]["name"] == "Test Character"
```

## 📚 Documentation

### Code Documentation
- Use clear, descriptive docstrings
- Include parameter types and descriptions
- Provide usage examples where helpful
- Document any side effects or requirements

### User Documentation
- Update README.md for new features
- Add examples to the documentation
- Include screenshots for UI changes
- Update the changelog

##  Reporting Issues

### Bug Reports
Please include:
- **Quill MCP version**
- **Python version**
- **Operating system**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Error messages/logs**
- **Database schema version** (if relevant)

### Feature Requests
Please include:
- **Use case description** - How would this help authors?
- **Proposed solution** - What should the feature do?
- **Alternative approaches** - Other ways to solve the problem
- **Implementation ideas** - Technical suggestions (optional)

##  Pull Request Process

### Before Submitting
1. **Create an issue** to discuss major changes
2. **Fork the repository** and create a feature branch
3. **Write tests** for your changes
4. **Update documentation** as needed
5. **Run all quality checks**

### PR Guidelines
- **Clear title** describing the change
- **Detailed description** explaining why and how
- **Link to related issues**
- **Screenshots** for UI changes
- **Breaking changes** clearly marked

### Review Process
1. **Automated checks** must pass (tests, linting, type checking)
2. **Code review** by maintainers
3. **Testing** with real writing scenarios
4. **Documentation review**
5. **Merge** when approved

##  Recognition

Contributors will be:
- **Listed in CONTRIBUTORS.md**
- **Mentioned in release notes**
- **Given credit in documentation**
- **Invited to maintainer discussions** for major contributors

##  Getting Help

- **GitHub Discussions** - Ask questions and share ideas
- **GitHub Issues** - Report bugs and request features
- **Discord** - Join our community chat (link in README)
- **Email** - Contact maintainers for sensitive issues

##  Development Roadmap

### Short Term (Next Release)
- [ ] Enhanced character relationship tracking
- [ ] Scene-by-scene writing progress
- [ ] Export functionality (DOCX, PDF)
- [ ] Writing goal templates

### Medium Term
- [ ] Series management across projects
- [ ] Collaborative features for writing groups
- [ ] Advanced analytics dashboard
- [ ] Plugin system for custom tools

### Long Term
- [ ] Integration with writing software (Scrivener, etc.)
- [ ] Mobile companion app
- [ ] Advanced AI writing assistance
- [ ] Community prompt sharing

##  Code of Conduct

### Our Standards
- **Be respectful** to all contributors
- **Focus on constructive feedback**
- **Welcome newcomers** and help them learn
- **Respect different writing styles** and approaches
- **Keep discussions technical** and on-topic

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or inflammatory comments
- Publishing private information
- Spam or self-promotion
- Off-topic discussions

##  License

By contributing to Quill MCP, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make Quill MCP better for authors everywhere! 