import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'
EXCEPTION_FILENAME = 'exception.txt' # Used for Abbreviation check in full tokenization

# --- 1. Pass 1: Clitic Separation Logic ---

def preprocess_text(text: str) -> str:
    """Handles quotes and the prefix 'ku' as separate words."""
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word_clitic(word: str, lexicon_words: Set[str]) -> str:
    """
    Applies clitic separation using case-insensitive checks against the lexicon,
    preserving original case and stripping simple end punctuation.
    """
    original_word = word
    
    # 1. Save and remove end punctuation (Required for basic tokenization)
    punctuation_match = re.search(r"([!?.,'\"()\[\]{}:;.../\\~_-])$", word)
    punctuation = punctuation_match.group(1) if punctuation_match else ""
    word_without_punct = re.sub(r"[!?.,'\"()\[\]{}:;.../\\~_-]$", "", word)
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    # Handle isolated clitics (e.g., 'nya' as a separate word)
    if lower_word == 'nya':
        return f"-nya {punctuation}".strip()
    if lower_word == 'mu':
        return f"-mu {punctuation}".strip()

    # Check if the full word is in the lexicon (no split if it is)
    if lower_word in lexicon_words:
        return original_word

    # Check for clitic suffixes ('nya', 'mu', 'ku')
    clitics = {'nya': 3, 'mu': 2, 'ku': 2}
    for clitic, length in clitics.items():
        if lower_word.endswith(clitic):
            root_word = word_without_punct[:-length]
            if root_word.lower() in lexicon_words:
                return f"{root_word} -{clitic} {punctuation}".strip()
    
    # Check for 'ku' prefix
    if lower_word.startswith('ku') and len(word_without_punct) > 2:
        root_word = word_without_punct[2:]
        if root_word.lower() in lexicon_words:
            prefix = original_word[:2] 
            return f"{prefix}- {root_word} {punctuation}".strip()
            
    return original_word

class CliticSeparatorParser(HTMLParser):
    """Parses text, preserves tags, and applies ONLY clitic separation."""
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
        tokens = re.split(r'(\s+)', text)
        
        processed_tokens = []
        for token in tokens:
            if token and not token.isspace():
                processed_tokens.append(process_word_clitic(token, self.lexicon_words))
            else:
                processed_tokens.append(token)
                
        self.processed_text += "".join(processed_tokens)
    
    def get_tokenized_output(self) -> str:
        # Clean up output spaces for smooth input into the next stage
        return re.sub(r'\s+', ' ', self.processed_text.strip())

# --- 2. Pass 2: Full TreeTagger Tokenization Logic ---

P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

def full_tokenization_pipeline(clitic_separated_text: str, exception_words: Set[str]) -> List[str]:
    """
    Applies the full TreeTagger tokenization rules (punctuation, abbreviation, period disambiguation)
    to the already clitic-separated text.
    """
    final_tokens = []
    
    # 1. Clean up potential extra spaces and treat clitics as single units
    # We rely on the clitic separator (e.g., 'rumah -nya') to keep the root and clitic separate.
    
    # 2. Prepare SGML/HTML Tags for tokenization (Perl: s/(<[^<>]*>)/\377$1\377/g)
    # Tags are already space-separated, but we need to ensure they are handled as single tokens.
    
    # 3. Process segments (tags vs. text)
    # The clitic separator already tokenized into a space-separated string.
    
    segments = clitic_separated_text.split() 
    
    for segment in segments:
        current_word = segment
        suffix = []
        
        # Check if it is a tag (already separated in Pass 1)
        if current_word.startswith('<') and current_word.endswith('>'):
            final_tokens.append(current_word)
            continue
            
        # --- ABSOLUTE PRIORITY CHECKS (Must win against stripping) ---
        
        # PRIORITY 1: Exception List (Exact Match)
        if current_word in exception_words:
            final_tokens.append(current_word)
            continue 
            
        # PRIORITY 2: Abbreviation Regex (Pattern Match)
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            final_tokens.append(current_word)
            continue 
            
        # PRIORITY 3: Hyphenated Compound Words (Already handled by clitic separation, 
        # but check again for safety, excluding clitics which contain a hyphen)
        if re.match(r"^[A-Za-z]+-[A-Za-z]+$", current_word):
            final_tokens.append(current_word)
            continue
        
        # -------------------------------------------------------------
        # --- SPLITTING AND DISAMBIGUATION (Default Logic) ---
        # -------------------------------------------------------------
        
        # 1. Strip external punctuation (do...while equivalent)
        while True:
            finished = True
            
            # Cut off preceding punctuation ($PChar)
            match_p = re.match(r"^(" + P_CHAR + r")(.+)$", current_word)
            if match_p:
                final_tokens.append(match_p.group(1)) 
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
        if current_word in exception_words:
            final_tokens.append(current_word)
            final_tokens.extend(suffix)
            continue
            
        # 3. Disambiguate periods
        if current_word.endswith('.') and current_word != '...' and not re.match(r"^[0-9]+\.$", current_word):
            root = current_word[:-1]
            period = '.'
            
            final_tokens.append(root)  # Clitic separation already happened in Pass 1
            final_tokens.append(period)
            final_tokens.extend(suffix)
            continue
            
        # 4. Final word token
        final_tokens.append(current_word)
        final_tokens.extend(suffix)

    return final_tokens

# --- 3. File Loading Functions ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    # ... (Implementation remains the same) ...
    lexicon_words = set()
    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, lexicon_file)
        # ... read file content ...
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().lower()
                if word:
                    lexicon_words.add(word)
        st.sidebar.success(f"✅ Lexicon loaded: {len(lexicon_words)} words.")
        return lexicon_words
    except Exception:
        st.sidebar.error("❌ Error loading lexicon.")
        return set()

@st.cache_resource 
def read_exceptions(exception_file: str) -> Set[str]:
    # ... (Implementation remains the same) ...
    exception_words = set()
    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, exception_file)
        # ... read file content ...
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip() 
                if word:
                    exception_words.add(word)
        st.sidebar.success(f"✅ Exceptions loaded: {len(exception_words)} phrases.")
        return exception_words
    except Exception:
        st.sidebar.warning("❗ Exception file not found. Proceeding without.")
        return set()

# --- 4. Main Streamlit Application Function ---

def main():
    st.title("🇮🇩 Indonesian Tokeniser Pipeline")
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
        key="input_text",
        height=150
    )

    # --- Stage 1: Clitic Separation ---
    if st.button("Run Clitic Separation (Stage 1)", type="primary"):
        if user_input.strip():
            parser = CliticSeparatorParser(lexicon_set)
            parser.feed(user_input)
            clitic_output = parser.get_tokenized_output()
            
            st.session_state['clitic_output'] = clitic_output
            st.session_state['stage1_done'] = True
            
            st.subheader("Stage 1 Output: Clitic Separation")
            st.code(clitic_output, language='text')
            st.rerun() # Rerun to display the next button

# --- Stage 2: Full Tokenization ---
    if 'stage1_done' in st.session_state and st.session_state['stage1_done']:
        st.markdown("---")
        st.header("2. Full Tokenization (Stage 2)")
        
        clitic_output = st.session_state['clitic_output']
        
        st.info("Input for Stage 2 (TreeTagger Logic):")
        st.code(clitic_output, language='text')

        # Button to proceed to the next stage
        if st.button("Proceed to Tokenization (Stage 2)"):
            if not exception_set:
                 st.warning("Warning: Exception file not loaded. Abbreviation rules will rely only on regex.")
            
            # Use the clitic-separated text as input
            final_tokens = full_tokenization_pipeline(clitic_output, exception_set)
            
            st.subheader("Final Tokenization Output (TreeTagger Rules Applied)")
            st.code('\n'.join(final_tokens), language='text')

if __name__ == "__main__":
    main()
