import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set
from pathlib import Path
# Removed: import treetaggerwrapper 

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'

# --- 1. Pure Python Tokenization Logic (Stable) ---

# Characters that should be cut off/separated at the beginning of a word
P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"
# characters which have to be cut off at the end of a word
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

def tree_tagger_split(text_segment: str, lexicon_words: Set[str]) -> List[str]:
    """Applies core tokenization logic based on TreeTagger's tokenize.pl."""
    tokens = []
    temp_text = ' ' + text_segment + ' '
    
    # Punctuation spacing
    temp_text = re.sub(r'(\.\.\.)', r' \1 ', temp_text)
    temp_text = re.sub(r'([;\!\?])([^\s])', r'\1 \2', temp_text)
    temp_text = re.sub(r'([.,:])(?![A-Z])([^\s0-9.])', r'\1 \2', temp_text)
    
    words = temp_text.split()
    
    for word in words:
        current_word = word
        suffix = []
        while True:
            finished = True
            
            # Cut off preceding punctuation
            match_p = re.match(r"^(" + P_CHAR + r")(.+)$", current_word)
            if match_p:
                tokens.append(match_p.group(1))
                current_word = match_p.group(2)
                finished = False
            
            # Cut off trailing punctuation
            match_f = re.match(r"^(.+)(" + F_CHAR + r")$", current_word)
            if match_f:
                suffix.insert(0, match_f.group(2))
                current_word = match_f.group(1)
                finished = False
                
            if finished:
                break
        
        # Abbreviation and Period Disambiguation
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

        # Clitic separation
        tokens.append(process_word(current_word, lexicon_words))
        tokens.extend(suffix)

    return tokens

# --- Helper Logic Functions (Clitic and HTML) ---

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
    """Implements clitic separation based on lexicon lookup."""
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

# Removed: @st.cache_data / check_treetagger_installation()

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
    st.title("🇮🇩 Indonesian Tokeniser (Pure Python)")
    st.markdown("---")
    # Removed: System check header

    st.header("1. Tokenization Module")
    
    st.subheader("Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-buku nya ada di U.S.A. Kulihat rumahmu (yang) besar!",
        height=150
    )
    
    lexicon_set = read_lexicon(LEXICON_FILENAME)
    
    if st.button("Run Tokenization", type="primary"):
        
        if not lexicon_set:
            st.error("❌ **Cannot run tokenization:** The required lexicon file failed to load.")
            return
            
        if user_input.strip():
            
            parser = TokenisingHTMLParser(lexicon_set)
            parser.feed(user_input)
            
            final_processed_text = parser.get_tokenized_output()
            
            st.header("2. Tokenization Output")
            st.markdown("Output demonstrates: Clitic separation, Punctuation separation, and Abbreviation handling.")
            
            st.subheader("Tokens (Space Separated)")
            st.code(final_processed_text, language='text')
            
            final_tokens = final_processed_text.split()
            st.subheader("Token List (One Token Per Line)")
            st.code('\n'.join(final_tokens), language='text')
            
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()
