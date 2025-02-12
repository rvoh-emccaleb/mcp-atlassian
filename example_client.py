import asyncio
import logging
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

# Load environment variables from .env file
load_dotenv()

# Configure logging first, before creating any loggers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configure logger for this module
logger = logging.getLogger(__name__)

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

def get_server_params() -> StdioServerParameters:
    """Create server parameters with environment variables."""
    return StdioServerParameters(
        command=sys.executable,  # Use current Python interpreter
        args=["-m", "mcp_atlassian.stdio_server"],
        env={
            "CONFLUENCE_API_TOKEN": os.environ.get("CONFLUENCE_API_TOKEN"),
            "CONFLUENCE_URL": os.environ.get("CONFLUENCE_URL"),
            "CONFLUENCE_USERNAME": os.environ.get("CONFLUENCE_USERNAME"),
            "JIRA_API_TOKEN": os.environ.get("JIRA_API_TOKEN"),
            "JIRA_URL": os.environ.get("JIRA_URL"),
            "JIRA_USERNAME": os.environ.get("JIRA_USERNAME"),
            "REQUESTS_CA_BUNDLE": os.environ.get("REQUESTS_CA_BUNDLE"),
        }
    )

async def list_resources(session: ClientSession) -> None:
    """List available resources from the server."""
    response = await session.list_resources()
    logger.debug("Raw response: %s", response)
    logger.info("Available Resources:")
    
    # Response is a Pydantic model with a resources field
    if hasattr(response, 'resources') and response.resources:
        for resource in response.resources:
            logger.info("  - %s (%s)", resource.name, resource.uri)
    else:
        logger.info("No resources found")

async def list_tools(session: ClientSession) -> None:
    """List available tools from the server."""
    response = await session.list_tools()
    logger.debug("Raw response: %s", response)
    logger.info("Available Tools:")
    
    # Response is a Pydantic model with a tools field
    if hasattr(response, 'tools') and response.tools:
        for tool in response.tools:
            logger.info("  - %s: %s", tool.name, tool.description)
    else:
        logger.info("No tools found")

async def search_confluence(session: ClientSession) -> None:
    """Example: Search Confluence."""
    result = await session.call_tool(
        "confluence_search",
        {
            "query": "type=page AND space=DAP",
            "limit": 5
        }
    )
    logger.info("Search Results: %s", result)

async def main():
    """Main entry point for the test client."""
    server = get_server_params()
    
    logger.info("Running MCP test client examples with server using stdio transport...")
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            logger.info("Session initialized")
            
            # Run test operations
            await list_resources(session)
            await list_tools(session)
            await search_confluence(session)

if __name__ == "__main__":
    asyncio.run(main())
