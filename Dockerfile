# Start with a suitable Python base image
FROM python:3.10-slim-buster

# Define the directory where TreeTagger will be installed
ENV TREETAGGER_DIR /usr/local/treetagger
# Add TreeTagger binaries to the system PATH
ENV PATH $PATH:$TREETAGGER_DIR/bin
# Set the environment variable the Python wrapper looks for
ENV TAGDIR $TREETAGGER_DIR

# --- 1. Install System Dependencies ---
# Install tools (wget, unzip), Perl runtime, and build essentials
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        unzip \
        perl \
        build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# --- 2. Install TreeTagger Binary ---
WORKDIR /tmp
# Download the TreeTagger executable package
RUN wget http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/tree-tagger-linux-3.2.zip && \
    unzip tree-tagger-linux-3.2.zip && \
    mkdir -p $TREETAGGER_DIR && \
    mv tagger/* $TREETAGGER_DIR/ && \
    rm tree-tagger-linux-3.2.zip && \
    chmod a+x $TREETAGGER_DIR/bin/*

# --- 3. Install Language Files (Required for wrapper to work) ---
# NOTE: Replace these with your Indonesian language files when ready.
# We use English files here just to satisfy the wrapper's startup requirements.
WORKDIR $TREETAGGER_DIR/lib
RUN wget http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/english-par-linux-3.2-utf8.bin && \
    wget http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/english-abbrev-tags && \
    mv english-par-linux-3.2-utf8.bin english-utf8.par && \
    mv english-abbrev-tags english-abbrev.txt

# --- 4. Install Python Dependencies ---
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- 5. Application Setup ---
COPY . /app
EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
