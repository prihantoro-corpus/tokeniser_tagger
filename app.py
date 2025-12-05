import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'
EXCEPTION_FILENAME = 'exception.txt' 

# --- 1. TreeTagger Tokenization Logic (Perl Equivalent) ---

# Characters that should be cut off/separated at the beginning of a word
P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"

# Characters that should be cut off/separated at the end of a word
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

def tree_tagger_split(text_segment: str, lexicon_words: Set[str], exception_words: Set[str]) -> List[str]:
    """
    Applies the full tokenization rules with the requested 3-layer precedence:
    1. Exception List Check (Highest Priority)
    2. Abbreviation Regex Check
    3. General Tokenization
    """
    tokens = []
    
    # 0. Initial cleanup and whitespace standardization
    temp_text = ' ' + text_segment + ' '
    temp_text = re.sub(r'(\.\.\.)', r' \1 ', temp_text)
    temp_text = re.sub(r'([;\!\?])([^\s])', r'\1 \2', temp_text)
    temp_text = re.sub(r'([.,:])([^\s0-9.])', r'\1 \2', temp_text)
    
    words = temp_text.split()
    
    for word in words:
        current_word = word
        suffix = []
        
        # --- PRECEDENCE CHECK 1: Exception List ---
        # Checks if the word, *after* initial spacing rules, is a defined exception.
        if current_word in exception_words:
            tokens.append(current_word)
            continue
            
        # --- PRECEDENCE CHECK 2: Abbreviation Regex ---
        # This check is crucial and happens *before* punctuation stripping.
        # Catches patterns like A. or U.S.A. (must end with a period).
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            # If it matches, treat it as a single token and skip splitting.
            tokens.append(current_word)
            continue
        
        # --- GENERAL TOKENIZATION (If 1 & 2 failed) ---
        
        # 1. Strip external punctuation (do...while equivalent)
        while True:
            finished = True
            
            # Cut off preceding punctuation ($PChar)
            match_p = re.match(r"^(" + P_CHAR + r")(.+)$", current_word)
            if match_p:
                tokens.append(match_p.group(1)) 
                current_word = match_p.group(2)
                finished = False

            # Cut off trailing punctuation ($FChar)
            match_f = re.match(r"^(.+)(" + F_CHAR + r")$", current_word)
            if match_f:
                suffix.insert(0, match_f.group(2)) 
                current_word = match_f.group(1)
                finished = False
            
            if finished:
                break
        
        # 2. Re-check Exception list after stripping surrounding punctuation
        # (e.g., if input was "(U.S.A.)", U.S.A. remains one token)
        if current_word in exception_words:
            tokens.append(current_word)
            tokens.extend(suffix)
            continue
            
        # 3. Disambiguate periods (The general period separation logic)
        # If word ends with '.' AND is not '...' and not a number, separate the period.
        if current_word.endswith('.') and current_word != '...' and not re.match(r"^[0-9]+\.$", current_word):
            root = current_word[:-1]
            period = '.'
            
            # Apply clitic separation (lexicon check) to the root word
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


# --- 3. Core Logic Functions (Clitic Separator) ---

def preprocess_text(text: str) -> str:
    # (Implementation remains the same)
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word(word: str, lexicon_words: Set[str]) -> str:
    # (Implementation remains the same, adjusted for no punctuation handling)
    original_word = word
    word_without_punct = word
    
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

# --- 4. HTML/Text Processing Class ---

class TokenisingHTMLParser(HTMLParser):
    # (Implementation remains the same, passing exception_words)
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
        
        # Pass both lexicon and exception sets to the tokenization function
        new_tokens = tree_tagger_split(text, self.lexicon_words, self.exception_words)
        self.processed_tokens.extend(new_tokens)
    
    def get_tokenized_output(self) -> str:
        return " ".join(self.processed_tokens)

# --- 5. Main Streamlit Application Function ---

def main():
    st.title("🇮🇩 Indonesian Tokeniser (TreeTagger Style)")
    st.markdown("---")

    # Load both files
    lexicon_set = read_lexicon(LEXICON_FILENAME)
    exception_set = read_exceptions(EXCEPTION_FILENAME)
    
    if not lexicon_set:
        st.warning("Application halted: Lexicon is required.")
        return

    st.header("1. Input Text")
    
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Buku-buku nya ada di U.S.A. Kulihat rumahmu (yang) besar!",
        height=150
    )
    
    if st.button("Run Full Tokenization", type="primary"):
        if user_input.strip():
            parser = TokenisingHTMLParser(lexicon_set, exception_set)
            parser.feed(user_input)
            
            final_processed_text = parser.get_tokenized_output()
            
            st.header("2. Tokenization Output")
            st.markdown("This output follows 3-layer precedence:")
            st.markdown("* **1st:** Exact match in `exception.txt` (e.g., `U.S.A.`)")
            st.markdown("* **2nd:** General abbreviation pattern match (`A.B.C.`)")
            st.markdown("* **3rd:** Punctuation splitting, then Clitic separation.")
            
            st.code(final_processed_text, language='text')
            
            final_tokens = final_processed_text.split()
            st.subheader("Token List (One Token Per Line)")
            st.code('\n'.join(final_tokens), language='text')
            
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()
