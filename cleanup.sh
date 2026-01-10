#!/bin/bash

# Risk Churn Platform - Cleanup Script
# This script removes all deployment artifacts and Docker resources

set -e  # Exit on error

echo "Risk Churn Platform - Cleanup Script"
echo "====================================="
echo ""
echo "This will remove:"
echo "  - All running containers"
echo "  - All Docker volumes (data will be lost)"
echo "  - All Docker images for this project"
echo "  - Frontend build artifacts"
echo "  - Python cache files"
echo "  - Test artifacts"
echo ""
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Stop and remove all containers and volumes
echo "[1/7] Stopping and removing containers and volumes..."
if [ -f "docker-compose.yml" ]; then
    docker-compose down -v 2>/dev/null || true
    echo "   ✓ Containers and volumes removed"
else
    echo "   ⚠ No docker-compose.yml found, skipping"
fi

# Remove Docker images
echo ""
echo "[2/7] Removing Docker images..."
IMAGES=$(docker images | grep risk-churn-platform | awk '{print $3}' | sort -u)
if [ -n "$IMAGES" ]; then
    echo "$IMAGES" | xargs docker rmi -f 2>/dev/null || true
    echo "   ✓ Docker images removed"
else
    echo "   ⚠ No project images found"
fi

# Clean frontend artifacts
echo ""
echo "[3/7] Cleaning frontend artifacts..."
if [ -d "frontend/node_modules" ] || [ -d "frontend/build" ]; then
    rm -rf frontend/node_modules frontend/build
    echo "   ✓ Frontend artifacts removed"
else
    echo "   ⚠ No frontend artifacts found"
fi

# Clean Python cache
echo ""
echo "[4/7] Cleaning Python cache files..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
PYC_COUNT=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYCACHE_COUNT" -gt 0 ] || [ "$PYC_COUNT" -gt 0 ]; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo "   ✓ Python cache removed ($PYCACHE_COUNT dirs, $PYC_COUNT files)"
else
    echo "   ⚠ No Python cache found"
fi

# Clean test artifacts
echo ""
echo "[5/7] Cleaning test artifacts..."
TEST_ARTIFACTS=".pytest_cache .mypy_cache .ruff_cache htmlcov .coverage"
CLEANED=0
for artifact in $TEST_ARTIFACTS; do
    if [ -e "$artifact" ]; then
        rm -rf "$artifact"
        CLEANED=$((CLEANED + 1))
    fi
done
if [ $CLEANED -gt 0 ]; then
    echo "   ✓ Test artifacts removed ($CLEANED items)"
else
    echo "   ⚠ No test artifacts found"
fi

# Clean macOS artifacts
echo ""
echo "[6/7] Cleaning macOS artifacts..."
DSSTORE_COUNT=$(find . -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
if [ "$DSSTORE_COUNT" -gt 0 ]; then
    find . -name ".DS_Store" -delete
    echo "   ✓ .DS_Store files removed ($DSSTORE_COUNT files)"
else
    echo "   ⚠ No .DS_Store files found"
fi

# Docker system prune
echo ""
echo "[7/7] Running Docker system prune..."
PRUNE_OUTPUT=$(docker system prune -f 2>&1)
echo "$PRUNE_OUTPUT" | grep -i "Total reclaimed space" || echo "   ✓ Docker system pruned"

echo ""
echo "====================================="
echo "Cleanup Complete!"
echo "====================================="
echo ""
echo "All deployment artifacts have been removed."
echo "To redeploy the platform, run: ./deploy.sh"
echo ""
