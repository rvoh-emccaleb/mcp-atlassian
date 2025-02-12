import argparse
import logging
from typing import Optional

__version__ = "0.1.7"

def main(mode: Optional[str] = None):
    """
    Main entry point for the package.
    
    Args:
        mode: Either 'http' or 'stdio' (default based on arguments)
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    if mode is None:
        parser = argparse.ArgumentParser(description='MCP Atlassian Server')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--http', action='store_true', help='Use HTTP transport')
        group.add_argument('--stdio', action='store_true', help='Use stdio transport')
        args = parser.parse_args()
        mode = 'http' if args.http else 'stdio'
    
    logger.info("Starting MCP Atlassian server in %s mode...", mode)
    
    if mode == 'http':
        from .http_server import run_server
        run_server()
    else:
        from .stdio_server import main
        main()

__all__ = ["main", "__version__"]
