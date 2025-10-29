"""
Tests for Microsoft Entra MCP Server
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from main import EntraClient, get_entra_client


class TestEntraClient:
    """Test the EntraClient class"""

    @pytest.fixture
    def mock_env(self):
        """Set up mock environment variables"""
        with patch.dict(os.environ, {
            'ENTRA_TENANT_ID': 'test-tenant-id',
            'ENTRA_CLIENT_ID': 'test-client-id',
            'ENTRA_CLIENT_SECRET': 'test-client-secret'
        }):
            yield

    @pytest.fixture
    def mock_credential(self):
        """Mock Azure credential"""
        with patch('main.ClientSecretCredential') as mock_cred:
            mock_instance = MagicMock()
            mock_instance.get_token.return_value = MagicMock(token='mock-token')
            mock_cred.return_value = mock_instance
            yield mock_cred

    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx client"""
        with patch('main.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"value": []}
            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance
            yield mock_client

    def test_init_missing_env_vars(self):
        """Test initialization fails with missing environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required environment variables"):
                EntraClient()

    def test_init_success(self, mock_env, mock_credential):
        """Test successful initialization"""
        client = EntraClient()
        assert client.tenant_id == 'test-tenant-id'
        assert client.client_id == 'test-client-id'
        assert client.client_secret == 'test-client-secret'

    @pytest.mark.asyncio
    async def test_search_users(self, mock_env, mock_credential, mock_httpx):
        """Test user search functionality"""
        client = EntraClient()
        mock_httpx.return_value.get.return_value.json.return_value = {
            "value": [
                {
                    "id": "user1",
                    "displayName": "John Doe",
                    "userPrincipalName": "john.doe@company.com",
                    "mail": "john.doe@company.com"
                }
            ]
        }

        results = await client.search_users("John", 5)
        assert len(results) == 1
        assert results[0]["displayName"] == "John Doe"

    @pytest.mark.asyncio
    async def test_search_groups(self, mock_env, mock_credential, mock_httpx):
        """Test group search functionality"""
        client = EntraClient()
        mock_httpx.return_value.get.return_value.json.return_value = {
            "value": [
                {
                    "id": "group1",
                    "displayName": "Developers",
                    "description": "Development team"
                }
            ]
        }

        results = await client.search_groups("Dev", 5)
        assert len(results) == 1
        assert results[0]["displayName"] == "Developers"

    @pytest.mark.asyncio
    async def test_get_user_membership(self, mock_env, mock_credential, mock_httpx):
        """Test getting user group membership"""
        client = EntraClient()
        mock_httpx.return_value.get.return_value.json.return_value = {
            "value": [
                {
                    "id": "group1",
                    "displayName": "Developers"
                }
            ]
        }

        results = await client.get_user_membership("user1")
        assert len(results) == 1
        assert results[0]["displayName"] == "Developers"

    @pytest.mark.asyncio
    async def test_get_group_members(self, mock_env, mock_credential, mock_httpx):
        """Test getting group members"""
        client = EntraClient()
        mock_httpx.return_value.get.return_value.json.return_value = {
            "value": [
                {
                    "id": "user1",
                    "displayName": "John Doe",
                    "userPrincipalName": "john.doe@company.com"
                }
            ]
        }

        results = await client.get_group_members("group1", 10)
        assert len(results) == 1
        assert results[0]["displayName"] == "John Doe"


def test_get_entra_client():
    """Test get_entra_client function"""
    # Reset global client
    import main
    main.entra_client = None

    with patch.dict(os.environ, {
        'ENTRA_TENANT_ID': 'test-tenant-id',
        'ENTRA_CLIENT_ID': 'test-client-id',
        'ENTRA_CLIENT_SECRET': 'test-client-secret'
    }):
        with patch('main.ClientSecretCredential'):
            client1 = get_entra_client()
            client2 = get_entra_client()
            assert client1 is client2  # Should return same instance