#!/bin/bash

# Stop on error
set -e

# Get the absolute path of the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to stop backend when this script is stopped
cleanup() {
    echo -e "\n\nMematikan backend..."
    # Suppress error if directory doesn't exist or docker is already stopped
    cd "$PROJECT_ROOT/autoclipper-backend" || true
    docker compose stop || true
    echo "Backend mati."
}

# Trap Interrupts (Ctrl+C) to run cleanup
trap cleanup SIGINT SIGTERM EXIT

echo "Memulai project AutoClipper..."

# --- 1. START BACKEND ---
echo "Menjalankan Backend (Docker)..."
cd "$PROJECT_ROOT/autoclipper-backend"

# Check dependencies
if ! command -v docker &> /dev/null; then
    echo "❌ Docker tidak ditemukan. Tolong install Docker dulu."
    trap - SIGINT SIGTERM EXIT
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker belum jalan, tolong buka Docker Desktop dulu."
    trap - SIGINT SIGTERM EXIT
    exit 1
fi

# Start services
docker compose up -d

# Check if backend started successfully
if [ $? -ne 0 ]; then
    echo "❌ Gagal menjalankan backend."
    exit 1
fi

echo "   Backend API: http://localhost:8000"
echo "   API Docs:    http://localhost:8000/docs"


# --- 2. START FRONTEND ---
echo -e "\nMenjalankan Frontend..."
cd "$PROJECT_ROOT/autoclipper-frontend"

# Check for stale process on port 3000
if lsof -i :3000 -t >/dev/null 2>&1; then
    echo "   ⚠️ Ada proses nyangkut di port 3000. Mematikan..."
    lsof -i :3000 -t | xargs kill -9 2>/dev/null
fi

# Clean up stale lock file
if [ -f ".next/dev/lock" ]; then
    echo "   🧹 Menghapus file lock lama..."
    rm ".next/dev/lock"
fi

if [ ! -d "node_modules" ]; then
    echo "   📦 Menginstall dependencies (pertama kali)..."
    npm install
fi

echo "   Frontend:    http://localhost:3000"
echo "   (Tekan Ctrl+C untuk berhenti)"
echo ""

# Run Next.js in foreground
npm run dev
