#!/bin/bash
# PhotoSort Git Setup Script
# Automates the initial Git setup for your PhotoSort repository
# 
# Usage: bash setup_git.sh

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                PhotoSort v9.1 - Git Setup Wizard                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "photosort.py" ]; then
    echo "❌ Error: photosort.py not found!"
    echo "   Please run this script from your photosort directory."
    echo ""
    echo "   cd /path/to/your/photosort"
    echo "   bash setup_git.sh"
    exit 1
fi

echo "✓ Found photosort.py - we're in the right directory!"
echo ""

# Check if Git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Error: Git is not installed!"
    echo "   Install with: brew install git"
    exit 1
fi

echo "✓ Git is installed"
echo ""

# Check if already a Git repo
if [ -d ".git" ]; then
    echo "⚠️  Warning: This directory is already a Git repository."
    echo "   Do you want to continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        echo "Setup cancelled."
        exit 0
    fi
else
    # Initialize Git
    echo "🔧 Initializing Git repository..."
    git init
    echo "✓ Git repository initialized"
    echo ""
fi

# Check for required files
echo "🔍 Checking for required files..."
echo ""

if [ ! -f ".gitignore" ]; then
    echo "⚠️  Warning: .gitignore not found!"
    echo "   This file is CRITICAL to prevent committing images."
    echo "   Please add it before continuing."
    exit 1
fi
echo "✓ .gitignore found"

if [ ! -f "requirements.txt" ]; then
    echo "⚠️  Warning: requirements.txt not found"
    echo "   (Not critical, but recommended)"
fi

if [ ! -f "README.md" ]; then
    echo "⚠️  Warning: README.md not found"
    echo "   (Not critical, but recommended)"
fi

echo ""

# Show what will be tracked
echo "📋 Files that will be tracked by Git:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git status --short 2>/dev/null || echo "   (Run 'git status' to see files)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for image files (CRITICAL!)
echo "🔍 Checking for image files (these should NOT be tracked)..."
image_files=$(git status --short 2>/dev/null | grep -E '\.(jpg|jpeg|png|gif|raw|rw2|cr2|nef|arw|dng)$' || echo "")
if [ -n "$image_files" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ ERROR: Image files detected in Git tracking!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$image_files"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Your .gitignore is not working properly!"
    echo "DO NOT CONTINUE. Fix .gitignore first."
    echo ""
    echo "Check that .gitignore includes:"
    echo "  *.jpg"
    echo "  *.jpeg"
    echo "  *.png"
    echo "  *.rw2"
    echo "  (and other image formats)"
    exit 1
fi
echo "✓ No image files detected - safe to continue!"
echo ""

# Ask for confirmation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Ready to create your first commit?"
echo "This will:"
echo "  1. Stage all files (respecting .gitignore)"
echo "  2. Create initial commit"
echo "  3. Set up for GitHub push"
echo ""
echo "Continue? (y/n): "
read -r response

if [ "$response" != "y" ]; then
    echo "Setup cancelled. No changes made."
    exit 0
fi

# Stage all files
echo ""
echo "📦 Staging files..."
git add .

# Show what's staged
echo ""
echo "📋 Files staged for commit:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git status --short
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit: PhotoSort v9.1 with v8.0 engines

- Complete v9.1 with AI burst naming and organized _Bursts/ folder
- v8.0 CLIP semantic burst detection integrated
- v8.0 BRISQUE quality assessment integrated  
- qwen2.5vl:3b for deterministic AI naming
- All documentation, configuration, and testing tools
- Tested and working on fanless MacBook Air M1"

if [ $? -eq 0 ]; then
    echo "✓ Initial commit created successfully!"
else
    echo "❌ Commit failed. Check errors above."
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Git Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo ""
echo "1. Create a PRIVATE repository on GitHub:"
echo "   → Go to https://github.com/new"
echo "   → Name: photosort"
echo "   → Description: AI-powered photography workflow automation"
echo "   → ✅ CHECK 'Private'"
echo "   → Do NOT initialize with README"
echo "   → Click 'Create repository'"
echo ""
echo "2. Connect your local repo to GitHub:"
echo "   (Replace YOUR_USERNAME with your GitHub username)"
echo ""
echo "   git remote add origin https://github.com/YOUR_USERNAME/photosort.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Enter your GitHub credentials when prompted"
echo ""
echo "4. Verify on GitHub that your code is there (and no images!)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "You can now sleep at night! 😴 Your code is version controlled."
echo ""
echo "For full instructions, see: GITHUB_SETUP_GUIDE.md"
echo ""
