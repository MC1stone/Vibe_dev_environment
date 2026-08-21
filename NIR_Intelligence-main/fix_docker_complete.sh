#!/bin/bash

# NIR Intelligence Platform - Complete Docker Fix
echo "🔧 Fixing Docker issues for NIR Intelligence Platform"

# 1. Clean up completely
echo "🧹 Complete cleanup..."
docker stop nir_postgresql_test nir_weaviate_test nir_ilias_test 2>/dev/null
docker rm -f nir_postgresql_test nir_weaviate_test nir_ilias_test 2>/dev/null
docker volume rm nir_test_postgres_data nir_test_weaviate_data 2>/dev/null
docker network rm nir_test_network 2>/dev/null

# 2. Kill port processes
echo "🔫 Killing port processes..."
sudo lsof -i :5432 | awk 'NR!=1 {print $2}' | xargs kill -9 2>/dev/null
sudo lsof -i :8080 | awk 'NR!=1 {print $2}' | xargs kill -9 2>/dev/null
sudo lsof -i :8081 | awk 'NR!=1 {print $2}' | xargs kill -9 2>/dev/null

# 3. Fix permissions
echo "🔐 Fixing permissions..."
mkdir -p nir_test_env/server/data/{raw,processed,output}
sudo chown -R $USER:$USER nir_test_env/ 2>/dev/null
sudo chmod -R 755 nir_test_env/ 2>/dev/null

# 4. Create simplified compose file
cat > nir_test_env/docker-compose.fixed.yml << 'YAML'
version: '3.8'

services:
  postgresql:
    image: postgres:15-alpine
    container_name: nir_postgresql_test
    environment:
      POSTGRES_USER: nir_user
      POSTGRES_PASSWORD: nir_password
      POSTGRES_DB: nir_db
    ports:
      - "5432:5432"
    volumes:
      - nir_test_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nir_user -d nir_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - nir_test_network

  weaviate:
    image: semitechnologies/weaviate:1.23.0
    container_name: nir_weaviate_test
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      PERSISTENCE_DATA_PATH: "/var/lib/weaviate"
    ports:
      - "8080:8080"
    volumes:
      - nir_test_weaviate_data:/var/lib/weaviate
    restart: unless-stopped
    networks:
      - nir_test_network

  ilias:
    image: python:3.12-slim
    container_name: nir_ilias_test
    command: tail -f /dev/null
    ports:
      - "8081:8081"
    volumes:
      - ./nir_test_env/server/data:/app/data
    restart: unless-stopped
    networks:
      - nir_test_network

volumes:
  nir_test_postgres_data:
  nir_test_weaviate_data:

networks:
  nir_test_network:
    driver: bridge
YAML

# 5. Try docker compose v2
echo "🚀 Trying docker compose v2..."
if docker compose -f nir_test_env/docker-compose.fixed.yml up -d; then
    echo "✅ Docker compose v2 worked!"
else
    echo "❌ Docker compose v2 failed, trying v1..."

    # 6. Try docker-compose v1
    if docker-compose -f nir_test_env/docker-compose.fixed.yml up -d; then
        echo "✅ Docker compose v1 worked!"
    else
        echo "❌ Both methods failed, starting manually..."

        # 7. Start containers manually
        docker run -d --name nir_postgresql_test \
          -e POSTGRES_USER=nir_user \
          -e POSTGRES_PASSWORD=nir_password \
          -e POSTGRES_DB=nir_db \
          -p 5432:5432 \
          -v nir_test_postgres_data:/var/lib/postgresql/data \
          --restart unless-stopped \
          --network nir_test_network \
          postgres:15-alpine

        docker network create nir_test_network 2>/dev/null

        docker run -d --name nir_weaviate_test \
          -e QUERY_DEFAULTS_LIMIT=25 \
          -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
          -p 8080:8080 \
          -v nir_test_weaviate_data:/var/lib/weaviate \
          --restart unless-stopped \
          --network nir_test_network \
          semitechnologies/weaviate:1.23.0

        docker run -d --name nir_ilias_test \
          -p 8081:8081 \
          -v $(pwd)/nir_test_env/server/data:/app/data \
          --restart unless-stopped \
          --network nir_test_network \
          python:3.12-slim tail -f /dev/null

        echo "✅ Manual startup completed"
    fi
fi

# 8. Verify containers
echo "🔍 Verifying containers..."
sleep 15
docker ps

# 9. Test database
echo "🔗 Testing database..."
if docker exec nir_postgresql_test pg_isready -U nir_user -d nir_db; then
    echo "✅ Database ready"
else
    echo "❌ Database not ready"
    docker logs nir_postgresql_test
fi

echo "🎉 Setup complete!"
