#!/usr/bin/env python3
"""
Multi-Galaxy-Note Setup Verification Script
Verifies that all components are properly set up
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and print status"""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (MISSING)")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists and print status"""
    if Path(dirpath).is_dir():
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} (MISSING)")
        return False

def main():
    print("🔍 Multi-Galaxy-Note Setup Verification")
    print("=" * 50)
    
    all_good = True
    
    # Check project structure
    print("\n📁 Project Structure:")
    structure_checks = [
        ("frontend", "Frontend directory"),
        ("backend", "Backend directory"),
        ("scripts", "Scripts directory"),
        (".github/workflows", "CI/CD workflows"),
    ]
    
    for path, desc in structure_checks:
        if not check_directory_exists(path, desc):
            all_good = False
    
    # Check configuration files
    print("\n⚙️ Configuration Files:")
    config_checks = [
        ("docker-compose.yml", "Docker Compose configuration"),
        ("backend/Dockerfile", "Backend Dockerfile"),
        ("frontend/Dockerfile", "Frontend Dockerfile"),
        ("backend/requirements.txt", "Backend dependencies"),
        ("frontend/package.json", "Frontend dependencies"),
        (".gitignore", "Git ignore file"),
        ("README.md", "Project documentation"),
        ("Makefile", "Development commands"),
    ]
    
    for path, desc in config_checks:
        if not check_file_exists(path, desc):
            all_good = False
    
    # Check backend structure
    print("\n🐍 Backend Structure:")
    backend_checks = [
        ("backend/main.py", "FastAPI main application"),
        ("backend/app/__init__.py", "App package"),
        ("backend/app/core/config.py", "Configuration module"),
        ("backend/tests/test_main.py", "Basic tests"),
        ("backend/.env.example", "Environment template"),
    ]
    
    for path, desc in backend_checks:
        if not check_file_exists(path, desc):
            all_good = False
    
    # Check frontend structure
    print("\n⚛️ Frontend Structure:")
    frontend_checks = [
        ("frontend/src/App.tsx", "React App component"),
        ("frontend/tailwind.config.js", "Tailwind configuration"),
        ("frontend/tsconfig.json", "TypeScript configuration"),
    ]
    
    for path, desc in frontend_checks:
        if not check_file_exists(path, desc):
            all_good = False
    
    # Check CI/CD
    print("\n🔄 CI/CD Pipeline:")
    cicd_checks = [
        (".github/workflows/ci.yml", "GitHub Actions workflow"),
    ]
    
    for path, desc in cicd_checks:
        if not check_file_exists(path, desc):
            all_good = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 All components are properly set up!")
        print("\n📋 Next steps:")
        print("  1. Run 'make setup' to initialize the development environment")
        print("  2. Run 'make start' to start all services with Docker")
        print("  3. Or run services individually:")
        print("     - Backend: 'make dev-be'")
        print("     - Frontend: 'make dev-fe'")
        print("\n🌐 Access points:")
        print("  - Frontend: http://localhost:3000")
        print("  - Backend API: http://localhost:8000")
        print("  - API Documentation: http://localhost:8000/docs")
        return 0
    else:
        print("❌ Some components are missing. Please check the setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())