import streamlit as st
import subprocess
import os
import time

# --- Configuration ---
CLITIC_SCRIPT = 'separate-clitic.pl'
TOKENIZE_SCRIPT = 'tokenize.pl'
INPUT_DIR = 'INPUT'
OUTPUT_DIR = 'OUTPUT'
TEMP_INPUT_FILE = 'temp_input.txt' # File used for passing data to separate-clitic.pl

def setup_directories():
    """Ensure the necessary folders exist."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_perl_pipeline(input_text: str) -> str | None:
    """
    Executes the two-step Perl pipeline:
    1. Separate Clitic (File-based)
    2. Tokenize (STDIN/STDOUT-based)
    """
    input_file_path = os.path.join(INPUT_DIR, TEMP_INPUT_FILE)
    output_file_path = os.path.join(OUTPUT_DIR, TEMP_INPUT_FILE)
    
    # 1. Write user input to a temporary file for the first Perl script
    try:
        with open(input_file_path, 'w', encoding='utf-8') as f:
            f.write(input_text)
    except Exception as e:
        st.error(f"Error writing temporary input file: {e}")
        return None

    # --- Step 1: Run Clitic Separation Script (separate-clitic.pl) ---
    # This script processes files from INPUT to OUTPUT.
    st.info(f"Running Step 1: Clitic separation via {CLITIC_SCRIPT}...")
    try:
        subprocess.run(
            ['perl', CLITIC_SCRIPT], 
            check=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
    except subprocess.CalledProcessError as e:
        st.error(f"❌ Error in {CLITIC_SCRIPT}. Check if 'lexicon_only.txt' and folders exist.")
        st.code(e.stderr, language='text')
        return None
    except FileNotFoundError:
        st.error(f"❌ Error: Perl interpreter or '{CLITIC_SCRIPT}' not found. Check installation/path.")
        return None

    # 2. Read the output of the clitic script
    try:
        with open(output_file_path, 'r', encoding='utf-8') as f:
            clitic_output = f.read()
    except Exception as e:
        st.error(f"Error reading output from {OUTPUT_DIR}: {e}")
        return None

    # --- Step 2: Run TreeTagger Tokenization Script (tokenize.pl) ---
    # This script reads from STDIN and prints to STDOUT, one token per line.
    st.info(f"Running Step 2: TreeTagger tokenization via {TOKENIZE_SCRIPT}...")
    try:
        # Pass the output of Step 1 to the STDIN of Step 2
        process = subprocess.run(
            ['perl', TOKENIZE_SCRIPT, '-u'], # -u ensures UTF8 support
            input=clitic_output,
            check=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        return process.stdout.strip()

    except subprocess.CalledProcessError as e:
        st.error(f"❌ Error in {TOKENIZE_SCRIPT}.")
        st.code(e.stderr, language='text')
        return None
    except FileNotFoundError:
        st.error(f"❌ Error: Perl interpreter or '{TOKENIZE_SCRIPT}' not found. Check installation/path.")
        return None

# --- Main Streamlit Application ---

def main():
    st.title("🇵🇾 Full Indonesian Tokenizer (Perl Pipeline)")
    st.markdown("---")

    setup_directories()

    st.header("1. Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-buku nya ada di U.S.A. Kulihat rumahmu (yang) besar!",
        height=150
    )
    
    if st.button("Run Full Perl Pipeline", type="primary"):
        if user_input.strip():
            
            # Reset UI elements for a clear run
            st.session_state['result'] = run_perl_pipeline(user_input)

            if st.session_state['result']:
                st.header("2. Final Tokenization Output")
                st.markdown("Output shows tokenization performed in two stages:")
                st.markdown("* **Stage 1:** Clitic separation (`rumah -mu`)")
                st.markdown("* **Stage 2:** Punctuation/Abbreviation/Tag separation (`U.S.A.`, `(`, `!`)")
                
                # The output is already one token per line
                st.code(st.session_state['result'], language='text')
                
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()
