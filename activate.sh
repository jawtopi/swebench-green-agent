#!/bin/bash
# Helper script to activate virtual environment

if [ ! -d "venv" ]; then
    echo "Virtual environment not found!"
    echo "Creating it now..."
    make venv
    echo ""
fi

echo "Activating virtual environment..."
echo ""
echo "Run this command:"
echo "  source venv/bin/activate"
echo ""
echo "Or use: source activate.sh && source venv/bin/activate"
