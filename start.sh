#!/bin/bash
echo "🚀 Starting DiamondAI Preview (Junior Friendly)"

# Copy files if needed
cp preview.html frontend/dist/preview.html 2>/dev/null || true
cp demo_stock.json frontend/dist/demo_stock.json 2>/dev/null || true

cd frontend/dist || exit

echo ""
echo "✅ Open this link in your browser:"
echo "   http://localhost:8765/preview.html"
echo ""
echo "All trained customer questions are clickable."
echo "Press Ctrl + C to stop the server."
echo ""

python3 -m http.server 8765
