import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'
# EXCEPTION_FILENAME is removed as we are reverting the complexity

# --- 1. Core Logic Functions (Clitic Separator - Finalized) ---

def preprocess_text(text: str) -> str:
    """Handles quotes and the prefix 'ku' as separate words."""
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word(word: str, lexicon_words: Set[str]) -> str:
    """
    Applies clitic separation using case-insensitive checks against the lexicon,
    preserving original case.
    """
    original_word = word
    
    # 1. Save and remove end punctuation (Required for basic tokenization)
    punctuation_match = re.search(r"([!?.,'\"()\[\]{}:;.../\\~_-])$", word)
    punctuation = punctuation_match.group(1) if punctuation_match else ""
    word_without_punct = re.sub(r"[!?.,'\"()\[\]{}:;.../\\~_-]$", "", word)
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    # 2. Handle isolated clitics (e.g., 'nya' as a separate word)
    if lower_word == 'nya':
        return f"-nya {punctuation}".strip()
    if lower_word == 'mu':
        return f"-mu {punctuation}".strip()

    # 3. Check if the full word is in the lexicon (no split if it is)
    if lower_word in lexicon_words:
        return original_word

    # 4. Check for clitic suffixes ('nya', 'mu', 'ku')
    clitics = {'nya': 3, 'mu': 2, 'ku': 2}
    for clitic, length in clitics.items():
        # Check for suffix using the lowercase word
        if lower_word.endswith(clitic):
            # Extract the root word, preserving the original casing
            root_word = word_without_punct[:-length]
            
            # Check the lowercase root word against the lexicon
            if root_word.lower() in lexicon_words:
                return f"{root_word} -{clitic} {punctuation}".strip()
    
    # 5. Check for 'ku' prefix
    if lower_word.startswith('ku') and len(word_without_punct) > 2:
        # Check for prefix using the lowercase word
        root_word = word_without_punct[2:]
        
        # Check the lowercase root word against the lexicon
        if root_word.lower() in lexicon_words:
            # Preserve the original capitalization of 'Ku' or 'ku'
            prefix = original_word[:2] 
            return f"{prefix}- {root_word} {punctuation}".strip()
            
    # 6. If no condition is met, return the word as is
    return original_word

# --- 2. File Loading Function ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    """Reads the lexicon file, converts words to lowercase, and returns a set."""
    lexicon_words = set()
    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, lexicon_file)
        
        if not os.path.exists(file_path):
             st.error(f"❌ Lexicon file not found at: {file_path}")
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

# --- 3. HTML/Text Processing Class ---

class TokenisingHTMLParser(HTMLParser):
    """
    Parses text, correctly delimiting tags, and applying only clitic separation 
    to text content.
    """
    def __init__(self, lexicon_words, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lexicon_words = lexicon_words
        self.processed_text = ""

    def handle_starttag(self, tag, attrs):
        attr_str = "".join([f' {key}="{value}"' for key, value in attrs])
        complete_tag = f"<{tag}{attr_str}>"
        self.processed_text += f" {complete_tag} "

    def handle_endtag(self, tag):
        complete_tag = f"</{tag}>"
        self.processed_text += f" {complete_tag} "

    def handle_data(self, data):
        text = preprocess_text(data)
        
        # Split by space/newline while keeping the delimiters (whitespace)
        tokens = re.split(r'(\s+)', text)
        
        processed_tokens = []
        for token in tokens:
            if token and not token.isspace():
                # Apply only clitic separation and basic punctuation stripping
                processed_tokens.append(process_word(token, self.lexicon_words))
            else:
                # Keep whitespace as is
                processed_tokens.append(token)
                
        self.processed_text += "".join(processed_tokens)
    
    def get_tokenized_output(self) -> str:
        # Final output needs to remove redundant spaces created by tag handling
        return re.sub(r'\s+', ' ', self.processed_text.strip())

# --- 4. Main Streamlit Application Function ---

def main():
    st.title("🇮🇩 Indonesian Tokeniser (Clitic Separator ONLY)")
    st.markdown("---")

    lexicon_set = read_lexicon(LEXICON_FILENAME)
    
    if not lexicon_set:
        st.warning("Application halted: Lexicon is required.")
        return

    st.header("1. Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-bukunya Kulihat. Ini rumahmu.",
        height=150
    )
    
    if st.button("Run Clitic Tokenization", type="primary"):
        if user_input.strip():
            parser = TokenisingHTMLParser(lexicon_set)
            parser.feed(user_input)
            
            final_processed_text = parser.get_tokenized_output()
            
            st.header("2. Tokenization Output")
            st.markdown("This version only performs **Case-Insensitive Clitic Separation** (e.g., `Buku-buku -nya`) and basic punctuation stripping.")
            
            st.code(final_processed_text, language='text')
            
            final_tokens = final_processed_text.split()
            st.subheader("Token List (One Token Per Line)")
            st.code('\n'.join(final_tokens), language='text')
            
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()
