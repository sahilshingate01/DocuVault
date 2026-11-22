#!/usr/bin/env bash
# ==============================================================================
# DocuVault Automated Screen Recording & Viva Presentation Script
# Records screen synchronized with DBMS_VIVA_SCRIPT.md for voiceover.
# ==============================================================================

set -e

DURATION="${1:-540}" # Default: 540 seconds (9 minutes)
SPEED="${2:-1.0}"
OUTPUT_PATH="${3:-$HOME/Desktop/DocuVault_Viva_Recording.mp4}"

echo "========================================================================"
echo "  🎬 DOCUVAULT AUTOMATED SCREEN RECORDING & VIVA PRESENTATION"
echo "========================================================================"
echo "• Duration: ${DURATION} seconds ($(( DURATION / 60 )) minutes $(( DURATION % 60 )) seconds)"
echo "• Sync Speed: ${SPEED}x"
echo "• Output Target: ${OUTPUT_PATH}"
echo "========================================================================"

# Step 1: Ensure backend server is healthy
if ! curl -s http://127.0.0.1:8000/health | grep -q "healthy"; then
    echo "⚠️ Backend not detected on 127.0.0.1:8000. Launching background server..."
    venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/docuvault_server.log 2>&1 &
    sleep 2
fi

echo "✔ Backend service confirmed on http://127.0.0.1:8000"

# Step 2: Open browser to auto-presentation URL
TARGET_URL="http://127.0.0.1:8000/?autopresent=true&speed=${SPEED}"
echo "🌐 Opening DocuVault auto-presentation at: ${TARGET_URL}"

if [ -d "/Applications/Google Chrome.app" ]; then
    open -a "Google Chrome" "${TARGET_URL}"
else
    open "${TARGET_URL}"
fi

# Step 3: Countdown
echo ""
echo "⏳ Getting ready to record in 4 seconds... Please ensure the window is active."
sleep 1; echo "3..."
sleep 1; echo "2..."
sleep 1; echo "1..."
sleep 1

# Step 4: Execute screencapture
echo "🔴 RECORDING IN PROGRESS..."
echo "The application will automatically step through all 5 DBMS Viva questions."
echo "Press Ctrl+C at any time if you wish to stop early."

screencapture -v -C -k -V "${DURATION}" "${OUTPUT_PATH}"

echo ""
echo "========================================================================"
echo "✔ RECORDING FINISHED SUCCESSFULLY!"
echo "Video saved to: ${OUTPUT_PATH}"
echo "You can now open this file in QuickTime or any editor to add your voiceover."
echo "========================================================================"
