name: yasmines-local-ai

volumes:
  n8n_storage:
  qdrant_storage:
  open-webui:
  flowise:
  caddy-data:
  caddy-config:
  valkey-data:
  supabase-db-data:
  supabase-storage-data:

networks:
  yasmines-local-ai:
    name: "yasmines-local-ai"

x-n8n: &service-n8n
  image: n8nio/n8n:next
  networks:
    - yasmines-local-ai
  environment:
    - DB_TYPE=postgresdb
    - DB_POSTGRESDB_HOST=supabase-db
    - DB_POSTGRESDB_USER=postgres
    - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
    - DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
    - N8N_DIAGNOSTICS_ENABLED=false
    - N8N_PERSONALIZATION_ENABLED=false
    - N8N_ENCRYPTION_KEY
    - N8N_USER_MANAGEMENT_JWT_SECRET
    - OLLAMA_HOST=host.docker.internal:11434
    - N8N_HOST=localhost
    - N8N_PORT=5678
    - N8N_EDITOR_BASE_URL=http://localhost:5678
    - WEBHOOK_URL=http://localhost:5678
    - TZ=America/New_York
    - GENERIC_TIMEZONE=America/New_York
    - NODE_FUNCTION_ALLOW_BUILTIN=*
    - NODE_FUNCTION_ALLOW_EXTERNAL=*
    - EXECUTIONS_DATA_SAVE_ON_ERROR=all
    - EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
    - EXECUTIONS_DATA_SAVE_ON_PROGRESS=true
    - N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true

services:
  # Local AI services
  flowise:
    image: flowiseai/flowise
    restart: unless-stopped
    container_name: flowise
    networks:
      - yasmines-local-ai
    environment:
      - PORT=3001
    ports:
      - 3001:3001
    extra_hosts:
      - "host.docker.internal:host-gateway"        
    volumes:
      - ~/.flowise:/root/.flowise
    entrypoint: /bin/sh -c "sleep 3; flowise start"

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    restart: unless-stopped
    container_name: open-webui
    networks:
      - yasmines-local-ai
    ports:
      - "3000:8080"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - open-webui:/app/backend/data

  n8n-import:
    <<: *service-n8n
    container_name: n8n-import
    entrypoint: /bin/sh
    command:
      - "-c"
      - "n8n import:credentials --separate --input=/backup/credentials && n8n import:workflow --separate --input=/backup/workflows"
    volumes:
      - ./n8n/backup:/backup  
    depends_on:
      supabase-db:
        condition: service_healthy

  n8n:
    <<: *service-n8n
    container_name: n8n
    restart: always
    ports:
      - 5678:5678
    volumes:
      - n8n_storage:/home/node/.n8n
      - ./n8n/backup:/backup
      - ./shared:/data/shared
    depends_on:
      n8n-import:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5678"]
      interval: 10s
      timeout: 10s
      retries: 5

  qdrant:
    image: qdrant/qdrant
    container_name: qdrant
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    ports:
      - 6333:6333
    volumes:
      - qdrant_storage:/qdrant/storage

  caddy:
    container_name: caddy
    image: docker.io/library/caddy:2-alpine
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data:rw
      - caddy-config:/config:rw
    ports:
      - "80:80"
      - "443:443"
    environment:
      - N8N_HOSTNAME=${N8N_HOSTNAME:-":8001"}
      - WEBUI_HOSTNAME=${WEBUI_HOSTNAME:-":8002"}
      - FLOWISE_HOSTNAME=${FLOWISE_HOSTNAME:-":8003"}
      - OLLAMA_HOSTNAME=${OLLAMA_HOSTNAME:-":8004"}
      - SUPABASE_HOSTNAME=${SUPABASE_HOSTNAME:-":8005"}
      - SEARXNG_HOSTNAME=${SEARXNG_HOSTNAME:-":8006"}
      - LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-internal}
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"

  redis:
    container_name: redis
    image: docker.io/valkey/valkey:8-alpine
    networks:
      - yasmines-local-ai
    command: valkey-server --save 30 1 --loglevel warning
    restart: unless-stopped
    volumes:
      - valkey-data:/data
    cap_drop:
      - ALL
    cap_add:
      - SETGID
      - SETUID
      - DAC_OVERRIDE
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"

  searxng:
    container_name: searxng
    image: docker.io/searxng/searxng:latest
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    ports:
      - 8080:8080
    volumes:
      - ./searxng:/etc/searxng:rw
    environment:
      - SEARXNG_BASE_URL=https://${SEARXNG_HOSTNAME:-localhost}/
      - UWSGI_WORKERS=${SEARXNG_UWSGI_WORKERS:-4}
      - UWSGI_THREADS=${SEARXNG_UWSGI_THREADS:-4}
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"
        
  # Supabase services
  supabase-studio:
    container_name: supabase-studio
    image: supabase/studio:20250317-6955350
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    healthcheck:
      test:
        [
          "CMD",
          "node",
          "-e",
          "fetch('http://supabase-studio:3000/api/platform/profile').then((r) => {if (r.status !== 200) throw new Error(r.status)})"
        ]
      timeout: 10s
      interval: 5s
      retries: 3
    depends_on:
      supabase-analytics:
        condition: service_healthy
    environment:
      STUDIO_PG_META_URL: http://supabase-meta:8080
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

      DEFAULT_ORGANIZATION_NAME: ${STUDIO_DEFAULT_ORGANIZATION:-Default Organization}
      DEFAULT_PROJECT_NAME: ${STUDIO_DEFAULT_PROJECT:-Default Project}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}

      SUPABASE_URL: http://supabase-kong:8000
      SUPABASE_PUBLIC_URL: ${SUPABASE_PUBLIC_URL:-http://localhost:8000}
      SUPABASE_ANON_KEY: ${ANON_KEY}
      SUPABASE_SERVICE_KEY: ${SERVICE_ROLE_KEY}
      AUTH_JWT_SECRET: ${JWT_SECRET}

      LOGFLARE_API_KEY: ${LOGFLARE_API_KEY:-}
      LOGFLARE_URL: http://supabase-analytics:4000
      NEXT_PUBLIC_ENABLE_LOGS: true
      NEXT_ANALYTICS_BACKEND_PROVIDER: postgres

  supabase-kong:
    container_name: supabase-kong
    image: kong:2.8.1
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    ports:
      - ${KONG_HTTP_PORT}:8000/tcp
      - ${KONG_HTTPS_PORT}:8443/tcp
    volumes:
      - ./supabase/docker/volumes/api/kong.yml:/home/kong/kong.yml:ro
    depends_on:
      supabase-analytics:
        condition: service_healthy
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /home/kong/kong.yml
      KONG_DNS_ORDER: LAST,A,CNAME
      KONG_PLUGINS: request-transformer,cors,key-auth,acl,basic-auth
      KONG_NGINX_PROXY_PROXY_BUFFER_SIZE: 160k
      KONG_NGINX_PROXY_PROXY_BUFFERS: 64 160k

  supabase-auth:
    container_name: supabase-auth
    image: supabase/gotrue:v2.170.0
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    healthcheck:
      test:
        [
          "CMD",
          "wget",
          "--no-verbose",
          "--tries=1",
          "--spider",
          "http://localhost:9999/health"
        ]
      timeout: 5s
      interval: 5s
      retries: 3
    depends_on:
      supabase-db:
        condition: service_healthy
      supabase-analytics:
        condition: service_healthy
    environment:
      GOTRUE_API_HOST: 0.0.0.0
      GOTRUE_API_PORT: 9999
      API_EXTERNAL_URL: ${API_EXTERNAL_URL:-}

      GOTRUE_DB_DRIVER: postgres
      GOTRUE_DB_DATABASE_URL: postgres://supabase_auth_admin:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}

      GOTRUE_SITE_URL: ${SITE_URL:-http://localhost:8000}
      GOTRUE_URI_ALLOW_LIST: ${ADDITIONAL_REDIRECT_URLS:-}
      GOTRUE_DISABLE_SIGNUP: ${DISABLE_SIGNUP:-false}
      GOTRUE_JWT_SECRET: ${JWT_SECRET}
      GOTRUE_JWT_EXP: ${JWT_EXPIRY:-3600}
      GOTRUE_JWT_DEFAULT_GROUP_NAME: authenticated
      GOTRUE_DB_AUTOMIGRATE: "true"
      GOTRUE_EXTERNAL_EMAIL_ENABLED: "true"
      GOTRUE_MAILER_AUTOCONFIRM: ${ENABLE_EMAIL_AUTOCONFIRM:-false}
      GOTRUE_SMTP_ADMIN_EMAIL: ${SMTP_ADMIN_EMAIL:-}
      GOTRUE_SMTP_HOST: ${SMTP_HOST:-}
      GOTRUE_SMTP_PORT: ${SMTP_PORT:-}
      GOTRUE_SMTP_USER: ${SMTP_USER:-}
      GOTRUE_SMTP_PASS: ${SMTP_PASS:-}
      GOTRUE_SMTP_SENDER_NAME: ${SMTP_SENDER_NAME:-}
      GOTRUE_MAILER_URLPATHS_CONFIRMATION: ${MAILER_URLPATHS_CONFIRMATION:-/auth/v1/verify}
      GOTRUE_MAILER_URLPATHS_INVITE: ${MAILER_URLPATHS_INVITE:-/auth/v1/verify}
      GOTRUE_MAILER_URLPATHS_RECOVERY: ${MAILER_URLPATHS_RECOVERY:-/auth/v1/verify}
      GOTRUE_MAILER_URLPATHS_EMAIL_CHANGE: ${MAILER_URLPATHS_EMAIL_CHANGE:-/auth/v1/verify}

      GOTRUE_EXTERNAL_PHONE_ENABLED: "true"
      GOTRUE_SMS_AUTOCONFIRM: ${ENABLE_PHONE_AUTOCONFIRM:-}

      # GitHub OAuth
      GOTRUE_EXTERNAL_GITHUB_ENABLED: "false"
      GOTRUE_EXTERNAL_GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID:-}
      GOTRUE_EXTERNAL_GITHUB_SECRET: ${GITHUB_SECRET:-}
      GOTRUE_EXTERNAL_GITHUB_REDIRECT_URI: ${SITE_URL:-http://localhost:8000}/auth/v1/callback
      
      GOTRUE_ENABLE_ANONYMOUS_USERS: ${ENABLE_ANONYMOUS_USERS:-false}
      GOTRUE_RATE_LIMIT_EMAIL_SENT: 6
      GOTRUE_RATE_LIMIT_ANONYMOUS_USERS: 3

      GOTRUE_SECURITY_REFRESH_TOKEN_ROTATION_ENABLED: true
      GOTRUE_MFA_ENABLED: true

      # SMS Provider settings
      GOTRUE_SMS_PROVIDER: "twilio"
      GOTRUE_SMS_TWILIO_ACCOUNT_SID: ${TWILIO_ACCOUNT_SID:-}
      GOTRUE_SMS_TWILIO_AUTH_TOKEN: ${TWILIO_AUTH_TOKEN:-}
      GOTRUE_SMS_TWILIO_MESSAGE_SERVICE_SID: ${TWILIO_MESSAGE_SERVICE_SID:-}
      
      ENABLE_EMAIL_SIGNUP: ${ENABLE_EMAIL_SIGNUP:-true}
      ENABLE_PHONE_SIGNUP: ${ENABLE_PHONE_SIGNUP:-true}
      
  supabase-rest:
    container_name: supabase-rest
    image: postgrest/postgrest:v11.1.0
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    depends_on:
      supabase-db:
        condition: service_healthy
    environment:
      PGRST_DB_URI: postgres://authenticator:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}
      PGRST_DB_SCHEMAS: ${PGRST_DB_SCHEMAS:-public,storage,graphql_public}
      PGRST_DB_ANON_ROLE: anon
      PGRST_JWT_SECRET: ${JWT_SECRET}
      PGRST_DB_USE_LEGACY_GUCS: "false"
      PGRST_DB_MAX_ROWS: 1000

  supabase-realtime:
    container_name: supabase-realtime
    image: supabase/realtime:v2.25.39
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    depends_on:
      supabase-db:
        condition: service_healthy
    environment:
      DB_HOST: supabase-db
      DB_PORT: ${POSTGRES_PORT}
      DB_NAME: ${POSTGRES_DB}
      DB_USER: supabase_admin
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      DB_SSL: "false"
      PORT: 4000
      METRICS_PORT: 4001
      API_JWT_SECRET: ${JWT_SECRET}
      FLY_ALLOC_ID: fly123
      FLY_APP_NAME: realtime
      SECRET_KEY_BASE: ${SECRET_KEY_BASE}
      ERL_AFLAGS: -proto_dist inet_tcp
      ENABLE_TAILSCALE: "false"
      DNS_NODES: "''"

  supabase-db:
    container_name: supabase-db
    image: supabase/postgres:15.1.0.147-preview1
    networks:
      - yasmines-local-ai
    healthcheck:
      test: pg_isready -U postgres -h localhost
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 5s
    volumes:
      - supabase-db-data:/var/lib/postgresql/data
      - ./supabase/docker/volumes/db/init:/docker-entrypoint-initdb.d
    restart: unless-stopped
    ports:
      - ${POSTGRES_PORT}:5432
    environment:
      POSTGRES_HOST: /var/run/postgresql
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_PORT: ${POSTGRES_PORT}

  supabase-meta:
    container_name: supabase-meta
    image: supabase/postgres-meta:v0.75.0
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    environment:
      PG_META_PORT: 8080
      PG_META_DB_HOST: supabase-db
      PG_META_DB_PORT: ${POSTGRES_PORT}
      PG_META_DB_NAME: ${POSTGRES_DB}
      PG_META_DB_USER: supabase_admin
      PG_META_DB_PASSWORD: ${POSTGRES_PASSWORD}

  supabase-imgproxy:
    container_name: supabase-imgproxy
    image: darthsim/imgproxy:v3.8.0
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    environment:
      IMGPROXY_BIND: ":5001"
      IMGPROXY_LOCAL_FILESYSTEM_ROOT: /
      IMGPROXY_USE_ETAG: "true"
      IMGPROXY_ENABLE_WEBP_DETECTION: ${IMGPROXY_ENABLE_WEBP_DETECTION:-false}

  supabase-pooler:
    container_name: supabase-pooler
    image: supabase/pgbouncer:1.19.0
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    depends_on:
      supabase-db:
        condition: service_healthy
    environment:
      POSTGRESQL_HOST: supabase-db
      POSTGRESQL_PORT: ${POSTGRES_PORT}
      POSTGRESQL_USERNAME: supabase_admin
      POSTGRESQL_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRESQL_DATABASE: ${POSTGRES_DB}
      PGBOUNCER_POOL_MODE: transaction
      PGBOUNCER_DEFAULT_POOL_SIZE: ${POOLER_DEFAULT_POOL_SIZE}
      PGBOUNCER_MAX_CLIENT_CONN: ${POOLER_MAX_CLIENT_CONN}
      PGBOUNCER_LISTEN_PORT: 5432
      PGBOUNCER_IGNORE_STARTUP_PARAMETERS: extra_float_digits,options,application_name
      PGBOUNCER_TENANT_ID: ${POOLER_TENANT_ID:-}
      PGBOUNCER_VERBOSE: 0

  supabase-storage:
    container_name: supabase-storage
    image: supabase/storage-api:v0.43.15
    networks:
      - yasmines-local-ai
    depends_on:
      supabase-db:
        condition: service_healthy
        restart: true
      supabase-rest:
        condition: service_started
        restart: true
    restart: unless-stopped
    environment:
      STORAGE_BACKEND: file
      FILE_STORAGE_BACKEND_PATH: /var/lib/storage
      TENANT_ID: stub
      REGION: stub
      GLOBAL_S3_BUCKET: stub
      ENABLE_IMAGE_TRANSFORMATION: "true"
      IMGPROXY_URL: http://supabase-imgproxy:5001
      JWT_SECRET: ${JWT_SECRET}
      DATABASE_URL: postgres://supabase_storage_admin:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      FILE_SIZE_LIMIT: 52428800
      STORAGE_REDIRECT_ALLOW_HOSTS: "${SUPABASE_PUBLIC_URL}"
      PGRST_JWT_SECRET: ${JWT_SECRET}
    volumes:
      - supabase-storage-data:/var/lib/storage

  supabase-functions:
    container_name: supabase-edge-functions
    image: supabase/edge-runtime:v1.22.3
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    depends_on:
      supabase-db:
        condition: service_healthy
    environment:
      JWT_SECRET: ${JWT_SECRET}
      VERIFY_JWT: ${FUNCTIONS_VERIFY_JWT:-false}
      PGHOST: supabase-db
      PGPORT: ${POSTGRES_PORT}
      PGDATABASE: ${POSTGRES_DB}
      PGUSER: supabase_functions_admin
      PGPASSWORD: ${POSTGRES_PASSWORD}
      SITE_URL: ${SITE_URL:-http://localhost:8000}
      SUPABASE_URL: http://supabase-kong:8000
      SUPABASE_ANON_KEY: ${ANON_KEY}
      SUPABASE_SERVICE_ROLE_KEY: ${SERVICE_ROLE_KEY}
      SUPABASE_AUTH_REDIS_CONNECTION_STRING: "redis://supabase-auth-redis:6379"
      REDIS_CONNECTION_STRING: "redis://supabase-auth-redis:6379"
      SUPABASE_SERVE_FUNCTION_LOG_LEVEL: "debug"
      SUPABASE_FUNCTIONS_DOCKER_EXTERNAL_NETWORK: "yasmines-local-ai"

  supabase-analytics:
    container_name: supabase-analytics
    image: supabase/logflare:1.4.0
    networks:
      - yasmines-local-ai
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 5s
    depends_on:
      supabase-db:
        condition: service_healthy
    environment:
      LOGFLARE_NODE_HOST: 127.0.0.1
      LOGFLARE_SINGLE_TENANT: supabase
      PHOENIX_SECRET: ${LOGFLARE_API_KEY:-}
      SECRET_KEY_BASE: ${VAULT_ENC_KEY}
      DATABASE_URL: postgres://supabase_admin:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}
      POSTGRESQL_HOSTNAME: supabase-db
      POSTGRESQL_PORT: ${POSTGRES_PORT}
      POSTGRESQL_USERNAME: postgres
      POSTGRESQL_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRESQL_DATABASE: ${POSTGRES_DB}
      ANALYZE_CHUNK_IO_CONCURRENCY: 4
      INGEST_CHUNK_IO_CONCURRENCY: 4

  supabase-auth-redis:
    container_name: supabase-auth-redis
    image: redis:7.2.3-alpine
    networks:
      - yasmines-local-ai
    restart: unless-stopped
