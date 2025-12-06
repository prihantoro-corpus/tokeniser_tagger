#!/bin/bash

INSTALL_DIR="treetagger_install"
mkdir -p "$INSTALL_DIR/lib"
mkdir -p "$INSTALL_DIR/cmd"

echo "Starting TreeTagger installation."

# 1. Download and Extract TreeTagger Executable
# Use the official download URL
TT_URL="https://cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/tree-tagger-linux-3.2.2.tar.gz"
DOWNLOAD_NAME="tree-tagger-linux-3.2.2.tar.gz"
EXECUTABLE_NAME="tree-tagger"

wget -q -O "$DOWNLOAD_NAME" "$TT_URL"

if [ -f "$DOWNLOAD_NAME" ]; then
    # Extract the tarball. It typically extracts the executable named 'tree-tagger'.
    tar -xzf "$DOWNLOAD_NAME"
    rm "$DOWNLOAD_NAME"

    # Check for the executable after extraction and move it
    if [ -f "$EXECUTABLE_NAME" ]; then
        echo "Executable found. Moving to cmd directory."
        mv "$EXECUTABLE_NAME" "$INSTALL_DIR/cmd/$EXECUTABLE_NAME"
        chmod +x "$INSTALL_DIR/cmd/$EXECUTABLE_NAME"
    else
        echo "ERROR: Executable not found after extraction. Check tarball contents."
        exit 1
    fi
else
    echo "ERROR: Failed to download TreeTagger executable."
    exit 1
fi

# 2. Install English Parameter File (Often required by setup)
EN_PAR_URL="https://cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/english-par-3.2.bin"
wget -q -O "$INSTALL_DIR/lib/english.par" "$EN_PAR_URL"

# 3. Copy your Indonesian Parameter File
cp indonesian.par "$INSTALL_DIR/lib/indonesian.par"
chmod +x "$INSTALL_DIR/lib/indonesian.par"

echo "TreeTagger and parameters installation complete."
