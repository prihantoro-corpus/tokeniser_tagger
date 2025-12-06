# Start with a suitable Python base image
FROM python:3.10-slim-buster

# 1. Install Perl and the required module (libhtml-parser-perl)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        perl \
        libhtml-parser-perl \
        build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy all local files (app.py, Perl scripts, lexicon) into the container's /app directory
COPY . /app

# 4. Install Python dependencies (like Streamlit, using requirements.txt)
# You should also create a requirements.txt file containing just 'streamlit'
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Expose the default Streamlit port
EXPOSE 8501

# 6. Define the command to run the Streamlit app when the container starts
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
