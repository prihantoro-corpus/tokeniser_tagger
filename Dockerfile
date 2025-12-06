# Use Python 3.13 as required by the Streamlit environment
FROM python:3.13-slim

# Define the working directory
WORKDIR /app

# --- 1. Install System Dependencies ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        unzip \
        perl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# --- 2. Install Python Dependencies (SpaCy) ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- 3. Install SpaCy Language Models (Direct PIP ONLY) ---
RUN echo "Starting fresh SpaCy model installation (Direct PIP)" && \
    pip install en-core-web-sm==3.7.0 && \
    pip install fr-core-news-sm==3.7.0 && \
    pip install es-core-news-sm==3.7.0
    # REMOVED: python -m spacy link commands

# --- 4. Application Setup ---
COPY . /app
EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
