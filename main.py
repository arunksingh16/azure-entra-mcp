#!/usr/bin/env python3

import httpx
import json
import os
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from fastapi.responses import JSONResponse
from azure.identity import ClientSecretCredential
from promptz import register_prompts
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

mcp = FastMCP("Microsoft Entra MCP Server")


# Access the underlying FastAPI app to add health endpoint
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse(
        {"status": "healthy", "service": "microsoft-entra-mcp-server"}
    )


class EntraClient:
    """Microsoft Graph API client for Entra operations"""

    def __init__(self):
        self.tenant_id = os.getenv("ENTRA_TENANT_ID")
        self.client_id = os.getenv("ENTRA_CLIENT_ID")
        self.client_secret = os.getenv("ENTRA_CLIENT_SECRET")

        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Missing required environment variables: ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET")

        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.base_url = "https://graph.microsoft.com/v1.0"
        self._token = None

    async def _get_token(self) -> str:
        """Get access token for Microsoft Graph API"""
        if not self._token:
            self._token = self.credential.get_token("https://graph.microsoft.com/.default").token
        return self._token

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make authenticated request to Microsoft Graph API"""
        token = await self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        if extra_headers:
            headers.update(extra_headers)

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    async def _get_next_link(self, next_link_url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Follow a Microsoft Graph @odata.nextLink URL with provided headers."""
        async with httpx.AsyncClient() as client:
            response = await client.get(next_link_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def _collect_paged(self, endpoint: str, params: Dict[str, Any], extra_headers: Dict[str, str], item_limit: Optional[int]) -> Dict[str, Any]:
        """Collect paginated Graph results until item_limit or the end.

        Returns a dict containing keys: value (list), count (Optional[int]).
        """
        first_page = await self._make_request(endpoint, params, extra_headers=extra_headers)
        items = list(first_page.get("value", []))
        total_count = first_page.get("@odata.count")
        next_link = first_page.get("@odata.nextLink")

        # If a limit is provided, stop when we have enough items
        while next_link and (item_limit is None or len(items) < item_limit):
            page = await self._get_next_link(next_link, {**extra_headers, "Authorization": f"Bearer {(await self._get_token())}", "Content-Type": "application/json"})
            page_items = page.get("value", [])
            items.extend(page_items)
            next_link = page.get("@odata.nextLink")

        if item_limit is not None and len(items) > item_limit:
            items = items[:item_limit]

        return {"value": items, "count": total_count}

    def _build_and_search_query(self, raw_query: str) -> str:
        """Build an AND-tokenized Microsoft Graph $search value from input."""
        tokens = [t.strip() for t in raw_query.split() if t.strip()]
        if not tokens:
            return f'"{raw_query.strip()}"'
        quoted = [f'"{t.replace("\"", "\\\"")}"' for t in tokens]
        return " AND ".join(quoted)

    async def search_users(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for users by display name, email, or user principal name.

        Returns a dict with keys: users (list) and total_count (int).
        """
        # Sanitize query to prevent injection
        sanitized_query = query.replace("'", "''").strip()

        # Try Graph $search first (full-text across relevant fields)
        search_headers = {"ConsistencyLevel": "eventual"}
        search_params = {
            "$search": self._build_and_search_query(sanitized_query),
            "$count": "true",
            "$top": limit,
            "$select": "id,displayName,userPrincipalName,mail,jobTitle,department,officeLocation"
        }
        try:
            page = await self._collect_paged("/users", search_params, search_headers, limit)
            users = page.get("value", [])
            total_count = page.get("count", len(users))
            return {"users": users, "total_count": total_count}
        except Exception:
            # Fall back to $filter with startswith if $search is not available
            pass

        # Fallback using $filter (prefix search on common properties) with count
        filter_params = {
            "$filter": f"startswith(displayName,'{sanitized_query}') or startswith(mail,'{sanitized_query}') or startswith(userPrincipalName,'{sanitized_query}')",
            "$count": "true",
            "$top": limit,
            "$select": "id,displayName,userPrincipalName,mail,jobTitle,department,officeLocation"
        }
        page = await self._collect_paged("/users", filter_params, search_headers, limit)
        users = page.get("value", [])
        total_count = page.get("count", len(users))
        return {"users": users, "total_count": total_count}

    async def search_groups(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for groups by display name or description.

        Returns a dict with keys: groups (list) and total_count (int).
        """
        # Sanitize query to prevent injection
        sanitized_query = query.replace("'", "''").strip()

        # Prefer Graph $search for full-text
        search_headers = {"ConsistencyLevel": "eventual"}
        search_params = {
            "$search": self._build_and_search_query(sanitized_query),
            "$count": "true",
            "$top": limit,
            "$select": "id,displayName,description,groupTypes,mail"
        }
        try:
            page = await self._collect_paged("/groups", search_params, search_headers, limit)
            groups = page.get("value", [])
            total_count = page.get("count", len(groups))
            return {"groups": groups, "total_count": total_count}
        except Exception:
            # Fallback to $filter with startswith
            pass

        filter_params = {
            "$filter": f"startswith(displayName,'{sanitized_query}') or startswith(description,'{sanitized_query}')",
            "$count": "true",
            "$top": limit,
            "$select": "id,displayName,description,groupTypes,mail"
        }
        page = await self._collect_paged("/groups", filter_params, search_headers, limit)
        groups = page.get("value", [])
        total_count = page.get("count", len(groups))
        return {"groups": groups, "total_count": total_count}

    async def _resolve_user_id(self, identifier: str) -> Optional[str]:
        """Resolve a user ID from a provided identifier (id, UPN, or mail)."""
        # Try direct GET using identifier (id or UPN)
        try:
            _ = await self._make_request(f"/users/{identifier}")
            return identifier
        except Exception:
            pass

        # If identifier looks like an email, try filter by mail
        try:
            params = {"$filter": f"mail eq '{identifier}'", "$select": "id"}
            res = await self._make_request("/users", params)
            users = res.get("value", [])
            if users:
                return users[0].get("id")
        except Exception:
            pass
        return None

    async def get_user_membership(self, user_identifier: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all groups a user is a member of, resolving identifier if needed."""
        resolved = await self._resolve_user_id(user_identifier)
        user_id = resolved or user_identifier
        endpoint = f"/users/{user_id}/memberOf"
        params = {
            "$select": "id,displayName,description,groupTypes,mail",
            "$count": "true",
            "$top": 50
        }
        headers = {"ConsistencyLevel": "eventual"}
        page = await self._collect_paged(endpoint, params, headers, limit)
        return page.get("value", [])

    async def get_group_members(self, group_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get members of a group"""
        endpoint = f"/groups/{group_id}/members"
        params = {
            "$top": limit,
            "$select": "id,displayName,userPrincipalName,mail,jobTitle,department"
        }
        response = await self._make_request(endpoint, params)
        return response.get("value", [])


# Global client instance
entra_client = None

def get_entra_client() -> EntraClient:
    """Get or create Entra client instance"""
    global entra_client
    if entra_client is None:
        entra_client = EntraClient()
    return entra_client


@mcp.tool(
    description="""
        Search for users in Microsoft Entra (Azure AD) by name, email, or user principal name.

        This tool allows you to find users based on their display name, email address, or UPN.
        Returns basic user information including name, email, job title, and department.

        Examples:
        - To find a user named "John Doe": use query="John Doe"
        - To find users with email containing "john": use query="john"
        - To find a specific user by UPN: use query="john.doe@company.com"

        Use this tool when:
        1. You need to find a specific user by name or email
        2. You want to search for users with similar names
        3. You need user contact information or basic profile details
        """
)
async def search_entra_users(
    query: str,
    max_results: int = 10
) -> str:
    """
    Search for users in Microsoft Entra.

    Args:
        query: Search term for user display name, email, or UPN
        max_results: Maximum number of results to return (default: 10)

    Returns:
        JSON string containing the user search results
    """
    try:
        client = get_entra_client()
        search_result = await client.search_users(query, max_results)
        users = search_result.get("users", [])
        total_count = search_result.get("total_count", len(users))

        result = {
            "query": query,
            "total_results": int(total_count),
            "users": users
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error searching users: {str(e)}"


@mcp.tool(
    description="""
        Search for groups in Microsoft Entra (Azure AD) by name or description.

        This tool allows you to find security groups, distribution groups, or Microsoft 365 groups
        based on their display name or description.

        Examples:
        - To find groups containing "admin": use query="admin"
        - To find a specific group: use query="Developers Team"
        - To find groups related to security: use query="security"

        Use this tool when:
        1. You need to find a specific group by name
        2. You want to discover available groups for user assignment
        3. You need to check group properties or email addresses
        """
)
async def search_entra_groups(
    query: str,
    max_results: int = 10
) -> str:
    """
    Search for groups in Microsoft Entra.

    Args:
        query: Search term for group display name or description
        max_results: Maximum number of results to return (default: 10)

    Returns:
        JSON string containing the group search results
    """
    try:
        client = get_entra_client()
        search_result = await client.search_groups(query, max_results)
        groups = search_result.get("groups", [])
        total_count = search_result.get("total_count", len(groups))

        result = {
            "query": query,
            "total_results": int(total_count),
            "groups": groups
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error searching groups: {str(e)}"


@mcp.tool(
    description="""
        Get all groups that a specific user is a member of in Microsoft Entra (Azure AD).

        This tool shows the group membership for a user, including security groups,
        distribution groups, and Microsoft 365 groups they belong to.

        You can provide either the user's ID, user principal name, or email address.

        Examples:
        - To check membership for user ID: use user_identifier="user-id-here"
        - To check membership for UPN: use user_identifier="john.doe@company.com"
        - To check membership for email: use user_identifier="john.doe@company.com"

        Use this tool when:
        1. You need to see what groups a user belongs to
        2. You want to check user permissions through group membership
        3. You need to verify group assignments for access control
        """
)
async def get_user_group_membership(
    user_identifier: str
) -> str:
    """
    Get group membership for a user in Microsoft Entra.

    Args:
        user_identifier: User ID, user principal name, or email address

    Returns:
        JSON string containing the user's group memberships
    """
    try:
        client = get_entra_client()
        membership = await client.get_user_membership(user_identifier)

        result = {
            "user_identifier": user_identifier,
            "total_groups": len(membership),
            "groups": membership
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting user membership: {str(e)}"


@mcp.tool(
    description="""
        Get all members of a specific group in Microsoft Entra (Azure AD).

        This tool shows all users who are members of a particular group,
        including their basic profile information.

        You can provide either the group's ID or display name.

        Examples:
        - To get members of group ID: use group_identifier="group-id-here"
        - To get members of a group by name: use group_identifier="Developers Team"

        Use this tool when:
        1. You need to see who belongs to a specific group
        2. You want to audit group membership
        3. You need to check user assignments for a particular group
        """
)
async def get_group_members(
    group_identifier: str,
    max_results: int = 50
) -> str:
    """
    Get members of a group in Microsoft Entra.

    Args:
        group_identifier: Group ID or display name
        max_results: Maximum number of members to return (default: 50)

    Returns:
        JSON string containing the group members
    """
    try:
        client = get_entra_client()
        members = await client.get_group_members(group_identifier, max_results)

        result = {
            "group_identifier": group_identifier,
            "total_members": len(members),
            "members": members
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting group members: {str(e)}"


# Register prompts
register_prompts(mcp)

if __name__ == "__main__":
    mcp.run(transport="http", port=8001, host="0.0.0.0")
