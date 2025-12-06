import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set
from pathlib import Path
import treetaggerwrapper # Keep this import

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'

# --- 1. TreeTagger Tokenization Logic (Pure Python Implementation) ---

# Characters that should be cut off/separated at the beginning of a word
P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"

# Characters that should be cut off/separated at the end of a word
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

def tree_tagger_split(text_segment: str, lexicon_words: Set[str]) -> List[str]:
    """
    Applies the core TreeTagger-style tokenization and punctuation separation.
    (Contains the fix for U.S.A. splitting)
    """
    tokens = []
    
    # Add temporary space padding
    temp_text = ' ' + text_segment + ' '
    
    # --- Punctuation Spacing (FIXED for Abbreviations) ---
    
    # 1. Triple-dot separation
    temp_text = re.sub(r'(\.\.\.)', r' \1 ', temp_text)
    
    # 2. Punctuation like ;, !, ? separated from the next non-space character
    temp_text = re.sub(r'([;\!\?])([^\s])', r'\1 \2', temp_text)
    
    # 3. FIX for U.S.A.: Only separate [.,:] if the following character is NOT an uppercase letter 
    temp_text = re.sub(r'([.,:])(?![A-Z])([^\s0-9.])', r'\1 \2', temp_text)
    
    # Split by any whitespace
    words = temp_text.split()
    
    for word in words:
        current_word = word
        suffix = []
        
        while True:
            finished = True
            
            # 1. Cut off preceding punctuation ($PChar)
            match_p = re.match(r"^(" + P_CHAR + r")(.+)$", current_word)
            if match_p:
                tokens.append(match_p.group(1)) # Punctuation token
                current_word = match_p.group(2)
                finished = False

            # 2. Cut off trailing punctuation ($FChar)
            match_f = re.match(r"^(.+)(" + F_CHAR + r")$", current_word)
            if match_f:
                suffix.insert(0, match_f.group(2)) # Punctuation token
                current_word = match_f.group(1)
                finished = False
                
            if finished:
                break
        
        # 4. Abbreviation and Period Disambiguation
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            tokens.append(process_word(current_word, lexicon_words))
            tokens.extend(suffix)
            continue
            
        # Disambiguate periods: if word ends with '.' AND is not '...' and not a number
        if current_word.endswith('.') and current_word != '...' and not re.match(r"^[0-9]+\.$", current_word):
            root = current_word[:-1]
            period = '.'
            
            tokens.append(process_word(root, lexicon_words))
            tokens.append(period)
            tokens.extend(suffix)
            continue

        # 5. Apply Indonesian Clitic Separator and add tokens
        tokens.append(process_word(current_word, lexicon_words))
        tokens.extend(suffix)

    return tokens

# --- 2. HTML/Text Processing Class & Core Logic Functions ---
# (Omitted for brevity in this response, but assumed to be present in the final script)

# --- 3. TreeTagger Installation Test Function ---

def check_treetagger_installation():
    """
    Attempts to initialize the TreeTagger wrapper and reports the status.
    """
    st.subheader("TreeTagger Installation Check Results:")
    try:
        # Tagger for English, as 'en' files were installed in the Dockerfile.
        tagger = treetaggerwrapper.TreeTagger(TAGLANG='en')
        
        st.success("✅ **SUCCESS!** TreeTagger and wrapper installed successfully!")
        st.markdown("The wrapper successfully initialized and found the TreeTagger binary for language 'en'.")

        # Run a minimal test to confirm the binary executes
        st.subheader("Minimal Tagging Output:")
        test_text = "This is a brief test."
        tags = tagger.tag_text(test_text)
        
        st.markdown(f"Input: `{test_text}`")
        st.code('\n'.join(tags), language='text')
        st.info("You can now proceed with your main application logic.")

    except Exception as e:
        st.error("❌ **FAILURE!** TreeTagger installation failed or the binary was not found.")
        st.markdown("The `treetaggerwrapper` could not initialize the external program.")
        st.markdown("---")
        st.subheader("Troubleshooting Steps:")
        st.markdown(
            """
            1.  **Check `requirements.txt`:** Ensure `treetaggerwrapper` is listed.
            2.  **Check `Dockerfile`:** Verify that `wget`, `unzip`, and `perl` are installed, the TreeTagger binary is downloaded and extracted, and the environment variable `TAGDIR` is set to `/usr/local/treetagger`.
            3.  **Check Deployment Logs:** Review the logs on your hosting platform for errors during the Docker build process.
            """
        )
        # st.exception(e) # Optionally show the full traceback for advanced debugging

# --- 4. Main Streamlit Application Function ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    # (Lexicon reading logic remains the same for brevity)
    lexicon_words = set()
    try:
        script_path = Path(__file__).resolve()
        file_path = script_path.parent / lexicon_file
        
        if not file_path.exists():
            st.error(f"❌ Lexicon file '{LEXICON_FILENAME}' not found.")
            return set()
            
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().lower()
                if word:
                    lexicon_words.add(word)
        
        st.sidebar.success(f"✅ Lexicon loaded: {len(lexicon_words)} words.")
        return lexicon_words
        
    except Exception as e:
        st.sidebar.error(f"❌ Error loading lexicon: {e}")
        return set()

def main():
    st.title("🇮🇩 Indonesian Tokeniser (TreeTagger/Python Hybrid)")
    st.markdown("---")

    st.header("1. System Check")
    # Button to trigger the installation check
    if st.button("Check Tagger Installation", type="primary"):
        check_treetagger_installation()
    
    st.markdown("---")

    st.header("2. Tokenization Module (Pure Python)")
    lexicon_set = read_lexicon(LEXICON_FILENAME)
    
    if not lexicon_set:
        st.warning("Application requires the lexicon to run. Please check file path and content.")
        return

    st.subheader("Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-buku nya ada di U.S.A. Kulihat rumahmu (yang) besar!",
        height=150
    )
    
    if st.button("Run Tokenization"):
        if user_input.strip():
            # ... (HTML parsing and tokenization logic)
            # This part requires the other helper functions (omitted here for space)
            # You must ensure the original process_word and HTML parser logic are present.
            
            # Placeholder code for running the actual process:
            st.warning("Ensure the full `TokenisingHTMLParser` and `process_word` functions are present here.")
            # parser = TokenisingHTMLParser(lexicon_set)
            # parser.feed(user_input)
            # final_processed_text = parser.get_tokenized_output()
            # st.code(final_processed_text, language='text')

if __name__ == "__main__":
    # Ensure all missing helper functions (TokenisingHTMLParser, process_word, etc.)
    # are present in the full script file you use for deployment.
    main()
