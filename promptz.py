"""
Prompts for Microsoft Entra MCP Server
"""

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP):
    """Register all prompts with the MCP server"""

    @mcp.prompt
    def find_user_by_name(name: str) -> str:
        """
        Find a user by their display name in Microsoft Entra.

        Use this for questions like:
        - "Who is John Doe?"
        - "Find user named Sarah Johnson"
        - "Look up employee Michael Chen"
        - Order-agnostic names like "Singh, Arun"
        - Compound names like "Arun Kumar Singh"

        Args:
            name: The display name or partial name to search for
        """
        return f"Call search_entra_users with: query='{name}', max_results=25"

    @mcp.prompt
    def find_user_by_email(email: str) -> str:
        """
        Find a user by their email address in Microsoft Entra.

        Use this for questions like:
        - "What's john.doe@company.com's info?"
        - "Find user with email sarah@company.com"
        - "Look up user by email address"

        Args:
            email: The email address to search for
        """
        return f"Call search_entra_users with: query='{email}', max_results=1"

    @mcp.prompt
    def find_group_by_name(name: str) -> str:
        """
        Find a group by name in Microsoft Entra.

        Use this for questions like:
        - "Find the Developers group"
        - "Look up Security Admins"
        - "Search for Marketing team group"

        Args:
            name: The group name or partial name to search for
        """
        return f"Call search_entra_groups with: query='{name}', max_results=5"

    @mcp.prompt
    def check_user_groups(user_identifier: str) -> str:
        """
        Check what groups a user belongs to in Microsoft Entra.

        Use this for questions like:
        - "What groups is John Doe in?"
        - "Check membership for sarah@company.com"
        - "What teams does Michael belong to?"
        - "Show me the groups for user ID xyz"

        Args:
            user_identifier: User name, email, or ID to check membership for
        """
        return f"Call get_user_group_membership with: user_identifier='{user_identifier}'"

    @mcp.prompt
    def list_group_members(group_name: str) -> str:
        """
        List all members of a specific group in Microsoft Entra.

        Use this for questions like:
        - "Who is in the Developers group?"
        - "List members of Security Admins"
        - "Show me who's in the Marketing team"
        - "Get users in group ID xyz"

        Args:
            group_name: The group name or ID to list members for
        """
        return f"Call get_group_members with: group_identifier='{group_name}', max_results=50"

    @mcp.prompt
    def user_access_audit(user_identifier: str) -> str:
        """
        Perform an access audit for a user by checking their group memberships.

        Use this for security and compliance questions like:
        - "What access does John Doe have?"
        - "Audit permissions for sarah@company.com"
        - "Check security groups for Michael"
        - "Review user access rights"

        Args:
            user_identifier: User name, email, or ID to audit
        """
        return f"Call get_user_group_membership with: user_identifier='{user_identifier}'"

    @mcp.prompt
    def group_membership_audit(group_name: str) -> str:
        """
        Audit the membership of a security-sensitive group.

        Use this for compliance and security reviews:
        - "Audit who has admin access"
        - "Check who's in the Security group"
        - "Review privileged group members"
        - "List users with elevated permissions"

        Args:
            group_name: The group name or ID to audit
        """
        return f"Call get_group_members with: group_identifier='{group_name}', max_results=100"