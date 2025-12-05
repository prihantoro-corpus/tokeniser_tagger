#!/bin/bash

# Define directories
INSTALL_DIR="treetagger_install"
mkdir -p "$INSTALL_DIR/lib"
mkdir -p "$INSTALL_DIR/cmd"

# 1. Install TreeTagger Executable (binary)
TT_URL="https://cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/tree-tagger-linux-3.2.tar.gz"
wget -O tt_binary.tar.gz "$TT_URL"
tar -xzf tt_binary.tar.gz
mv tree-tagger "$INSTALL_DIR/cmd/tree-tagger"
chmod +x "$INSTALL_DIR/cmd/tree-tagger"
rm tt_binary.tar.gz

# 2. Install English Parameter File (required dependency for many taggers)
EN_PAR_URL="https://cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/english-par-3.2.bin"
wget -O "$INSTALL_DIR/lib/english.par" "$EN_PAR_URL"
chmod +x "$INSTALL_DIR/lib/english.par"

# 3. Copy your Indonesian Parameter File
# Assumes indonesian.par is in the root GitHub directory
cp indonesian.par "$INSTALL_DIR/lib/indonesian.par"
chmod +x "$INSTALL_DIR/lib/indonesian.par"

echo "TreeTagger and parameters installed successfully."
