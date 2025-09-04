#!/bin/bash

# Build script for generating Python protobuf files
# This script generates the protobuf files needed for the Python calc engine

set -e

echo "🔧 Building protobuf files for Python calc engine..."

# Create proto directory if it doesn't exist
mkdir -p proto

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "❌ protoc is not installed. Please install it first:"
    echo "   macOS: brew install protobuf"
    echo "   Ubuntu: sudo apt-get install protobuf-compiler"
    echo "   Windows: Download from https://github.com/protocolbuffers/protobuf/releases"
    exit 1
fi

# Check if grpcio-tools is installed
if ! python -c "import grpc_tools" &> /dev/null; then
    echo "📦 Installing grpcio-tools..."
    pip install grpcio-tools
fi

# Generate Python files from protobuf
echo "🚀 Generating Python protobuf files..."
python -m grpc_tools.protoc \
    --proto_path=proto_src \
    --python_out=proto \
    --grpc_python_out=proto \
    proto_src/steelbeam.proto

# Fix import paths in generated files (common issue with Python gRPC)
if [ -f "proto/steelbeam_pb2_grpc.py" ]; then
    echo "🔧 Fixing import paths in generated files..."
    sed -i.bak 's/import steelbeam_pb2/from . import steelbeam_pb2/' proto/steelbeam_pb2_grpc.py
    rm proto/steelbeam_pb2_grpc.py.bak 2>/dev/null || true
fi

echo "✅ Protobuf files generated successfully!"
echo "📁 Files created:"
ls -la proto/*.py

echo ""
echo "🎯 Ready for deployment! The Python calc engine now has all required protobuf files."
