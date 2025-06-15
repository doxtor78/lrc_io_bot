#!/bin/bash

# Create project directory
mkdir -p cryptofolio_project
cd cryptofolio_project

# Clone Cryptofolio repository
git clone https://github.com/Xtrendence/Cryptofolio.git

# Change to Cryptofolio directory
cd Cryptofolio

# Build and start Docker containers
docker-compose up -d

echo "Setup complete! Cryptofolio is now running at http://localhost:8080" 