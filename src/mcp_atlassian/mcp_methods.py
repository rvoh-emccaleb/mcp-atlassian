import json
import logging
from collections.abc import Sequence
from typing import Any

from mcp.server import Server
from mcp.types import (
    Resource, 
    TextContent, 
    Tool,
)
from pydantic import AnyUrl

from .confluence import ConfluenceFetcher
from .jira import JiraFetcher

logger = logging.getLogger(__name__)

# Initialize the content fetchers and server
confluence_fetcher = ConfluenceFetcher()
jira_fetcher = JiraFetcher()
app = Server("mcp-atlassian")

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available Confluence spaces and Jira projects as resources."""
    logger.debug("Listing resources...")
    resources = []

    # Add Confluence spaces
    spaces_response = confluence_fetcher.get_spaces()
    if isinstance(spaces_response, dict) and "results" in spaces_response:
        spaces = spaces_response["results"]
        resources.extend(
            [
                Resource(
                    uri=AnyUrl(f"confluence://{space['key']}"),
                    name=f"Confluence Space: {space['name']}",
                    mimeType="text/plain",
                    description=space.get("description", {}).get("plain", {}).get("value", ""),
                )
                for space in spaces
            ]
        )
        logger.debug("Found %d Confluence spaces", len(spaces))

    # Add Jira projects
    try:
        projects = jira_fetcher.jira.projects()
        resources.extend(
            [
                Resource(
                    uri=AnyUrl(f"jira://{project['key']}"),
                    name=f"Jira Project: {project['name']}",
                    mimeType="text/plain",
                    description=project.get("description", ""),
                )
                for project in projects
            ]
        )
        logger.debug("Found %d Jira projects", len(projects))
        
    except Exception as e:
        if hasattr(e, 'response'):
            logger.error(
                "Error fetching Jira projects: HTTP %s - %s (%s)", 
                e.response.status_code if hasattr(e, 'response') else 'Unknown',
                str(e) or "No error message", 
                type(e).__name__
            )
            logger.debug("Response content: %s", e.response.text if hasattr(e, 'response') else 'No response content')
        else:
            logger.error("Error fetching Jira projects: %s (%s)", str(e) or "No error message", type(e).__name__)
        logger.debug("Exception details:", exc_info=True)

    logger.info("Listed %d total resources", len(resources))
    return resources


@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Read content from Confluence or Jira."""
    uri_str = str(uri)

    # Handle Confluence resources
    if uri_str.startswith("confluence://"):
        parts = uri_str.replace("confluence://", "").split("/")

        # Handle space listing
        if len(parts) == 1:
            space_key = parts[0]
            documents = confluence_fetcher.get_space_pages(space_key)
            content = []
            for doc in documents:
                content.append(f"# {doc.metadata['title']}\n\n{doc.page_content}\n---")
            return "\n\n".join(content)

        # Handle specific page
        elif len(parts) >= 3 and parts[1] == "pages":
            space_key = parts[0]
            title = parts[2]
            doc = confluence_fetcher.get_page_by_title(space_key, title)

            if not doc:
                raise ValueError(f"Page not found: {title}")

            return doc.page_content

    # Handle Jira resources
    elif uri_str.startswith("jira://"):
        parts = uri_str.replace("jira://", "").split("/")

        # Handle project listing
        if len(parts) == 1:
            project_key = parts[0]
            issues = jira_fetcher.get_project_issues(project_key)
            content = []
            for issue in issues:
                content.append(f"# {issue.metadata['key']}: {issue.metadata['title']}\n\n{issue.page_content}\n---")
            return "\n\n".join(content)

        # Handle specific issue
        elif len(parts) >= 3 and parts[1] == "issues":
            issue_key = parts[2]
            issue = jira_fetcher.get_issue(issue_key)
            return issue.page_content

    raise ValueError(f"Invalid resource URI: {uri}")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Confluence and Jira tools."""
    return [
        Tool(
            name="confluence_search",
            description="Search Confluence content using CQL",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": """CQL (Confluence Query Language) query string (e.g. 'type=page AND space=DEV').

Note, every query should have a "space" in it, otherwise it will likely
return no results.

Here is a list of spaces you can search for pages in, and their high-level names. You will use the value before the ':' in your query, e.g. DAP:
- AO: AI Ops
- DAP: AI Products
- CoreProductsServices: Core Products & Services
- OSS: Open Source Software
- RP: Red Platform - Red Platform is a suite of technology products that enable data-driven and personalized experiences.
- RA: RVO Auth
- RBP: RVOH Best Practices
- HPM: RVO Technical Project Management

The "~" operator is used to search for content where the value of the specified field matches the specified value (either an exact match or a "fuzzy" match -- see examples below). The "~" operator can only be used with text fields, for example:
- title
- text

Confluence supports single and multiple character wildcard searches. Wildcard characters need to be enclosed in quote-marks, as they are reserved characters in CQL.
To perform a single character wildcard search use the "?" symbol.
To perform a multiple character wildcard search use the "*" symbol.

Some examples:

Find all content where the title contains the word "win" (or simple derivatives of that word, such as "wins").
title ~ win

Find all content where the text containing "text" or "test" (not "tempt") you can use the search:
text ~ "te?t"

Find all content where the text contains a wild-card match for the word "win" (e.g Windows, Win95 or WindowsNT).
text ~ "win*"

Find all content where the text contains "Win95" or "Windows95" you can use the search:
text ~ "wi*95"

Find all content where the text contains the word "advanced" and the word "search".
text ~ "advanced search"

In CQL, searching for specific text within content requires the use of the text field combined with the ~ operator. Additionally, when combining multiple search terms, each term should be enclosed in double quotes and connected using the OR operator within the text field.
For example:
type=page AND space=HPM AND (text ~ "technical decisions" OR text ~ "engineering autonomy" OR text ~ "product engineering partnership")

Some other CQL examples (all should also have `space = SPACE_NAME and type=page`):

creator = "99:27935d01-XXXX-XXXX-XXXX-a9b8d3b2ae2e"

title = "\"Advanced Searching\""

not creator = "99:27935d01-XXXX-XXXX-XXXX-a9b8d3b2ae2e"

creator != "99:27935d01-XXXX-XXXX-XXXX-a9b8d3b2ae2e"

creator = currentUser() and mention != currentUser()

Note: You do not need to escape these quotes in your queries for things like this.
created > now("-4w")

created > startOfMonth() and type = attachment

created >= "2008/12/31"

lastModified < startOfYear() and type = page

created >= startOfWeek("-1w") and type = blogpost

mention in ("99:27935d01-XXXX-XXXX-XXXX-a9b8d3b2ae2e", "48293:5s04-XXXX-XXXX-XXXX-d7a9b9d8c9f01", "2223:48d-3a-XXXX-XXXX-XXXX-8d9dd0e98as7")

creator in ("99:27935d01-XXXX-XXXX-XXXX-a9b8d3b2ae2e", "48293:5s04-XXXX-XXXX-XXXX-d7a9b9d8c9f01") or contributor in ("99:27935d01-XXXX-XXXX-XXXX-a9b8d3b2ae2e", "48293:5s04-XXXX-XXXX-XXXX-d7a9b9d8c9f01")

creator not in ("99:27935d01-XXXX-XXXX-XXXX-a9b8d3b2ae2e", "48293:5s04-XXXX-XXXX-XXXX-d7a9b9d8c9f01", "2223:48d-3a-XXXX-XXXX-XXXX-8d9dd0e98as7")

creator.fullname ~ "alana"

title ~ win

title ~ "win*"

text ~ "advanced search"

title !~ run

Find content in the DEV space ordered by creation date.
order by created

Find content in the DEV space ordered by creation date with the newest first, then title.
order by created desc, title

Find pages created by jsmith ordered by created, then title.
creator = jsmith order by created, title asc

Find all content created in the last 4 weeks. (Note: the quotes don't need escaping)
created > now("-4w")

Find all content created on or after 31/12/2008.
created >= "2008/12/31"

Find all pages lastModified before the start of the year.
lastModified < startOfYear()
"""
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="confluence_get_page",
            description="Get content of a specific Confluence page by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Confluence page ID"},
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Whether to include page metadata",
                        "default": True,
                    },
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="confluence_get_comments",
            description="Get comments for a specific Confluence page",
            inputSchema={
                "type": "object",
                "properties": {"page_id": {"type": "string", "description": "Confluence page ID"}},
                "required": ["page_id"],
            },
        ),
        Tool(
            name="jira_get_issue",
            description="Get details of a specific Jira issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string", "description": "Jira issue key (e.g., 'PROJ-123')"},
                    "expand": {"type": "string", "description": "Optional fields to expand", "default": None},
                },
                "required": ["issue_key"],
            },
        ),
        Tool(
            name="jira_search",
            description="Search Jira issues using JQL",
            inputSchema={
                "type": "object",
                "properties": {
                    "jql": {"type": "string", "description": "JQL query string"},
                    "fields": {"type": "string", "description": "Comma-separated fields to return", "default": "*all"},
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["jql"],
            },
        ),
        Tool(
            name="jira_get_project_issues",
            description="Get all issues for a specific Jira project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_key": {"type": "string", "description": "The project key"},
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["project_key"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool calls for Confluence and Jira operations."""
    try:
        logger.debug("Executing tool '%s' with arguments: %s", name, arguments)
        
        if name == "confluence_search":
            limit = min(int(arguments.get("limit", 10)), 50)
            logger.debug("Searching Confluence with query: %s (limit: %d)", arguments["query"], limit)
            documents = confluence_fetcher.search(arguments["query"], limit)
            search_results = [
                {
                    "page_id": doc.metadata["page_id"],
                    "title": doc.metadata["title"],
                    "space": doc.metadata["space"],
                    "url": doc.metadata["url"],
                    "last_modified": doc.metadata["last_modified"],
                    "type": doc.metadata["type"],
                    "excerpt": doc.page_content,
                }
                for doc in documents
            ]
            logger.debug("Found %d Confluence search results", len(search_results))
            return [TextContent(type="text", text=json.dumps(search_results, indent=2))]

        elif name == "confluence_get_page":
            logger.debug("Fetching Confluence page: %s", arguments["page_id"])
            doc = confluence_fetcher.get_page_content(arguments["page_id"])
            include_metadata = arguments.get("include_metadata", True)

            if include_metadata:
                result = {"content": doc.page_content, "metadata": doc.metadata}
            else:
                result = {"content": doc.page_content}

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "confluence_get_comments":
            logger.debug("Fetching comments for page: %s", arguments["page_id"])
            comments = confluence_fetcher.get_page_comments(arguments["page_id"])
            formatted_comments = [
                {
                    "author": comment.metadata["author_name"],
                    "created": comment.metadata["last_modified"],
                    "content": comment.page_content,
                }
                for comment in comments
            ]
            logger.debug("Found %d comments", len(formatted_comments))
            return [TextContent(type="text", text=json.dumps(formatted_comments, indent=2))]

        elif name == "jira_get_issue":
            logger.debug("Fetching Jira issue: %s", arguments["issue_key"])
            doc = jira_fetcher.get_issue(arguments["issue_key"], expand=arguments.get("expand"))
            result = {"content": doc.page_content, "metadata": doc.metadata}
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "jira_search":
            limit = min(int(arguments.get("limit", 10)), 50)
            logger.debug("Searching Jira with JQL: %s (limit: %d)", arguments["jql"], limit)
            documents = jira_fetcher.search_issues(
                arguments["jql"], fields=arguments.get("fields", "*all"), limit=limit
            )
            search_results = [
                {
                    "key": doc.metadata["key"],
                    "title": doc.metadata["title"],
                    "type": doc.metadata["type"],
                    "status": doc.metadata["status"],
                    "created_date": doc.metadata["created_date"],
                    "priority": doc.metadata["priority"],
                    "link": doc.metadata["link"],
                    "excerpt": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                }
                for doc in documents
            ]
            logger.debug("Found %d Jira search results", len(search_results))
            return [TextContent(type="text", text=json.dumps(search_results, indent=2))]

        elif name == "jira_get_project_issues":
            limit = min(int(arguments.get("limit", 10)), 50)
            logger.debug("Fetching issues for project: %s (limit: %d)", arguments["project_key"], limit)
            documents = jira_fetcher.get_project_issues(arguments["project_key"], limit=limit)
            project_issues = [
                {
                    "key": doc.metadata["key"],
                    "title": doc.metadata["title"],
                    "type": doc.metadata["type"],
                    "status": doc.metadata["status"],
                    "created_date": doc.metadata["created_date"],
                    "link": doc.metadata["link"],
                }
                for doc in documents
            ]
            logger.debug("Found %d project issues", len(project_issues))
            return [TextContent(type="text", text=json.dumps(project_issues, indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        if hasattr(e, 'response'):
            logger.error(
                "Tool execution error: HTTP %s - %s (%s)", 
                e.response.status_code if hasattr(e, 'response') else 'Unknown',
                str(e) or "No error message", 
                type(e).__name__
            )
            logger.debug("Response content: %s", e.response.text if hasattr(e, 'response') else 'No response content')
        else:
            logger.error("Tool execution error: %s (%s)", str(e) or "No error message", type(e).__name__)
        logger.debug("Exception details:", exc_info=True)
        raise RuntimeError(f"Tool execution failed: {str(e)}")
