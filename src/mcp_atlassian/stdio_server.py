import asyncio
import logging
from mcp.server.stdio import stdio_server

from .mcp_methods import app

logger = logging.getLogger(__name__)

async def run_stdio_server():
    """Run the MCP server using stdio transport."""
    logger.info("Starting MCP server with stdio transport...")
    
    async with stdio_server() as (read_stream, write_stream):
        init_options = app.create_initialization_options(
            notification_options=app.notification_options,
            experimental_capabilities={}
        )
        await app.run(read_stream, write_stream, init_options)

def main():
    """Main entry point for stdio server."""
    asyncio.run(run_stdio_server())

if __name__ == "__main__":
    main() 