# Microsoft Entra MCP Server

A FastMCP server that provides AI assistants with access to Microsoft Entra (Azure AD) directory services. This server enables LLMs to search for users, groups, and check memberships using the Microsoft Graph API.

## Features

- 🔍 **4 Tools**: Search users, search groups, get user membership, get group members
- 🧠 **Full-text Search**: Uses Microsoft Graph `$search` with AND tokenization for order-agnostic matches (e.g., "Arun AND Singh" matches "Singh, Arun" and "Arun Kumar Singh")
- 📈 **Accurate Counts**: Uses `ConsistencyLevel: eventual` with `$count=true` and pagination across `@odata.nextLink`
- 🔁 **Pagination**: Users, groups, and group members are paginated to return complete results up to limits
- 🆔 **Robust Identifier Resolution**: Membership lookup resolves user ID from email/UPN before querying
- 🎨 **7 Prompts**: Pre-built prompt templates for common Entra queries
- 🔐 **Secure Authentication**: Uses Azure AD app registration with client credentials
- 🌐 **Health Endpoint**: Built-in health check for monitoring
- ✅ **Fully Tested**: Comprehensive test suite with pytest

## Prerequisites

### Azure AD App Registration

1. Go to Azure Portal → Microsoft Entra ID → App registrations
2. Create a new app registration
3. Note down:
   - Application (client) ID
   - Directory (tenant) ID
4. Create a client secret under Certificates & secrets
5. Grant the following Microsoft Graph API permissions:
   - `User.Read.All`
   - `Group.Read.All`
   - `GroupMember.Read.All`

### Environment Variables

Set these environment variables before running. You can either:

**Option 1: Direct environment variables**
```bash
export ENTRA_TENANT_ID="your-tenant-id-here"
export ENTRA_CLIENT_ID="your-client-id-here"
export ENTRA_CLIENT_SECRET="your-client-secret-here"
```

**Option 2: Use .env file**
```bash
cp env.template .env
# Edit .env with your actual values
```

The server will automatically load variables from a `.env` file if it exists.

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Running Locally

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ENTRA_TENANT_ID="..."
export ENTRA_CLIENT_ID="..."
export ENTRA_CLIENT_SECRET="..."

# Run the server
python main.py
```

Server will start on `http://0.0.0.0:8001`

### Using Docker

```bash
# Build the image
docker build -t entra-mcp .

# Run the container with environment variables
docker run -p 8001:8001 \
  -e ENTRA_TENANT_ID="..." \
  -e ENTRA_CLIENT_ID="..." \
  -e ENTRA_CLIENT_SECRET="..." \
  entra-mcp
```

## API Reference

### Tools

#### 1. `search_entra_users`

Search for users by display name, email, or user principal name.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search term for user name, email, or UPN (full-text `$search` with AND-tokenized terms) |
| `max_results` | integer | No | 10 | Maximum number of results to return |

**Search Behavior:**
- Full-text across `displayName`, `mail`, and `userPrincipalName` using Graph `$search`
- Tokens are ANDed for better relevance (e.g., "Arun Singh" → `"Arun" AND "Singh"`), matching order-agnostic names and middle names
- Uses `ConsistencyLevel: eventual` and `$count=true` for accurate totals
- Paginates across `@odata.nextLink` and returns up to `max_results`

**Example Usage:**

```python
# Order-agnostic and middle-name tolerant
search_entra_users(query="Arun Singh", max_results=25)

# Also matches comma-separated and compound names
search_entra_users(query="Singh, Arun", max_results=25)

# Email or UPN fragments are also matched by `$search`
search_entra_users(query="arun.singh@company.com")
```

#### 2. `search_entra_groups`

Search for groups by display name or description.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search term for group name or description (full-text `$search` with AND-tokenized terms) |
| `max_results` | integer | No | 10 | Maximum number of results to return |

**Search Behavior:**
- Full-text across `displayName` and `description` with Graph `$search` and AND-tokenized terms
- Uses `ConsistencyLevel: eventual` and `$count=true` for accurate totals
- Paginates across `@odata.nextLink` and returns up to `max_results`

#### 3. `get_user_group_membership`

Get all groups a user belongs to.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_identifier` | string | Yes | - | User ID, UPN, or email address |

**Behavior:**
- Resolves the user ID from email/UPN automatically when needed
- Uses `ConsistencyLevel: eventual`, `$count=true`, and paginates across `@odata.nextLink`

#### 4. `get_group_members`

Get all members of a group.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `group_identifier` | string | Yes | - | Group ID or display name |
| `max_results` | integer | No | 50 | Maximum number of members to return |

**Behavior:**
- Uses `ConsistencyLevel: eventual` and paginates across `@odata.nextLink`
- Returns up to `max_results` members

## Available Prompts

### 1. `find_user_by_name`
Find a user by their display name.

Default now suggests a broader search and higher limit to take advantage of `$search`:

```python
# Suggests: Call search_entra_users with: query='{name}', max_results=25
```

### 2. `find_user_by_email`
Find a user by their email address.

### 3. `find_group_by_name`
Find a group by name.

### 4. `check_user_groups`
Check what groups a user belongs to.

### 5. `list_group_members`
List all members of a specific group.

### 6. `user_access_audit`
Perform an access audit for a user.

### 7. `group_membership_audit`
Audit the membership of a security-sensitive group.

## Testing

### Health Check

```bash
curl http://localhost:8001/health
```

### Run Test Suite

```bash
# Run all tests
python -m pytest tests/ -v
```

## Project Structure

```
streamable-HTTP-Entra-MCP/
├── main.py              # Main server with tools and authentication
├── promptz.py           # Prompt templates for LLMs (7 prompts)
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── tests/
    ├── __init__.py
    └── test_main.py    # Tests for main functionality
```

## Security Notes

- The server requires Azure AD application permissions to read user and group data
- All API calls are authenticated using client credentials flow
- No user data is stored locally - all queries go directly to Microsoft Graph API
- Ensure your Azure AD app has minimal required permissions

### Graph Query Semantics Used
- `ConsistencyLevel: eventual` is required for `$search` and `$count`
- `$search` values are AND-tokenized to improve relevance and handle name order variations
- `$count=true` is requested to return accurate totals
- Results are paginated via `@odata.nextLink` until limits are reached

## Use Cases

- 🔍 **User Lookup**: Find user information by name or email
- 👥 **Group Discovery**: Search for available groups
- 🔐 **Access Control**: Check user group memberships for permissions
- 📊 **Audit & Compliance**: Review group memberships and user access
- 🤖 **AI Assistants**: Enable LLMs to answer questions about Entra directory

## Dependencies

**Core:**
- `fastmcp==2.13.0.1` - FastMCP framework for MCP server
- `httpx==0.28.1` - Async HTTP client
- `azure-identity==1.19.0` - Azure authentication
- `msal==1.31.0` - Microsoft Authentication Library

**Development:**
- `pytest==8.3.4` - Testing framework
- `pytest-asyncio==0.24.0` - Async test support

## API Data Source

This server uses the Microsoft Graph API:
- **Base URL**: `https://graph.microsoft.com/v1.0`
- **Authentication**: Client Credentials Flow
- **Scopes**: `https://graph.microsoft.com/.default`

## Troubleshooting

### Authentication Errors
```bash
# Check environment variables are set
echo $ENTRA_TENANT_ID $ENTRA_CLIENT_ID $ENTRA_CLIENT_SECRET

# Verify Azure AD app permissions in Azure Portal
# Ensure client secret is not expired
```

### Import Errors
```bash
# Install dependencies
pip install -r requirements.txt

# Verify Azure packages
pip list | grep azure
```

## License

See [LICENSE](../LICENSE) file for details.

---

**Built with ❤️ using FastMCP and Microsoft Graph API**