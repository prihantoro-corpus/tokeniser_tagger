import streamlit as st
import re
from html.parser import HTMLParser
import os

# --- Configuration ---
# Assuming 'lexicon_only.txt' is placed in the same directory as this script on GitHub
LEXICON_FILENAME = 'lexicon_only.txt'

# --- Utility Function: Lexicon Loading ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> set:
    """
    Reads the lexicon file, converts words to lowercase, and returns a set.
    The @st.cache_resource decorator ensures the lexicon is loaded only once,
    which is essential for Streamlit performance.
    """
    lexicon_words = set()
    try:
        # Use a path relative to the script's directory for robust deployment
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

# --- Core Logic Functions (Clitic Separator) ---

def preprocess_text(text: str) -> str:
    """Handles quotes and the prefix 'ku' as separate words."""
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word(word: str, lexicon_words: set) -> str:
    """Processes a single word, handling punctuation and lexicon-based clitic separation."""
    original_word = word
    
    # 1. Save and remove end punctuation
    punctuation_match = re.search(r"([!?.,'\"()\[\]{}:;.../\\~_-])$", word)
    punctuation = punctuation_match.group(1) if punctuation_match else ""
    word_without_punct = re.sub(r"[!?.,'\"()\[\]{}:;.../\\~_-]$", "", word)
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    # 2. Check if the full word is in the lexicon (no split if it is)
    if lower_word in lexicon_words:
        return original_word

    # 3. Check for clitic suffixes ('nya', 'mu', 'ku')
    clitics = {'nya': 3, 'mu': 2, 'ku': 2}
    for clitic, length in clitics.items():
        if lower_word.endswith(clitic):
            root_word = word_without_punct[:-length]
            if root_word.lower() in lexicon_words:
                # Format: root -clitic punctuation
                return f"{root_word} -{clitic} {punctuation}" 
    
    # 4. Check for 'ku' prefix
    if lower_word.startswith('ku') and len(word_without_punct) > 2:
        root_word = word_without_punct[2:]
        if root_word.lower() in lexicon_words:
            # Format: ku- root punctuation
            return f"ku- {root_word} {punctuation}"
            
    # 5. Return the word as is
    return original_word

# --- HTML/Text Processing Class ---

class TokenisingHTMLParser(HTMLParser):
    """Parses text, skipping tags, and applying tokenization/clitic separation."""
    def __init__(self, lexicon_words, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lexicon_words = lexicon_words
        self.processed_text = ""

    def handle_starttag(self, tag, attrs):
        attr_str = "".join([f' {key}="{value}"' for key, value in attrs])
        self.processed_text += f"<{tag}{attr_str}>"

    def handle_endtag(self, tag):
        self.processed_text += f"</{tag}>"

    def handle_data(self, data):
        text = preprocess_text(data)
        # Split by space/newline while keeping the delimiters
        tokens = re.split(r'(\s+)', text)
        
        processed_tokens = []
        for token in tokens:
            if token and not token.isspace():
                processed_tokens.append(process_word(token, self.lexicon_words))
            else:
                processed_tokens.append(token)
                
        self.processed_text += "".join(processed_tokens)

# --- Main Streamlit Application Function ---

def main():
    st.title("🇮🇩 Indonesian Tokeniser (Clitic Separator) Prototype")
    st.markdown("---")

    # Load the lexicon
    lexicon_set = read_lexicon(LEXICON_FILENAME)
    
    if not lexicon_set:
        st.warning("Application requires the lexicon to run. Please check file path.")
        return

    st.header("1. Input Text")
    
    # Streamlit widget for user input (multiline)
    user_input = st.text_area(
        "Enter your Indonesian sentence or text:",
        "Kulihat rumahnya sangat besar. <tag>Apakah itu rumahmu?</tag>",
        height=150
    )
    
    # Process the text when the button is clicked
    if st.button("Tokenize & Separate Clitics", type="primary"):
        if user_input.strip():
            parser = TokenisingHTMLParser(lexicon_set)
            parser.feed(user_input)
            
            st.header("2. Tokenization Output")
            st.markdown("The output shows clitics separated by a space and hyphen, following your Perl script logic.")
            
            # Display the resulting text
            st.code(parser.processed_text, language='text')
            
            # Optionally show tokens in a list format
            final_tokens = parser.processed_text.split()
            st.subheader("Token List")
            st.write(final_tokens)
            
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()