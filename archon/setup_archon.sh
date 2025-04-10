#!/bin/bash

# Setup script for Archon integration with Yasmine's Local AI stack
echo "Setting up Archon for integration with Yasmine's Local AI stack..."

# Clone the Archon repository
if [ ! -d "archon_repo" ]; then
  echo "Cloning Archon repository..."
  git clone https://github.com/coleam00/archon.git archon_repo
  cd archon_repo
else
  echo "Archon repository already exists, updating..."
  cd archon_repo
  git pull
fi

# Copy necessary files to parent directory
echo "Copying necessary files..."
cp Dockerfile ../
cp -r mcp ../
cp requirements.txt ../

# Create .env file for Archon if it doesn't exist
if [ ! -f "../.env" ]; then
  echo "Creating .env file for Archon..."
  cat > ../.env << EOL
# Archon Environment Variables
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OLLAMA_API_BASE=http://host.docker.internal:11434
EOL
  echo ".env file created. Please edit it with your API keys."
else
  echo ".env file already exists."
fi

# Create workbench directory if it doesn't exist
if [ ! -d "../workbench" ]; then
  echo "Creating workbench directory..."
  mkdir -p ../workbench
fi

echo "Archon setup complete! You can now integrate it with your docker-compose.yml"
