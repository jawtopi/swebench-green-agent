#!/bin/bash
# Demo script for SWE-Bench Green Agent

set -e

echo "=========================================="
echo "SWE-Bench Green Agent Demo"
echo "=========================================="
echo ""

# Base URL
BASE_URL="http://localhost:8000"

# Test 1: Get Agent Card
echo "1. Getting Agent Card (GET /card)"
echo "------------------------------------------"
curl -s "${BASE_URL}/card" | python3 -m json.tool
echo ""
echo ""

# Test 2: Reset Environment
echo "2. Resetting Environment (POST /reset)"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/reset" | python3 -m json.tool
echo ""
echo ""

# Test 3: Test numpy-1234 with good patch
echo "3. Running numpy-1234 with GOOD patch"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/task" \
     -H "Content-Type: application/json" \
     -d '{"task_id": "numpy-1234", "patch_choice": "good"}' | python3 -m json.tool
echo ""
echo ""

# Test 4: Test numpy-1234 with bad patch
echo "4. Running numpy-1234 with BAD patch"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/task" \
     -H "Content-Type: application/json" \
     -d '{"task_id": "numpy-1234", "patch_choice": "bad"}' | python3 -m json.tool
echo ""
echo ""

# Test 5: Test django-5678 with good patch
echo "5. Running django-5678 with GOOD patch"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/task" \
     -H "Content-Type: application/json" \
     -d '{"task_id": "django-5678", "patch_choice": "good"}' | python3 -m json.tool
echo ""
echo ""

# Test 6: Test django-5678 with bad patch (apply error)
echo "6. Running django-5678 with BAD patch (apply error)"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/task" \
     -H "Content-Type: application/json" \
     -d '{"task_id": "django-5678", "patch_choice": "bad"}' | python3 -m json.tool
echo ""
echo ""

echo "=========================================="
echo "Demo Complete!"
echo "=========================================="
echo ""
echo "Logs are available at: ${BASE_URL}/logs/<filename>"
echo ""
echo "Example:"
echo "  curl ${BASE_URL}/logs/numpy-1234-good.txt"
echo ""
