#!/bin/bash
# Sync code changes to Raspberry Pi
# Usage: ./sync_to_pi.sh [user@pi_hostname]

PI_HOST="${1:-techspark@techspark}"
PI_PATH="~/techspark/lelamp"

echo "🔄 Syncing code to $PI_HOST:$PI_PATH"

# Sync modified files
rsync -avz --progress \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='firebase-credentials.json' \
  --exclude='.env' \
  ./ "$PI_HOST:$PI_PATH/"

echo "✅ Sync complete!"
echo ""
echo "Next steps on Pi:"
echo "1. cd ~/techspark/lelamp"
echo "2. .venv/bin/pip install pyserial>=3.5"
echo "3. ./start.sh"
