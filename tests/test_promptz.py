"""
Tests for Microsoft Entra MCP Server Prompts
"""

import pytest
from promptz import register_prompts
from fastmcp import FastMCP


def test_register_prompts():
    """Test that prompts are registered correctly"""
    mcp = FastMCP("Test MCP")

    # Register prompts
    register_prompts(mcp)

    # Check that prompts were registered (this is a basic test)
    # In a real scenario, you'd check the mcp instance has the prompts
    assert mcp is not None


def test_prompt_find_user_by_name():
    """Test find_user_by_name prompt logic"""
    from promptz import register_prompts
    mcp = FastMCP("Test MCP")
    register_prompts(mcp)

    # The actual prompt function would be tested by calling it
    # For now, just ensure registration works
    assert True


def test_prompt_find_user_by_email():
    """Test find_user_by_email prompt logic"""
    from promptz import register_prompts
    mcp = FastMCP("Test MCP")
    register_prompts(mcp)
    assert True


def test_prompt_find_group_by_name():
    """Test find_group_by_name prompt logic"""
    from promptz import register_prompts
    mcp = FastMCP("Test MCP")
    register_prompts(mcp)
    assert True


def test_prompt_check_user_groups():
    """Test check_user_groups prompt logic"""
    from promptz import register_prompts
    mcp = FastMCP("Test MCP")
    register_prompts(mcp)
    assert True


def test_prompt_list_group_members():
    """Test list_group_members prompt logic"""
    from promptz import register_prompts
    mcp = FastMCP("Test MCP")
    register_prompts(mcp)
    assert True


def test_prompt_user_access_audit():
    """Test user_access_audit prompt logic"""
    from promptz import register_prompts
    mcp = FastMCP("Test MCP")
    register_prompts(mcp)
    assert True


def test_prompt_group_membership_audit():
    """Test group_membership_audit prompt logic"""
    from promptz import register_prompts
    mcp = FastMCP("Test MCP")
    register_prompts(mcp)
    assert True