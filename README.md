# MCP Atlassian

Model Context Protocol (MCP) server for Atlassian Cloud products (Confluence and Jira). This integration is designed specifically for Atlassian Cloud instances and does not support Atlassian Server or Data Center deployments.

This is a fork of the [mcp-atlassian](https://github.com/sooperset/mcp-atlassian) repo. Here is a link to its [README](https://github.com/sooperset/mcp-atlassian/blob/main/README.md). Those details have been omitted, here.

## Initial Setup

```bash
cd <root-of-this-repo>
    
activate # Activate your Python virtual environment

pip install -e .
```

#### Required Environment Variables

- `CONFLUENCE_URL`: Confluence instance URL. Likely `https://rvohealth.atlassian.net/wiki`.
- `CONFLUENCE_USERNAME`: Confluence username. Likely paired with API token.
- `CONFLUENCE_API_TOKEN`: Confluence API token with read access to the desired spaces.
- `JIRA_URL`: Jira instance URL. Likely `https://rvohealth.atlassian.net`.
- `JIRA_USERNAME`: Jira username. Likely paired with API token.
- `JIRA_API_TOKEN`: Jira API token with read access to the desired projects.

## Standard Input/Output (stdio) Mode

This is used, for example, when configuring this MCP server to be used with Claude Desktop. As of the time of this writing, Claude Desktop does not support the HTTP mode.

1. Run the MCP server in Standard Input/Output (stdio) mode
    ```bash
    python -m mcp_atlassian --stdio
    ```

## HTTP Mode

This example uses `curl` to interact with the MCP server. You can also view our [example_client.py](example_client.py) for an example of how to call the MCP server using the `ClientSession` class.

Note: It may be useful to review the [MCP Connection Lifecycle docs](https://modelcontextprotocol.io/docs/concepts/architecture#connection-lifecycle).

1. Run the MCP server in HTTP mode
    ```bash
    python -m mcp_atlassian --http
    ```

1. Begin initialization handshake
    ```bash
    curl -X POST http://localhost:8000/mcp \
      -H "Content-Type: application/json" \
      -d '{
        "jsonrpc": "2.0",
        "id": 1,                              
        "method": "initialize",
        "params": {
          "protocolVersion": "2024-11-05",
          "capabilities": {},
          "clientInfo": {
            "name": "test-client",
            "version": "v0.0.0"
          }
        }
      }'
    ```

1. Finish initialization handshake
    ```bash
    curl -X POST http://localhost:8000/mcp \
      -H "Content-Type: application/json" \
      -d '{
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}           
      }'
    ```

1. List available MCP tools
    ```bash
    curl -X POST http://localhost:8000/mcp \
      -H "Content-Type: application/json" \
      -d '{
        "jsonrpc": "2.0",
        "id": 3,                              
        "method": "tools/list",
        "params": {}           
      }'
    ```

1. List available MCP resources
    ```bash
    curl -X POST http://localhost:8000/mcp \
      -H "Content-Type: application/json" \
      -d '{
        "jsonrpc": "2.0",
        "id": 2,                              
        "method": "resources/list",
        "params": {}           
      }'
    ```

1. Use one of the available MCP tools
    ```bash
    curl -X POST http://localhost:8000/mcp \
      -H "Content-Type: application/json" \
      -d '{
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
          "name": "confluence_search",
          "arguments": {
              "query": "space = DAP AND text ~ \"eval\" order by lastmodified DESC",
              "limit": 10
          }
        }
      }'
    ```

1. Read one of the available MCP resources
    
    > Note: Normally, you would expect to be able to use the `resources/read` method on a `uri` returned in the MCP server's `resources/list` response. However, this server seems to be somewhat broken on that front.
    >
    > Instead, it's advised to use the `tools/call` method to call the `confluence_get_page` tool with the desired `page_id`, which can be obtained by the `confluence_search` tool.
    
    ```bash
    curl -X POST http://localhost:8000/mcp \
      -H "Content-Type: application/json" \
      -d '{
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
          "name": "confluence_get_page",
          "arguments": {
              "page_id": "1150648415",              
              "include_metadata": true
          }
        }
      }'
    ```

## License

Licensed under MIT - see [LICENSE](LICENSE) file. This is not an official Atlassian product.
