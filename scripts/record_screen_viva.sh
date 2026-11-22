#!/usr/bin/env bash
# ==============================================================================
# DocuVault DBMS Viva Automated Screen Recording Suite
# Drives the screen UI according to the script and records an MP4 video.
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

OUTPUT_DIR="$HOME/Desktop"
OUTPUT_FILE="$OUTPUT_DIR/DocuVault_Viva_Recording.mp4"

# Handle optional --test flag for quick 15-second trial
if [ "$1" == "--test" ]; then
    DURATION=15
    OUTPUT_FILE="$OUTPUT_DIR/DocuVault_Viva_Sample_Test.mp4"
    echo "=================================================================="
    echo "🎬 RUNNING 15-SECOND SAMPLE TEST RECORDING"
    echo "=================================================================="
else
    DURATION=560  # 9 minutes 20 seconds (under 10 minute cap)
    echo "=================================================================="
    echo "🎬 STARTING FULL 9-MINUTE DBMS VIVA AUTOMATED SCREEN RECORDING"
    echo "=================================================================="
fi

echo "Target Output File: $OUTPUT_FILE"
echo "Duration: $DURATION seconds"
echo

# 1. Ensure backend server is healthy
echo "Step 1: Checking DocuVault backend service..."
if ! curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "Starting backend server in background..."
    venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
    sleep 2
fi
echo "✔ Backend server is healthy on http://127.0.0.1:8000"
echo

# 2. Open browser with autopilot sequence
echo "Step 2: Launching DocuVault with Auto-Director..."
open "http://127.0.0.1:8000/?autopilot=1"
sleep 3

# 3. Start screen recording
echo "Step 3: Recording screen now (Duration: ${DURATION}s)..."
echo "        • The browser will automatically demonstrate each question on screen."
echo "        • Please do not close or cover the browser window while recording."
echo "        • To stop early at any time, press [Ctrl + C] in this terminal."
echo

screencapture -v -C -k -V "$DURATION" "$OUTPUT_FILE"

echo
echo "=================================================================="
echo "✔ SCREEN RECORDING COMPLETED SUCCESSFULLY!"
echo "=================================================================="
echo "Saved Video: $OUTPUT_FILE"
if [ -f "/opt/homebrew/bin/ffmpeg" ]; then
    echo "Video Stream Metadata:"
    /opt/homebrew/bin/ffmpeg -i "$OUTPUT_FILE" 2>&1 | grep -E "Duration|Video:"
fi
echo
echo "You can now add your voiceover to this video following the script in:"
echo "DBMS_VIVA_SCRIPT.md"
echo "=================================================================="
