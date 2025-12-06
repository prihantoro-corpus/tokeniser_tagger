import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set
import configparser
configparser.SafeConfigParser = configparser.ConfigParser # Fix for Python 3.12+
import treetaggerwrapper
import shutil

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'
EXCEPTION_FILENAME = 'exception.txt' 
PARAM_FILE = 'indonesian.par' 
TT_INSTALL_DIR = "treetagger_install"

# --- 1. TreeTagger Setup and Tagger Function (Kept for completeness) ---

@st.cache_resource
def setup_treetagger():
    # Checks if TreeTagger was installed by the external shell script
    BASE_PATH = os.path.abspath(TT_INSTALL_DIR)
    CMD_PATH = os.path.join(BASE_PATH, 'cmd')
    EXECUTABLE_PATH = os.path.join(CMD_PATH, 'tree-tagger') 
    
    if not os.path.exists(EXECUTABLE_PATH):
        st.sidebar.error("❌ TreeTagger executable not found. Installation script likely failed.")
        return None

    os.environ['PATH'] = f"{os.environ['PATH']}:{CMD_PATH}"
    os.environ['TREETAGGER_HOME'] = BASE_PATH
    os.environ['TAGDIR'] = BASE_PATH
    
    if os.path.exists(os.path.join(BASE_PATH, 'lib', PARAM_FILE)):
        st.sidebar.success("✅ TreeTagger environment successfully configured.")
        return BASE_PATH
    else:
        st.sidebar.error(f"❌ Error: {PARAM_FILE} not found in TreeTagger lib directory.")
        return None

def run_pos_tagger(token_list: List[str], tagger_dir: str):
    # Runs the POS Tagger (omitted details for brevity, assumed functional)
    if not tagger_dir: return ["Error: Tagger setup failed."]
    try:
        tagger = treetaggerwrapper.TreeTagger(TAGLANG='indonesian', TAGDIR=tagger_dir, TAGPARFILE=PARAM_FILE )
        tags = tagger.tag_list(token_list)
        return tags
    except Exception as e:
        return [f"Error during tagging: {e}"]

# --- 2. Pass 2: Full Tokenization Logic (TreeTagger Rules) ---

P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

def full_tokenization_pipeline(clitic_separated_text: str, exception_words: Set[str]) -> List[str]:
    """
    Applies the full TreeTagger tokenization rules (punctuation, abbreviation, period disambiguation)
    to the already clitic-separated text.
    """
    tokens = []
    
    # 1. Initial cleanup and whitespace standardization (Perl logic equivalent)
    temp_text = ' ' + clitic_separated_text + ' '
    temp_text = re.sub(r'(\.\.\.)', r' \1 ', temp_text)
    temp_text = re.sub(r'([;\!\?])([^\s])', r'\1 \2', temp_text)
    temp_text = re.sub(r'([.,:])([^\s0-9.])', r'\1 \2', temp_text)
    
    words = temp_text.split()
    
    for word in words:
        current_word = word
        suffix = []
        
        # --- ABSOLUTE PRIORITY CHECKS (If matched, skip splitting) ---
        
        # PRIORITY 1: Exception List (Exact Match)
        if current_word in exception_words:
            tokens.append(current_word)
            continue 
            
        # PRIORITY 2: Abbreviation Regex (Pattern Match)
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            tokens.append(current_word)
            continue 
            
        # PRIORITY 3: Hyphenated Compound Words 
        if re.match(r"^[A-Za-z]+-[A-Za-z]+$", current_word):
             tokens.append(current_word)
             continue
        
        # --- SPLITTING AND DISAMBIGUATION (Default Logic) ---
        
        # 1. Strip external punctuation
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
            
            tokens.append(root) 
            tokens.append(period)
            tokens.extend(suffix)
            continue
            
        # 4. Final word token
        tokens.append(current_word)
        tokens.extend(suffix)

    return tokens


# --- 3. Pass 1: Clitic Separation Logic (Finalized) ---

def preprocess_text(text: str) -> str:
    """Handles quotes and the prefix 'ku' as separate words."""
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word_clitic(word: str, lexicon_words: Set[str]) -> str:
    """Applies case-insensitive clitic separation and basic punctuation stripping."""
    original_word = word
    
    punctuation_match = re.search(r"([!?.,'\"()\[\]{}:;.../\\~_-])$", word)
    punctuation = punctuation_match.group(1) if punctuation_match else ""
    word_without_punct = re.sub(r"[!?.,'\"()\[\]{}:;.../\\~_-]$", "", word)
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    # --- PRIORITY 1: Check for clitic suffixes (Aggressive Split) ---
    clitics = {'nya': 3, 'mu': 2, 'ku': 2}
    
    for clitic, length in clitics.items():
        if lower_word.endswith(clitic):
            root_word = word_without_punct[:-length]
            
            if root_word and root_word.lower() in lexicon_words:
                return f"{root_word} -{clitic} {punctuation}".strip()

    # --- PRIORITY 2: Check for 'ku' prefix ---
    if lower_word.startswith('ku') and len(word_without_punct) > 2:
        root_word = word_without_punct[2:]
        if root_word.lower() in lexicon_words:
            prefix = original_word[:2] 
            return f"{prefix}- {root_word} {punctuation}".strip()
            
    # --- PRIORITY 3: Check for full word match (No split necessary) ---
    if lower_word in lexicon_words:
        return original_word

    # --- PRIORITY 4: Handle isolated clitics ---
    if lower_word == 'nya':
        return f"-nya {punctuation}".strip()
    if lower_word == 'mu':
        return f"-mu {punctuation}".strip()

    # 5. If no condition is met, return the word as is
    return original_word

class CliticSeparatorParser(HTMLParser):
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
        return re.sub(r'\s+', ' ', self.processed_text.strip())

# --- 4. File Loading Functions ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    lexicon_words = set()
    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, lexicon_file)
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
    exception_words = set()
    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, exception_file)
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

# --- 5. Main Streamlit Application Function ---

def main():
    st.title("🇮🇩 Indonesian Tokeniser + Tagger Pipeline")
    st.markdown("---")

    # Load resources and setup Tagger
    lexicon_set = read_lexicon(LEXICON_FILENAME)
    exception_set = read_exceptions(EXCEPTION_FILENAME)
    tagger_install_dir = setup_treetagger()
    
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

    if st.button("Run Clitic Separation (Stage 1)", type="primary"):
        if user_input.strip():
            parser = CliticSeparatorParser(lexicon_set)
            parser.feed(user_input)
            clitic_output = parser.get_tokenized_output()
            
            st.session_state['clitic_output'] = clitic_output
            st.session_state['stage1_done'] = True
            st.session_state['stage2_done'] = False
            st.session_state['stage3_done'] = False 
            
            st.subheader("Stage 1 Output: Clitic Separation")
            st.code(clitic_output, language='text')
            st.rerun()

# --- Stage 2: Full Tokenization ---
    if 'stage1_done' in st.session_state and st.session_state['stage1_done']:
        st.markdown("---")
        st.header("2. Full Tokenization (Stage 2)")
        
        clitic_output = st.session_state['clitic_output']
        st.info(f"Input for Stage 2: {clitic_output}")

        if st.button("Proceed to Tokenization (Stage 2)"):
            
            tokens_pass2 = full_tokenization_pipeline(clitic_output, exception_set)
            
            st.session_state['tokens_pass2'] = tokens_pass2
            st.session_state['stage2_done'] = True
            st.session_state['stage3_done'] = False
            
            st.subheader("Stage 2 Output: Final Tokens")
            st.code('\n'.join(tokens_pass2), language='text')
            st.rerun()

# --- Stage 3: POS Tagging ---
    if 'stage2_done' in st.session_state and st.session_state['stage2_done']:
        st.markdown("---")
        st.header("3. POS Tagging (Stage 3)")
        
        tokens_pass2 = st.session_state['tokens_pass2']
        
        if tagger_install_dir:
            if st.button("Run POS Tagger (Stage 3)"):
                
                # Run the tagger on the list of final tokens
                tagged_output = run_pos_tagger(tokens_pass2, tagger_install_dir)
                
                st.subheader("Final Output: Token | Tag | Lemma")
                st.code('\n'.join(tagged_output), language='text')
        else:
            st.error("Cannot run tagger: TreeTagger setup failed during deployment.")

if __name__ == "__main__":
    main()
