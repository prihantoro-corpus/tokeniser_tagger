import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set
from pathlib import Path
import treetaggerwrapper 

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'

# --- 1. TreeTagger Tokenization Logic (Pure Python Implementation) ---

# Characters that should be cut off/separated at the beginning of a word
P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"
# characters which have to be cut off at the end of a word
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

def tree_tagger_split(text_segment: str, lexicon_words: Set[str]) -> List[str]:
    # ... (Tokenization logic remains the same) ...
    tokens = []
    temp_text = ' ' + text_segment + ' '
    temp_text = re.sub(r'(\.\.\.)', r' \1 ', temp_text)
    temp_text = re.sub(r'([;\!\?])([^\s])', r'\1 \2', temp_text)
    temp_text = re.sub(r'([.,:])(?![A-Z])([^\s0-9.])', r'\1 \2', temp_text)
    words = temp_text.split()
    
    for word in words:
        current_word = word
        suffix = []
        while True:
            finished = True
            match_p = re.match(r"^(" + P_CHAR + r")(.+)$", current_word)
            if match_p:
                tokens.append(match_p.group(1))
                current_word = match_p.group(2)
                finished = False
            match_f = re.match(r"^(.+)(" + F_CHAR + r")$", current_word)
            if match_f:
                suffix.insert(0, match_f.group(2))
                current_word = match_f.group(1)
                finished = False
            if finished:
                break
        
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            tokens.append(process_word(current_word, lexicon_words))
            tokens.extend(suffix)
            continue
            
        if current_word.endswith('.') and current_word != '...' and not re.match(r"^[0-9]+\.$", current_word):
            root = current_word[:-1]
            period = '.'
            tokens.append(process_word(root, lexicon_words))
            tokens.append(period)
            tokens.extend(suffix)
            continue

        tokens.append(process_word(current_word, lexicon_words))
        tokens.extend(suffix)

    return tokens

# --- 2. HTML/Text Processing Class & Core Logic Functions ---

class TokenisingHTMLParser(HTMLParser):
    def __init__(self, lexicon_words, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lexicon_words = lexicon_words
        self.processed_tokens = [] 

    def handle_starttag(self, tag, attrs):
        attr_str = "".join([f' {key}="{value}"' for key, value in attrs])
        complete_tag = f"<{tag}{attr_str}>"
        self.processed_tokens.append(complete_tag)

    def handle_endtag(self, tag):
        complete_tag = f"</{tag}>"
        self.processed_tokens.append(complete_tag)

    def handle_data(self, data):
        text = preprocess_text(data)
        segments = re.split(r'(\s+)', text)
        for segment in segments:
            if not segment or segment.isspace():
                continue
            new_tokens = tree_tagger_split(segment, self.lexicon_words)
            self.processed_tokens.extend(new_tokens)
    
    def get_tokenized_output(self) -> str:
        return " ".join(self.processed_tokens)

def preprocess_text(text: str) -> str:
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word(word: str, lexicon_words: Set[str]) -> str:
    original_word = word
    word_without_punct = re.sub(r"[!?.,'\"()\[\]{}:;.../\\~_-]$", "", word)
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    if lower_word in lexicon_words:
        return original_word

    clitics = {'nya': 3, 'mu': 2, 'ku': 2}
    for clitic, length in clitics.items():
        if lower_word.endswith(clitic):
            root_word = word_without_punct[:-length]
            if root_word.lower() in lexicon_words:
                return f"{root_word} -{clitic}" 
    
    if lower_word.startswith('ku') and len(word_without_punct) > 2:
        root_word = word_without_punct[2:]
        if root_word.lower() in lexicon_words:
            return f"ku- {root_word}"
            
    return original_word

# --- 3. TreeTagger Installation Check Function (CRITICAL FIX) ---

@st.cache_data
def check_treetagger_installation():
    """
    Attempts to initialize the TreeTagger wrapper by explicitly passing TAGDIR.
    """
    st.subheader("TreeTagger Installation Check Results:")
    
    # CRITICAL FIX: Explicitly get TAGDIR from the Docker environment.
    tag_dir = os.environ.get('TAGDIR', '/usr/local/treetagger') 
    
    try:
        tagger = treetaggerwrapper.TreeTagger(
            TAGLANG='en', 
            TAGDIR=tag_dir
        )
        
        st.success("✅ **SUCCESS!** TreeTagger and wrapper installed successfully!")
        st.markdown(f"The tagger was initialized using binary path: `{tag_dir}`")
        
        st.subheader("Minimal Tagging Output:")
        test_text = "This is a brief test."
        tags = tagger.tag_text(test_text)
        
        st.markdown(f"Input: `{test_text}`")
        st.code('\n'.join(tags), language='text')

    except Exception as e:
        st.error("❌ **FAILURE!** TreeTagger installation failed or the binary was not found.")
        st.markdown(f"The wrapper failed to initialize. Attempted binary path: `{tag_dir}`")
        st.markdown("---")
        st.subheader("Last Known Error:")
        st.code(str(e))
        st.markdown("Please verify your `Dockerfile` ensures the TreeTagger binary is available at the path above.")

# --- 4. Main Streamlit Application Function ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    """Loads the lexicon file for clitic checks using a robust path."""
    lexicon_words = set()
    try:
        script_path = Path(__file__).resolve()
        file_path = script_path.parent / lexicon_file
        
        if not file_path.exists():
            st.error(f"❌ Lexicon file '{LEXICON_FILENAME}' not found. Searched at: {file_path}")
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

    # AUTO-CHECK: Call the test function immediately upon load
    st.header("1. System Check")
    check_treetagger_installation() 
    st.markdown("---") 

    st.header("2. Tokenization Module (Pure Python)")
    
    # --- UI Elements (Must be rendered regardless of lexicon status) ---
    st.subheader("Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-buku nya ada di U.S.A. Kulihat rumahmu (yang) besar!",
        height=150
    )
    
    # --- Get Lexicon (Now placed before the button check for clarity) ---
    lexicon_set = read_lexicon(LEXICON_FILENAME)
    
    # Check if the button was pressed
    if st.button("Run Tokenization", type="primary"):
        
        # --- Processing Logic (Only runs if lexicon and input are valid) ---
        if not lexicon_set:
            st.error("❌ **Cannot run tokenization:** The required lexicon file failed to load.")
            return # Stop processing if the lexicon is missing
            
        if user_input.strip():
            
            parser = TokenisingHTMLParser(lexicon_set)
            parser.feed(user_input)
            
            final_processed_text = parser.get_tokenized_output()
            
            st.header("3. Tokenization Output")
            st.markdown("Output demonstrates: Clitic separation, Punctuation separation, and Abbreviation handling.")
            
            # Display tokens joined by a space
            st.subheader("Tokens (Space Separated)")
            st.code(final_processed_text, language='text')
            
            # Display tokens vertically (TreeTagger standard format)
            final_tokens = final_processed_text.split()
            st.subheader("Token List (One Token Per Line)")
            st.code('\n'.join(final_tokens), language='text')
            
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()
