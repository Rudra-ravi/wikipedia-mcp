# Wikipedia MCP Server

A Model Context Protocol (MCP) server that retrieves information from Wikipedia to provide context to LLMs. Built by [Ravikumar E](https://github.com/Rudra-ravi), a Cybersecurity Analyst and Full-stack Developer specializing in Python development and AI integration.

## Features

- Search Wikipedia articles
- Retrieve article summaries
- Get full article content
- Extract article sections
- Find links within articles

## Installation

### Using pipx (Recommended)

```bash
# Install pipx if you don't have it
sudo apt install pipx
pipx ensurepath

# Install the Wikipedia MCP server
pipx install git+https://github.com/rudra-ravi/wikipedia-mcp.git
```

### Using a virtual environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the package
pip install git+https://github.com/rudra-ravi/wikipedia-mcp.git
```

## Usage

### Running the server

```bash
# If installed with pipx
wikipedia-mcp

# If installed in a virtual environment
source venv/bin/activate
wikipedia-mcp
```

### Configuration for Claude Desktop

Add the following to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "wikipedia": {
      "command": "wikipedia-mcp"
    }
  }
}
```

Location of the configuration file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

### Example Prompts

Once the server is running and configured with Claude Desktop, you can use prompts like:

- "Tell me about quantum computing using the Wikipedia information."
- "Summarize the history of artificial intelligence based on Wikipedia."
- "What does Wikipedia say about climate change?"

## Development

The server is built using the Model Context Protocol (MCP) Python SDK and the Wikipedia API. It provides several resources and tools for interacting with Wikipedia content.

### Local Development

```bash
# Clone the repository
git clone https://github.com/rudra-ravi/wikipedia-mcp.git
cd wikipedia-mcp

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package in development mode
pip install -e .

# Run the server
wikipedia-mcp
```

## Release Workflow

The release process is automated using GitHub Actions. Follow these steps to create a new release:

1. Update the version in `setup.py`.
2. Commit the changes and push to the `main` branch.
3. Create a new release on GitHub with the updated version tag.
4. The GitHub Actions workflow will automatically build and upload the package to PyPI.

Author: [Ravikumar E](https://github.com/rudra-ravi/wikipedia-mcp.git)

## Connect with Me

- 🌐 Portfolio: [ravikumar-dev.me](https://ravikumar-dev.me)
- 📝 Blog: [Medium](https://medium.com/@Ravikumar-e)
- 💼 LinkedIn: [in/ravi-kumar-e](https://linkedin.com/in/ravi-kumar-e)
- 🐦 Twitter: [@Ravikumar_d3v](https://twitter.com/Ravikumar_d3v)

## License

MIT 
