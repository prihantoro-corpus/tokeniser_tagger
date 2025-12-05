import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'
EXCEPTION_FILENAME = 'exception.txt' 

# --- 1. TreeTagger Tokenization Logic (Finalized) ---

P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

def tree_tagger_split(text_segment: str, lexicon_words: Set[str], exception_words: Set[str]) -> List[str]:
    """
    Applies the full tokenization rules with absolute priority for Exceptions 
    and Abbreviation Patterns, preventing general punctuation stripping from 
    breaking these high-priority tokens.
    """
    tokens = []
    
    # Initial cleanup and whitespace standardization
    temp_text = ' ' + text_segment + ' '
    temp_text = re.sub(r'(\.\.\.)', r' \1 ', temp_text)
    temp_text = re.sub(r'([;\!\?])([^\s])', r'\1 \2', temp_text)
    temp_text = re.sub(r'([.,:])([^\s0-9.])', r'\1 \2', temp_text)
    
    words = temp_text.split()
    
    for word in words:
        current_word = word
        suffix = []
        
        # -------------------------------------------------------------
        # --- ABSOLUTE PRIORITY CHECKS (If matched, skip splitting) ---
        # -------------------------------------------------------------
        
        # --- PRIORITY 1: Exception List (Exact Match) ---
        if current_word in exception_words:
            tokens.append(current_word)
            continue 
            
        # --- PRIORITY 2: Abbreviation Regex (Pattern Match) ---
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            tokens.append(current_word)
            continue 
            
        # --- PRIORITY 3: Hyphenated Compound Words (Indonesian) ---
        if '-' in current_word and not re.match(r"^[A-Za-z]+-[nya|mu|ku]$", current_word.lower()):
            tokens.append(current_word)
            continue 

        # -------------------------------------------------------------
        # --- SPLITTING AND DISAMBIGUATION (Default Logic) ---
        # -------------------------------------------------------------
        
        # 1. Strip external punctuation (do...while equivalent)
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
        
        # 2. Re-check Exception list after stripping surrounding punctuation
        if current_word in exception_words:
            tokens.append(current_word)
            tokens.extend(suffix)
            continue
            
        # 3. Disambiguate periods
        if current_word.endswith('.') and current_word != '...' and not re.match(r"^[0-9]+\.$", current_word):
            root = current_word[:-1]
            period = '.'
            
            tokens.append(process_word(root, lexicon_words))
            tokens.append(period)
            tokens.extend(suffix)
            continue

        # 4. Apply Indonesian Clitic Separator and add tokens
        tokens.append(process_word(current_word, lexicon_words))
        tokens.extend(suffix)

    return tokens

# --- 2. File Loading Functions ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    # (Implementation remains the same)
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

@st.cache_resource 
def read_exceptions(exception_file: str) -> Set[str]:
    # (Implementation remains the same)
    exception_words = set()
    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, exception_file)
        
        if not os.path.exists(file_path):
             st.warning(f"❗ Exception file not found at: {file_path}. Proceeding without exceptions.")
             return set()
             
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip() 
                if word:
                    exception_words.add(word)
        
        st.sidebar.success(f"✅ Exceptions loaded: {len(exception_words)} phrases.")
        return exception_words
        
    except Exception as e:
        st.sidebar.error(f"❌ Error loading exceptions: {e}")
        return set()


# --- 3. Core Logic Functions (Clitic Separator - Case-Insensitive Fix) ---

def preprocess_text(text: str) -> str:
    # (Implementation remains the same)
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word(word: str, lexicon_words: Set[str]) -> str:
    """
    Applies clitic separation using case-insensitive checks against the lexicon.
    """
    original_word = word
    word_without_punct = word 
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    # 1. Handle isolated clitics (e.g., 'nya' as a separate word)
    if lower_word == 'nya':
        return '-nya'
    if lower_word == 'mu':
        return '-mu'

    # Check if the full word is in the lexicon (no split if it is)
    if lower_word in lexicon_words:
        return original_word

    # Check for clitic suffixes ('nya', 'mu', 'ku')
    clitics = {'nya': 3, 'mu': 2, 'ku': 2}
    for clitic, length in clitics.items():
        # Check for suffix using the lowercase word
        if lower_word.endswith(clitic):
            # Extract the root word, preserving the original casing
            root_word = word_without_punct[:-length]
            
            # Check the lowercase root word against the lexicon
            if root_word.lower() in lexicon_words:
                # The word is a valid root + clitic. Return split form.
                return f"{root_word} -{clitic}" 
    
    # Check for 'ku' prefix
    if lower_word.startswith('ku') and len(word_without_punct) > 2:
        # Check for prefix using the lowercase word
        if lower_word.startswith('ku'):
            root_word = word_without_punct[2:]
            
            # Check the lowercase root word against the lexicon
            if root_word.lower() in lexicon_words:
                # Preserve the original capitalization of 'Ku' or 'ku'
                prefix = original_word[:2] 
                return f"{prefix}- {root_word}"
            
    return original_word

# --- 4. HTML/Text Processing Class ---

class TokenisingHTMLParser(HTMLParser):
    def __init__(self, lexicon_words, exception_words, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lexicon_words = lexicon_words
        self.exception_words = exception_words
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
        
        new_tokens = tree_tagger_split(text, self.lexicon_words, self.exception_words)
        self.processed_tokens.extend(new_tokens)
    
    def get_tokenized_output(self) -> str:
        return " ".join(self.processed_tokens)

# --- 5. Main Streamlit Application Function ---

def main():
    st.title("🇮🇩 Indonesian Tokeniser (TreeTagger Style)")
    st.markdown("---")

    lexicon_set = read_lexicon(LEXICON_FILENAME)
    exception_set = read_exceptions(EXCEPTION_FILENAME)
    
    if not lexicon_set:
        st.warning("Application halted: Lexicon is required.")
        return

    st.header("1. Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-bukunya ada di U.S.A. Kulihat rumahmu (yang) besar!",
        height=150
    )
    
    if st.button("Run Full Tokenization", type="primary"):
        if user_input.strip():
            parser = TokenisingHTMLParser(lexicon_set, exception_set)
            parser.feed(user_input)
            
            final_processed_text = parser.get_tokenized_output()
            
            st.header("2. Tokenization Output")
            st.markdown("This version uses **Case-Insensitive Clitic Logic** and **Absolute Priority** for Exceptions.")
            
            st.code(final_processed_text, language='text')
            
            final_tokens = final_processed_text.split()
            st.subheader("Token List (One Token Per Line)")
            st.code('\n'.join(final_tokens), language='text')
            
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()
