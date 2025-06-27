#!/usr/bin/env python3
"""
Quill MCP Installation Script

Helps users install and configure Quill MCP for Claude Desktop integration.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def get_claude_config_path() -> Path:
    """Get the Claude Desktop configuration file path for the current OS."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif system == "Windows":
        return Path(os.environ.get("APPDATA", "")) / "Claude/claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config/claude/claude_desktop_config.json"


def check_python_version() -> bool:
    """Check if Python version is 3.11 or higher."""
    version = sys.version_info
    return version.major == 3 and version.minor >= 11


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_with_uv() -> bool:
    """Install Quill MCP using uv."""
    try:
        print("[Installing] Installing Quill MCP with uv...")
        
        # Run uv sync to install dependencies
        result = subprocess.run(["uv", "sync"], check=True, capture_output=True, text=True)
        print("[SUCCESS] Dependencies installed successfully")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error installing with uv: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def install_with_pip() -> bool:
    """Install Quill MCP using pip."""
    try:
        print("[Installing] Installing Quill MCP with pip...")
        
        # Install in development mode
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                              check=True, capture_output=True, text=True)
        print("[SUCCESS] Package installed successfully")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error installing with pip: {e}")
        return False


def test_installation() -> bool:
    """Test that Quill MCP can be imported and run."""
    try:
        print("[Testing] Testing installation...")
        
        # Try to import the module
        result = subprocess.run([
            sys.executable, "-c", 
            "import quill_mcp; print('Import successful')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"[ERROR] Import test failed: {result.stderr}")
            return False
        
        # Try to run the server with --help
        result = subprocess.run([
            sys.executable, "-m", "quill_mcp.server", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"[ERROR] Server test failed: {result.stderr}")
            return False
        
        print("[SUCCESS] Installation test passed")
        return True
        
    except subprocess.TimeoutExpired:
        print("[ERROR] Installation test timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Installation test error: {e}")
        return False


def load_claude_config(config_path: Path) -> Dict[str, Any]:
    """Load existing Claude Desktop configuration."""
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARNING]  Warning: Could not read existing config: {e}")
    
    return {}


def save_claude_config(config_path: Path, config: Dict[str, Any]) -> bool:
    """Save Claude Desktop configuration."""
    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True
    except IOError as e:
        print(f"[ERROR] Error saving config: {e}")
        return False


def configure_claude_desktop(use_uv: bool = False) -> bool:
    """Configure Claude Desktop to use Quill MCP."""
    config_path = get_claude_config_path()
    print(f"[Configuring] Configuring Claude Desktop at: {config_path}")
    
    # Load existing configuration
    config = load_claude_config(config_path)
    
    # Ensure mcpServers section exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Get absolute path to current directory
    quill_path = Path.cwd().absolute()
    
    # Configure Quill MCP server
    if use_uv:
        config["mcpServers"]["quill-mcp"] = {
            "command": "uv",
            "args": [
                "run",
                "--directory", str(quill_path),
                "python", "-m", "quill_mcp.server"
            ],
            "env": {},
            "description": "Quill MCP - Local memory server for authors"
        }
    else:
        config["mcpServers"]["quill-mcp"] = {
            "command": sys.executable,
            "args": ["-m", "quill_mcp.server"],
            "env": {},
            "description": "Quill MCP - Local memory server for authors"
        }
    
    # Save configuration
    if save_claude_config(config_path, config):
        print("[SUCCESS] Claude Desktop configured successfully")
        return True
    else:
        print("[ERROR] Failed to configure Claude Desktop")
        return False


def main():
    """Main installation process."""
    print("[Quill]  Quill MCP Installation Script")
    print("=====================================")
    print()
    
    # Check Python version
    if not check_python_version():
        print("[ERROR] Python 3.11 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    print(f"[SUCCESS] Python {sys.version.split()[0]} detected")
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("[ERROR] pyproject.toml not found")
        print("   Please run this script from the Quill MCP repository root")
        sys.exit(1)
    
    # Check for uv
    use_uv = check_uv_installed()
    if use_uv:
        print("[SUCCESS] uv detected - using uv for installation")
    else:
        print("[WARNING]  uv not found - using pip for installation")
        print("   Consider installing uv for better dependency management: https://github.com/astral-sh/uv")
    
    print()
    
    # Install dependencies
    if use_uv:
        success = install_with_uv()
    else:
        success = install_with_pip()
    
    if not success:
        print("[ERROR] Installation failed")
        sys.exit(1)
    
    # Test installation
    if not test_installation():
        print("[ERROR] Installation test failed")
        sys.exit(1)
    
    print()
    
    # Configure Claude Desktop
    response = input("[Claude] Configure Claude Desktop? (Y/n): ").strip().lower()
    if response in ("", "y", "yes"):
        if configure_claude_desktop(use_uv=use_uv):
            print()
            print("[Complete] Installation completed successfully!")
            print()
            print("Next steps:")
            print("1. Restart Claude Desktop")
            print("2. Create your first project: /project new \"My Novel\"")
            print("3. Add characters: /memory add character \"Character Name\" \"Description\"")
            print("4. Start writing with persistent memory!")
            print()
            print("[Documentation] See README.md for complete usage guide")
        else:
            print()
            print("[WARNING]  Installation completed but Claude Desktop configuration failed")
            print("Please manually add Quill MCP to your Claude Desktop config")
            print("See README.md for configuration instructions")
    else:
        print()
        print("[SUCCESS] Installation completed")
        print("Manual configuration required - see README.md")
    
    print()
    print("Support: https://github.com/quill-mcp/quill-mcp/issues")


if __name__ == "__main__":
    main()