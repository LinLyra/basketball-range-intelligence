#!/bin/zsh
set -e
cd "${0:A:h}/web"
echo "Basketball Range Intelligence"
echo "Open http://127.0.0.1:5173/ in your browser."
npm run dev
