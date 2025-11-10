#!/bin/bash
# Quick test script for all v7.1 modules

echo "🧪 Testing PHOTOSORT v7.1 Modules"
echo "=================================="
echo

echo "1️⃣  Testing phrases.py..."
python3 phrases.py
echo

echo "2️⃣  Testing utils.py..."
python3 utils.py
echo

echo "3️⃣  Testing session_tracker.py..."
python3 session_tracker.py
echo

echo "4️⃣  Testing smart_progress.py..."
python3 smart_progress.py
echo

echo "✅ All module tests complete!"
echo
echo "Note: directory_selector.py requires interactive input"
echo "Test it manually with: python3 directory_selector.py"
