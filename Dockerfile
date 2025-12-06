import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set
from pathlib import Path
import treetaggerwrapper # REQUIRED for installation test

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
    # (using negative lookahead: (?![A-Z])) to protect abbreviations.
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
        # Check for abbreviations of the form A. or U.S.A. (not split)
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            tokens.append(process_word(current_word, lexicon_words))
            tokens.extend(suffix)
            continue
            
        # Disambiguate periods: if word ends with '.' AND is not '...' and not a number
        if current_word.endswith('.') and current_word != '...' and not re.match(r"^[0-9]+\.$", current_word):
            root = current_word[:-1]
            period = '.'
            
            # Apply clitic separation (lexicon check) to the root word
            tokens.append(process_word(root, lexicon_words))
            tokens.append(period)
            tokens.extend(suffix)
            continue

        # 5. Apply Indonesian Clitic Separator and add tokens
        tokens.append(process_word(current_word, lexicon_words))
        tokens.extend(suffix)

    return tokens

# --- 2. HTML/Text Processing Class ---

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
        
        # Split by whitespace to process individual segments
        segments = re.split(r'(\s+)', text)
        
        for segment in segments:
            if not segment or segment.isspace():
                continue
            
            # Apply the full TreeTagger tokenization to each segment
            new_tokens = tree_tagger_split(segment, self.lexicon_words)
            self.processed_tokens.extend(new_tokens)
    
    def get_tokenized_output(self) -> str:
        return " ".join(self.processed_tokens)


# --- 3. Core Logic Functions (Clitic Separator) ---

def preprocess_text(text: str) -> str:
    """Handles quotes and the prefix 'ku' as separate words."""
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word(word: str, lexicon_words: Set[str]) -> str:
    """
    Applies the lexicon-based clitic separation ('nya', 'mu', 'ku', 'ku-').
    """
    original_word = word
    word_without_punct = re.sub(r"[!?.,'\"()\[\]{}:;.../\\~_-]$", "", word)
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    # 1. Check if the full word is in the lexicon (no split if it is)
    if lower_word in lexicon_words:
        return original_word

    # 2. Check for clitic suffixes ('nya', 'mu', 'ku')
    clitics = {'nya': 3, 'mu': 2, 'ku': 2}
    for clitic, length in clitics.items():
        if lower_word.endswith(clitic):
            root_word = word_without_punct[:-length]
            if root_word.lower() in lexicon_words:
                return f"{root_word} -{clitic}" 
    
    # 3. Check for 'ku' prefix
    if lower_word.startswith('ku') and len(word_without_punct) > 2:
        root_word = word_without_punct[2:]
        if root_word.lower() in lexicon_words:
            return f"ku- {root_word}"
            
    # Return the word as is
    return original_word

# --- 4. Main Streamlit Application Functions ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    """Loads the lexicon file for clitic checks using a robust path (FIXED)."""
    lexicon_words = set()
    try:
        # FIX: Use pathlib to reliably find the path relative to the currently executing script
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


def test_treetagger_installation():
    """
    Attempts to initialize the TreeTagger wrapper to verify installation.
    This function should be REMOVED once successful.
    """
    st.header("TreeTagger Installation Test")
    try:
        # Initializes the tagger for English, as 'en' files were installed in the Dockerfile.
        tagger = treetaggerwrapper.TreeTagger(TAGLANG='en')
        st.success("✅ TreeTagger and wrapper installed successfully!")
        st.write("Initialization successful for language **'en'**.")
        
        # Run a minimal test to confirm the binary executes
        st.subheader("Minimal Tagging Test")
        test_text = "This is a brief test."
        tags = tagger.tag_text(test_text)
        
        st.markdown(f"Input: `{test_text}`")
        st.code('\n'.join(tags), language='text')

    except Exception as e:
        st.error("❌ TreeTagger installation failed or is not found.")
        st.warning("Check your Dockerfile, requirements.txt, and remote deployment logs.")
        st.exception(e)


def main():
    st.title("🇮🇩 Indonesian Tokeniser (Pure Python)")
    st.markdown("---")

    # CALL THE TEST FUNCTION HERE
    test_treetagger_installation() 
    st.markdown("---") 

    lexicon_set = read_lexicon(LEXICON_FILENAME)
    
    if not lexicon_set:
        st.warning("Application requires the lexicon to run. Please check file path and content.")
        return

    st.header("1. Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-buku nya ada di U.S.A. Kulihat rumahmu (yang) besar!",
        height=150
    )
    
    if st.button("Run Full Tokenization", type="primary"):
        if user_input.strip():
            
            parser = TokenisingHTMLParser(lexicon_set)
            parser.feed(user_input)
            
            final_processed_text = parser.get_tokenized_output()
            
            st.header("2. Tokenization Output")
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
