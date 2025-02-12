from typing import Any, Dict
from fastapi import HTTPException


def validate_initialize_params(params: Dict[str, Any]) -> None:
    """Validate initialize request params."""
    if params is None:
        raise HTTPException(
            status_code=400,
            detail="Initialize request requires params with protocolVersion, capabilities, and clientInfo"
        )

    required_fields = {
        "protocolVersion": "Protocol version is required for version negotiation",
        "capabilities": "Client capabilities are required for capability negotiation",
        "clientInfo": "Client implementation information is required"
    }
    missing_fields = {k: v for k, v in required_fields.items() if k not in params}
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Initialize request missing required fields",
                "missing": missing_fields
            }
        )

    if not isinstance(params["protocolVersion"], str):
        raise HTTPException(
            status_code=400,
            detail="protocolVersion must be a string"
        )

    if not isinstance(params["capabilities"], dict):
        raise HTTPException(
            status_code=400,
            detail="capabilities must be an object"
        )

    client_info = params["clientInfo"]
    if not isinstance(client_info, dict):
        raise HTTPException(
            status_code=400,
            detail="clientInfo must be an object"
        )
    if "name" not in client_info or "version" not in client_info:
        raise HTTPException(
            status_code=400,
            detail="clientInfo must include name and version"
        )

def validate_read_resource_params(params: Dict[str, Any]) -> None:
    """Validate resources/read request params."""
    if params is None or "uri" not in params:
        raise HTTPException(
            status_code=400,
            detail="resources/read request requires uri parameter"
        )

def validate_call_tool_params(params: Dict[str, Any]) -> None:
    """Validate tools/call request params."""
    if params is None or "name" not in params:
        raise HTTPException(
            status_code=400,
            detail="tools/call request requires name parameter"
        )

def validate_complete_params(params: Dict[str, Any]) -> None:
    """Validate completion/complete request params."""
    if params is None:
        raise HTTPException(
            status_code=400,
            detail="completion/complete request requires ref and argument parameters"
        )
    
    required_fields = {
        "ref": "Reference to resource or prompt is required",
        "argument": "Completion argument is required"
    }
    missing_fields = {k: v for k, v in required_fields.items() if k not in params}
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "completion/complete request missing required fields",
                "missing": missing_fields
            }
        )

VALIDATORS = {
    "initialize": validate_initialize_params,
    "resources/read": validate_read_resource_params,
    "tools/call": validate_call_tool_params,
    "completion/complete": validate_complete_params,
}

def validate_request(method: str, params: Dict[str, Any]) -> None:
    """Validate request params based on method."""
    if validator := VALIDATORS.get(method):
        validator(params) 
