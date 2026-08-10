#!/bin/bash

# Install Agent Dependencies in Current Workspace Venv
set -e

echo "📦 Installing LangGraph and LangChain dependencies..."
echo ""

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found at ./venv"
    echo "Please create it first with: python3 -m venv venv"
    exit 1
fi

# Install packages
echo "Installing packages in: $(pwd)/venv"
./venv/bin/pip install --upgrade pip
./venv/bin/pip install \
    langgraph \
    langchain \
    langchain-core \
    langchain-community \
    langchain-ollama \
    chromadb \
    sentence-transformers \
    langchain-chroma \
    sse-starlette \
    redis \
    tiktoken \
    tenacity \
    instructor

echo ""
echo "✅ All dependencies installed successfully!"
echo ""
echo "Verifying installation..."
./venv/bin/python -c "import langchain_core; print('✅ langchain_core imported successfully')"
./venv/bin/python -c "import langgraph; print('✅ langgraph imported successfully')"
./venv/bin/python -c "from langgraph.graph import StateGraph; print('✅ StateGraph imported successfully')"

echo ""
echo "🎉 Installation complete! You can now restart the backend."

# Made with Bob
