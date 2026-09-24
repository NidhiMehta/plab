#!/usr/bin/env bash
# Compile PLAB papers to PDF  (full bibtex + 3-pass pdflatex)
#
# Papers:
#   main      → main.pdf      "Silent Judge" (first paper, v0.4/v0.5)
#   plab_v06  → plab_v06.pdf  "The Instruction Is the Defense" (second paper, v0.6)
#
# Requires: BasicTeX / MacTeX — install with:
#   brew install --cask basictex
#   sudo tlmgr update --self
#   sudo tlmgr install helvetic units collection-fontsrecommended
#
# Usage (from the paper/ directory):
#   bash compile_paper.sh           # compile both papers
#   bash compile_paper.sh main      # compile first paper only
#   bash compile_paper.sh plab_v06  # compile second paper only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Bring TeX binaries into PATH on macOS (handles both BasicTeX and full MacTeX)
if [[ "$OSTYPE" == "darwin"* ]]; then
  eval "$(/usr/libexec/path_helper)"
fi

if ! command -v pdflatex &>/dev/null; then
  echo "ERROR: pdflatex not found. Install BasicTeX:" >&2
  echo "  brew install --cask basictex" >&2
  echo "  sudo tlmgr install helvetic units collection-fontsrecommended" >&2
  exit 1
fi

compile_one() {
  local TARGET="$1"
  echo "--- Compiling ${TARGET}.tex ---"
  pdflatex -shell-escape -interaction=nonstopmode "$TARGET.tex" > /dev/null
  bibtex "$TARGET" > /dev/null
  pdflatex -shell-escape -interaction=nonstopmode "$TARGET.tex" > /dev/null
  pdflatex -shell-escape -interaction=nonstopmode "$TARGET.tex" > /dev/null
  echo "Done — ${TARGET}.pdf"
}

if [[ $# -eq 0 ]]; then
  compile_one main
  compile_one plab_v06
else
  compile_one "$1"
fi
