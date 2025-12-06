import streamlit as st
import subprocess
import os
import shutil # Used for directory management

# --- Configuration ---
CLITIC_SCRIPT = 'separate-clitic.pl'
TOKENIZE_SCRIPT = 'tokenize.pl'
LEXICON_FILE = 'lexicon_only.txt'
INPUT_DIR = 'INPUT'
OUTPUT_DIR = 'OUTPUT'
TEMP_INPUT_FILE = 'temp_input.txt' 

def setup_directories():
    """Ensure the necessary folders exist and clear the output folder."""
    try:
        os.makedirs(INPUT_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Clear output folder contents to prevent old files from interfering
        for filename in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                st.warning(f'Failed to delete {file_path}. Reason: {e}')

    except Exception as e:
        st.error(f"Failed to set up directories: {e}")

def check_lexicon():
    """Check if the lexicon file is present."""
    if not os.path.exists(LEXICON_FILE):
        st.error(f"🚨 **Lexicon Missing:** Please ensure '{LEXICON_FILE}' is in the same directory as this script.")
        return False
    return True

def run_perl_pipeline(input_text: str) -> str | None:
    """
    Executes the two-step Perl pipeline: Clitic Separation (File-based) 
    followed by Tokenization (STDIN/STDOUT-based).
    """
    input_file_path = os.path.join(INPUT_DIR, TEMP_INPUT_FILE)
    output_file_path = os.path.join(OUTPUT_DIR, TEMP_INPUT_FILE)
    
    # --- 1. Pass data to the Clitic Script (File-based input) ---
    try:
        # Write user input to a temporary file
        with open(input_file_path, 'w', encoding='utf-8') as f:
            f.write(input_text)
    except Exception as e:
        st.error(f"Error writing temporary input file: {e}")
        return None

    # --- Step 1: Run Clitic Separation Script (separate-clitic.pl) ---
    st.info(f"Step 1: Running Clitic Separation ({CLITIC_SCRIPT})...")
    try:
        subprocess.run(
            ['perl', CLITIC_SCRIPT], 
            check=True, # Raise exception on non-zero exit code
            capture_output=True, 
            text=True,
            encoding='utf-8',
            timeout=10 # Set a timeout
        )
    except subprocess.CalledProcessError as e:
        st.error(f"❌ **Perl Error (Clitic):** Check Perl dependencies (like HTML::Parser) or file paths.")
        st.code(e.stderr, language='text')
        return None
    except FileNotFoundError:
        st.error(f"❌ **File Missing:** Perl interpreter or '{CLITIC_SCRIPT}' not found.")
        return None
    except subprocess.TimeoutExpired:
        st.error(f"❌ **Timeout:** {CLITIC_SCRIPT} took too long to execute.")
        return None

    # 2. Read the output of the clitic script
    if not os.path.exists(output_file_path):
        st.error(f"❌ Clitic output file not found: {output_file_path}. Check the Perl script's file handling logic.")
        return None
        
    try:
        with open(output_file_path, 'r', encoding='utf-8') as f:
            clitic_output = f.read()
    except Exception as e:
        st.error(f"Error reading output from {OUTPUT_DIR}: {e}")
        return None

    # --- Step 2: Run TreeTagger Tokenization Script (tokenize.pl) ---
    # This script reads from STDIN and prints to STDOUT, one token per line.
    st.info(f"Step 2: Running TreeTagger Tokenization ({TOKENIZE_SCRIPT})...")
    try:
        # Pass the output of Step 1 to the STDIN of Step 2
        process = subprocess.run(
            ['perl', TOKENIZE_SCRIPT, '-u'], # -u enables UTF8 support
            input=clitic_output,
            check=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            timeout=10
        )
        return process.stdout.strip()

    except subprocess.CalledProcessError as e:
        st.error(f"❌ **Perl Error (Tokenize):** Error in {TOKENIZE_SCRIPT}.")
        st.code(e.stderr, language='text')
        return None
    except FileNotFoundError:
        st.error(f"❌ **File Missing:** Perl interpreter or '{TOKENIZE_SCRIPT}' not found.")
        return None
    except subprocess.TimeoutExpired:
        st.error(f"❌ **Timeout:** {TOKENIZE_SCRIPT} took too long to execute.")
        return None


# --- Main Streamlit Application ---

def main():
    st.title("🇮🇩 Full Indonesian Tokenizer (Perl Pipeline)")
    st.markdown("---")

    setup_directories()
    if not check_lexicon():
        return

    st.header("1. Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-buku nya ada di U.S.A. Kulihat rumahmu (yang) besar!",
        height=150
    )
    
    if st.button("Run Full Perl Pipeline", type="primary"):
        if user_input.strip():
            
            with st.spinner('Processing...'):
                final_output = run_perl_pipeline(user_input)

            if final_output:
                st.header("2. Final Tokenization Output")
                st.markdown("This output is the result of the two-stage Perl pipeline (Clitics then TreeTagger-style tokenization).")
                
                # The output is already one token per line
                st.code(final_output, language='text')
                
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()
