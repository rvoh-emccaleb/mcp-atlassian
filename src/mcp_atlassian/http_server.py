from typing import Union
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from mcp.types import (
    JSONRPCRequest, 
    JSONRPCNotification, 
    JSONRPCResponse, 
    JSONRPCMessage,
)
from anyio import create_memory_object_stream
import logging
from .validation import validate_request
from .mcp_methods import app as mcp_app

logger = logging.getLogger(__name__)

# Create two pairs of streams - one for each direction
client_to_server_send, client_to_server_receive = create_memory_object_stream()
server_to_client_send, server_to_client_receive = create_memory_object_stream()
server_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the MCP server lifecycle"""
    global server_task
        
    # Create a queue to track server status
    status_queue = asyncio.Queue()
    
    async def server_runner():
        try:
            await status_queue.put("starting")
                        
            init_options = mcp_app.create_initialization_options(
                notification_options=mcp_app.notification_options,
                experimental_capabilities={}
            )
            
            try:
                await mcp_app.run(
                    client_to_server_receive,  # Server reads from client
                    server_to_client_send,     # Server writes to client
                    init_options,
                    raise_exceptions=True
                )
            except* Exception as eg:  # Use except* to catch ExceptionGroup
                for e in eg.exceptions:
                    logger.error("Server task error: %s: %s", type(e).__name__, str(e))
                raise
                
            logger.info("MCP server run completed")
        except Exception as e:
            logger.error("Server error: %s", e)
            await status_queue.put(f"error: {e}")
    
    server_task = asyncio.create_task(server_runner())
    logger.debug("MCP server task created")
    
    # Wait for server to signal it's starting
    try:
        status = await asyncio.wait_for(status_queue.get(), timeout=5.0)
        if status == "starting":
            logger.info("MCP server starting")
        else:
            logger.warning("Unexpected server status: %s", status)
    except asyncio.TimeoutError:
        logger.error("Server startup timeout")
    
    yield  # Server runs during this yield
    
    logger.info("Shutting down MCP server...")
    if server_task and not server_task.done():
        server_task.cancel()
        try:
            await server_task
            logger.info("MCP server shut down cleanly")
        except asyncio.CancelledError:
            logger.info("MCP server cancelled")
        except Exception as e:
            logger.error("Error shutting down MCP server: %s", e)

api = FastAPI(title="MCP Atlassian HTTP Server", lifespan=lifespan)

@api.post("/mcp")
async def handle_mcp_request(
    request: Union[JSONRPCRequest, JSONRPCNotification]
) -> Union[JSONRPCResponse, None]:
    """
    Handle MCP requests over HTTP instead of stdio.
    
    If the request has an id, it's a JSONRPCRequest and expects a response.
    If it doesn't have an id, it's a JSONRPCNotification and doesn't expect a response.
    """

    logger.debug("MCP request received: %s", request.model_dump_json()) 
    
    try:
        validate_request(request.method, request.params)
        message = JSONRPCMessage(root=request)

        logger.debug("Received request - Method: %s, Params: %s", request.method, request.params)
        if isinstance(request, JSONRPCRequest):
            logger.debug("Request ID: %s", request.id)
        else:
            logger.debug("Request type: Notification (no id)")
        
        await client_to_server_send.send(message)
        logger.debug("Message sent to server")
        # If this was a notification (no id), return None
        if isinstance(request, JSONRPCNotification):
            return None

        try:
            logger.debug("Waiting for response from server")
            response = await asyncio.wait_for(
                server_to_client_receive.receive(),
                timeout=5.0  # 5 seconds
            )
            logger.debug("Response received from server")
            
            if isinstance(response, Exception):
                logger.error("Got exception response: %s", response)
                raise response
            
            if isinstance(response, JSONRPCMessage):
                jsonrpc_response = response.root
                if isinstance(jsonrpc_response, JSONRPCResponse):
                    return JSONRPCResponse(
                        jsonrpc=jsonrpc_response.jsonrpc,
                        id=jsonrpc_response.id,
                        result=jsonrpc_response.result
                    )
            
            raise ValueError(f"Unexpected response type: {type(response)}")
            
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for response")
            raise HTTPException(status_code=500, detail="No response received from MCP server")

    except Exception as e:
        logger.error("Error handling request: %s", e)
        if isinstance(request, JSONRPCRequest):
            return JSONRPCResponse(
                jsonrpc="2.0",
                id=request.id,
                result={
                    "error": {
                        "code": -32603,  # Internal error
                        "message": str(e)
                    }
                }
            )
        raise HTTPException(status_code=500, detail=str(e))

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the HTTP server."""
    import uvicorn
    uvicorn.run(api, host=host, port=port)

if __name__ == "__main__":
    run_server()
