# Yasmine's Local AI Setup Guide

This document provides a comprehensive guide to your local AI setup, including all services, configurations, and environment variables.

## Services Overview

### 1. Open WebUI
- **URL**: http://localhost:3000
- **Purpose**: Web interface for interacting with Ollama models
- **Features**: Chat interface, model management, conversation history

### 2. N8N
- **URL**: http://localhost:5678
- **Purpose**: Workflow automation platform
- **Features**: Visual workflow editor, automation tasks, API integrations
- **Database Config**:
  - Host: supabase-db
  - User: postgres
  - Database: postgres

### 3. Flowise
- **URL**: http://localhost:3001
- **Purpose**: Low-code UI for building AI applications
- **Features**: Visual flow builder, AI components, chatbot creation

### 4. SearXNG
- **URL**: http://localhost:8080
- **Purpose**: Privacy-focused metasearch engine
- **Configuration**:
  - Workers: 2
  - Threads: 4

### 5. Supabase
- **API URL**: http://localhost:8000
- **Studio URL**: http://localhost:8000/studio
- **Purpose**: Open source Firebase alternative
- **Components**:
  - PostgreSQL Database
  - Authentication
  - Real-time subscriptions
  - Storage
  - Edge Functions

### 6. Qdrant
- **Purpose**: Vector database for AI applications
- **Features**: Vector similarity search, collections management

### 7. Ollama
- **URL**: host.docker.internal:11434
- **Purpose**: Local model serving
- **Current Model**: Mistral

### 8. MinIO
- **API URL**: http://localhost:9000
- **Console URL**: http://localhost:9001
- **Purpose**: S3-compatible object storage
- **Features**: Buckets, file storage, versioning, access control
- **Default Credentials**:
  - Username: minioadmin
  - Password: minioadmin
- **Environment Variables**:
  - MINIO_ROOT_USER: Username for MinIO admin
  - MINIO_ROOT_PASSWORD: Password for MinIO admin
  - MINIO_HOSTNAME: Hostname for Caddy proxy
- **Integration**:
  - S3 API Endpoint: http://minio:9000
  - For services within Docker network: Use service name "minio" as hostname
  - For external access: Use localhost:9000 or the Caddy proxy

### 9. Archon
- **Streamlit UI**: http://localhost:8501
- **Graph Service**: http://localhost:8100
- **MCP Server**: http://localhost:8200
- **Purpose**: AI agent builder for creating autonomous AI agents
- **Features**: 
  - Build, refine, and optimize AI agents
  - Prebuilt tools and examples
  - MCP server integration for AI IDEs
- **Integration**:
  - Uses Ollama for local LLMs
  - Can connect to OpenAI/Anthropic/OpenRouter
  - Supabase for vector database
  - Docker-based deployment

## Environment Configuration

### Core Settings
```env
COMPOSE_PROJECT_NAME=yasmines-local-ai
DOCKER_SOCKET_LOCATION=/var/run/docker.sock
SITE_URL=http://localhost:3000
API_EXTERNAL_URL=http://localhost:8000
```

### Database Configuration
```env
POSTGRES_HOST=localhost
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=[your-password]
```

### Authentication Settings
```env
JWT_SECRET=[your-jwt-secret]
JWT_EXPIRY=3600
ANON_KEY=[your-anon-key]
SERVICE_ROLE_KEY=[your-service-role-key]
```

### Email Configuration
```env
SMTP_PORT=2500
GOTRUE_SMTP_PORT=2500
SMTP_USER=[your-smtp-user]
SMTP_PASS=[your-smtp-pass]
SMTP_SENDER_NAME=[your-sender-name]
```

### Additional Security Settings
```env
SECRET_KEY_BASE=0123456789abcdef0123456789abcdef
VAULT_ENC_KEY=fedcba9876543210fedcba9876543210
```

### Feature Flags
```env
ENABLE_PHONE_SIGNUP=true
ENABLE_PHONE_AUTOCONFIRM=false
ENABLE_ANONYMOUS_USERS=false
IMGPROXY_ENABLE_WEBP_DETECTION=true
```

## Starting the Services

To start all services:

```bash
python3 start_services.py --profile none
```

## Health Checks

You can check the health of all services using:

```bash
docker ps
```

## Service Dependencies

1. Supabase services must start first
2. N8N depends on the Supabase database
3. Open WebUI requires Ollama to be running
4. All web services are proxied through Caddy
5. MinIO can be used by any service requiring object storage
6. Archon depends on Ollama for local LLM access

## Security Notes

1. All sensitive keys and passwords are stored in the .env file
2. JWT tokens expire after 1 hour (3600 seconds)
3. Phone signup is enabled but requires manual confirmation
4. Anonymous users are disabled by default

## Using MinIO with Other Services

### Creating Buckets and Access Keys

1. Access the MinIO Console at http://localhost:9001 (or via Caddy proxy)
2. Log in with the credentials (default: minioadmin/minioadmin)
3. Create a new bucket for your application data
4. Create access keys for services that need to access MinIO:
   - Go to Access Keys in the console
   - Create a new access key and save the credentials securely

### Integration Examples

#### With N8N:
```
- Use the S3 node in N8N workflows
- Endpoint: http://minio:9000
- Access Key: Your created access key
- Secret Key: Your secret key
- Bucket: Your bucket name
```

#### With Flowise:
```
- Use S3 storage components
- Endpoint URL: http://minio:9000
- Region: us-east-1 (default)
- Access Key: Your created access key
- Secret Key: Your secret key
```

#### With Supabase:
```
- For storage buckets, you can use MinIO as an alternative
- Configure storage client to point to MinIO endpoint
```

## Using Archon with Other Services

### Setup and Configuration

1. Access the Archon UI at http://localhost:8501 (or via Caddy proxy)
2. Follow the guided setup process in the Streamlit UI:
   - Configure your API keys and model settings
   - Set up your Supabase vector database
   - Crawl and index documentation
   - Start the agent service

### Integration Examples

#### With Ollama:
```
- Archon is pre-configured to use your local Ollama instance
- Ensure Ollama is running with your preferred models
- The connection is set via OLLAMA_API_BASE=http://host.docker.internal:11434
```

#### With Supabase:
```
- Archon uses Supabase for its vector database
- Configure Supabase connection in the Archon UI
- Uses the same Supabase instance as your other services
```

#### With N8N:
```
- Create workflows that interact with Archon's API
- Trigger agent creation and execution via HTTP requests
- Process and utilize agent outputs in your automation flows
```

### MCP Integration for AI IDEs

Archon includes an MCP (Model Context Protocol) server that allows integration with AI-powered IDEs like:
- Cursor
- Cline
- Roo Code
- Windsurf

To use this feature:
1. Ensure the MCP server is running (port 8200)
2. Configure your IDE to use the Archon MCP endpoint
3. Leverage Archon's agent capabilities directly from your development environment

## Troubleshooting

### Common Issues

1. If n8n-import fails:
   - Check database connectivity
   - Verify database credentials

2. If realtime service shows as unhealthy:
   - This is expected and shouldn't affect functionality
   - Verify REALTIME_JWT_SECRET is set correctly

3. If auth service fails:
   - Check SMTP configuration
   - Verify site URL and external URL settings

### Logs

To view service logs:

```bash
docker logs [container-name]
```

Example:
```bash
docker logs n8n
docker logs supabase-auth
docker logs open-webui
