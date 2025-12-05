import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set
import treetaggerwrapper
import subprocess
import shutil

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'
EXCEPTION_FILENAME = 'exception.txt' 
PARAM_FILE = 'indonesian.par' # Your uploaded parameter file

# --- TreeTagger Setup (Must run once during deployment) ---

@st.cache_resource
def setup_treetagger():
    """
    Downloads and installs the TreeTagger executable into the Streamlit environment.
    This mimics running an install script during deployment.
    """
    # Define installation directory
    INSTALL_DIR = "treetagger_install"
    os.makedirs(INSTALL_DIR, exist_ok=True)
    
    # 1. Download TreeTagger (using the path from the wrapper library)
    try:
        if not os.path.exists(os.path.join(INSTALL_DIR, 'cmd', 'tree-tagger')):
            st.warning("Attempting to download TreeTagger binaries...")
            treetaggerwrapper.install_tagger(target_dir=INSTALL_DIR)
            st.success("TreeTagger binaries installed.")
        
        # 2. Copy the parameter file into the TreeTagger 'lib' directory
        param_src = os.path.join(os.path.dirname(__file__), PARAM_FILE)
        param_dest_dir = os.path.join(INSTALL_DIR, 'lib')
        os.makedirs(param_dest_dir, exist_ok=True)
        param_dest = os.path.join(param_dest_dir, PARAM_FILE)
        
        if os.path.exists(param_src) and not os.path.exists(param_dest):
            shutil.copy(param_src, param_dest)
            st.info(f"Copied {PARAM_FILE} to {param_dest_dir}")

        return os.path.abspath(INSTALL_DIR)
    
    except Exception as e:
        st.error(f"Failed to set up TreeTagger: {e}. Ensure required dependencies are available.")
        return None

# --- 2. Pass 3: POS Tagger Function ---

def run_pos_tagger(token_list: List[str], tagger_dir: str):
    """
    Runs the TreeTagger wrapper on the final token list.
    """
    if not tagger_dir:
        return ["Error: Tagger setup failed."]
        
    tagger = treetaggerwrapper.TreeTagger(
        TAGLANG='indonesian', # Custom language code for Tagger output
        TAGDIR=tagger_dir,
        TAGPARFILE=PARAM_FILE # Use the custom parameter file
    )
    
    try:
        # Tagger expects input as a list of tokens (one token per line)
        # It handles the token -> tag/lemma output
        tags = tagger.tag_list(token_list)
        return tags
    except Exception as e:
        st.error(f"TreeTagger execution failed: {e}. Check indonesian.par path/format.")
        return ["Error during tagging."]

# --- 3. Pass 2: Full Tokenization Logic (Perl Equivalent) ---

P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

def tree_tagger_split(text_segment: str, lexicon_words: Set[str], exception_words: Set[str]) -> List[str]:
    # (Use the FINAL CORRECTED logic from the previous step)
    # ... [Insert the complete and corrected tree_tagger_split function logic here] ...
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
        
        # --- ABSOLUTE PRIORITY CHECKS ---
        
        if current_word in exception_words:
            tokens.append(current_word)
            continue 
            
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            tokens.append(current_word)
            continue 
            
        if re.match(r"^[A-Za-z]+-[A-Za-z]+$", current_word):
             tokens.append(current_word)
             continue
        
        # --- SPLITTING AND DISAMBIGUATION ---
        
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
            
            # Note: This is where we break the token to prepare for tagging
            tokens.append(root) 
            tokens.append(period)
            tokens.extend(suffix)
            continue

        # 4. Final word token
        tokens.append(current_word)
        tokens.extend(suffix)

    return tokens


# --- 4. Pass 1: Clitic Separation Logic (Used for intermediate tokenizing) ---

def process_word_clitic(word: str, lexicon_words: Set[str]) -> str:
    # ... [Insert the final corrected process_word_clitic function logic here] ...
    original_word = word
    
    # 1. Save and remove end punctuation 
    punctuation_match = re.search(r"([!?.,'\"()\[\]{}:;.../\\~_-])$", word)
    punctuation = punctuation_match.group(1) if punctuation_match else ""
    word_without_punct = re.sub(r"[!?.,'\"()\[\]{}:;.../\\~_-]$", "", word)
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    # Handle isolated clitics 
    if lower_word == 'nya':
        return f"-nya {punctuation}".strip()
    if lower_word == 'mu':
        return f"-mu {punctuation}".strip()

    # Check if the full word is in the lexicon 
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

# --- 5. File Loading Functions (No Change) ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    # ... read file content ...
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
    # ... read file content ...
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

# --- 6. Main Streamlit Application Function ---

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
    if not tagger_install_dir:
        st.warning("Application halted: TreeTagger setup failed.")
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
            st.session_state['stage2_done'] = False # Reset subsequent stages
            
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
            
            # Use the clitic-separated text as input
            # This requires passing the string, and the function splits it internally
            tokens_pass2 = full_tokenization_pipeline(clitic_output, exception_set)
            
            st.session_state['tokens_pass2'] = tokens_pass2
            st.session_state['stage2_done'] = True
            
            st.subheader("Stage 2 Output: Final Tokens")
            st.code('\n'.join(tokens_pass2), language='text')
            st.rerun()

# --- Stage 3: POS Tagging ---
    if 'stage2_done' in st.session_state and st.session_state['stage2_done']:
        st.markdown("---")
        st.header("3. POS Tagging (Stage 3)")
        
        tokens_pass2 = st.session_state['tokens_pass2']
        
        # Check if Tagger is installed before showing button
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
