import streamlit as st
import re
from html.parser import HTMLParser
import os
from typing import List, Set

# --- Configuration ---
LEXICON_FILENAME = 'lexicon_only.txt'

# --- 1. TreeTagger Tokenization Logic (Perl Equivalent) ---

# Characters that should be cut off/separated at the beginning of a word
# [¿¡{(\\`"‚„†‡‹‘’“”•–—›
P_CHAR = r"[¿¡{()\\[\`\"‚„†‡‹‘’“”•–—›]"

# Characters that should be cut off/separated at the end of a word
# ]}'"`"),;:\!?\%‚„…†‡‰‹‘’“”•–—›
F_CHAR = r"[\]\}\'\"\`\)\,\;\:\!\?\%‚„…†‡‰‹‘’“”•–—›]"

# Indonesian-specific clitics (Suffixes: nya, mu, ku. Prefix: ku)
# NOTE: The clitic logic is handled in the existing process_word function
P_CLITIC = ''  # Not used for prefix 'ku-' as the Perl logic is complex; stick to the lexicon-based 'ku-' split
F_CLITIC = ''  # Not used for Indonesian suffixes; stick to lexicon-based split

def tree_tagger_split(text_segment: str, lexicon_words: Set[str]) -> List[str]:
    """
    Applies the core TreeTagger-style tokenization and punctuation separation 
    to a segment of text (which may be a word or punctuation).
    
    This function replaces the simple whitespace split from the previous version.
    """
    tokens = []
    
    # Add temporary space padding for robust regex matching (equivalent to Perl's ' '.$_.' ')
    temp_text = ' ' + text_segment + ' '
    
    # Insert missing blanks after punctuation (Perl lines s/([.,:])([^ 0-9.])/$1 $2/g etc.)
    temp_text = re.sub(r'(\.\.\.)', r' \1 ', temp_text)
    temp_text = re.sub(r'([;\!\?])([^\s])', r'\1 \2', temp_text)
    temp_text = re.sub(r'([.,:])([^\s0-9.])', r'\1 \2', temp_text)
    
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
                
            # 3. Cut off trailing periods if punctuation precedes (Perl's s/([$FChar])\.$//)
            # This is complex and often handled by the general punctuation logic. 
            # We focus on the main TreeTagger period disambiguation.

            if finished:
                break
        
        # 4. Abbreviation and Period Disambiguation
        # Check for explicitly listed tokens (equivalent to $Token{$_})
        # For simplicity, we assume your lexicon_only.txt serves as this list for the base word.
        # Check for A. or U.S.A. (not split)
        if re.match(r"^([A-Za-z-]\.)+$", current_word):
            tokens.append(process_word(current_word, lexicon_words))
            tokens.extend(suffix)
            continue
            
        # Disambiguate periods: if word ends with '.' AND is not '...' and not a number
        # If it's not in the lexicon, treat the period as a separator.
        if current_word.endswith('.') and current_word != '...' and not re.match(r"^[0-9]+\.$", current_word):
            root = current_word[:-1]
            period = '.'
            
            # Use lexicon check to determine if the root should be separated from the period
            # If the root is not in the lexicon (or defined as an exception), we separate.
            # TreeTagger usually only separates if the root is not an abbreviation and not defined.
            # We apply the clitic separation to the root (which also performs the lexicon check).
            
            # If the root is in the lexicon OR if it contains non-alpha characters (like numbers), we keep it.
            # To simplify, we rely on process_word's behavior.
            
            # If the root is NOT in the lexicon, it implies the period is a sentence ender/separator.
            # Since the Perl script separates the period if the root is not defined, we force separation.
            
            # Apply clitic separation (lexicon check) to the root word
            tokens.append(process_word(root, lexicon_words))
            tokens.append(period)
            tokens.extend(suffix)
            continue

        # 5. Apply Indonesian Clitic Separator and add tokens
        tokens.append(process_word(current_word, lexicon_words))
        tokens.extend(suffix)

    return tokens

# --- 2. HTML/Text Processing Class (Modified for Full Tokenization) ---

class TokenisingHTMLParser(HTMLParser):
    """
    Parses text, correctly delimiting tags, and applying the full TreeTagger-style
    tokenization/clitic separation only to text content.
    """
    def __init__(self, lexicon_words, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lexicon_words = lexicon_words
        self.processed_tokens = [] # Store tokens in a list
        self.processed_text = ""   # Store joined text

    # --- HTML Tag Handling (Modified for Desired Output) ---
    def handle_starttag(self, tag, attrs):
        """Reconstructs the opening tag, appending it as a single token."""
        attr_str = "".join([f' {key}="{value}"' for key, value in attrs])
        complete_tag = f"<{tag}{attr_str}>"
        self.processed_tokens.append(complete_tag)

    def handle_endtag(self, tag):
        """Reconstructs the closing tag, appending it as a single token."""
        complete_tag = f"</{tag}>"
        self.processed_tokens.append(complete_tag)

    def handle_data(self, data):
        """Processes the actual text content using the full tokenizer."""
        text = preprocess_text(data)
        
        # Split by the special separator character used for SGML isolation in the Perl script
        segments = re.split(r'(\s+)', text)
        
        for segment in segments:
            if not segment or segment.isspace():
                # Keep whitespace/empty strings out of the token list
                continue 
            
            # Apply the full TreeTagger tokenization to each segment
            new_tokens = tree_tagger_split(segment, self.lexicon_words)
            self.processed_tokens.extend(new_tokens)
    
    def get_tokenized_output(self) -> str:
        # Join tokens with a single space for the final output string
        return " ".join(self.processed_tokens)


# --- 3. Core Logic Functions (Clitic Separator - Retained from Part 1) ---

def preprocess_text(text: str) -> str:
    """Handles quotes and the prefix 'ku' as separate words."""
    text = re.sub(r"(['\"])\s*ku", r"\1 ku", text)
    return text

def process_word(word: str, lexicon_words: Set[str]) -> str:
    """
    Applies the lexicon-based clitic separation (Part 1).
    Note: This is now called *within* the full tokenization pipeline.
    """
    original_word = word
    
    # 1. Check if punctuation exists (handled by tree_tagger_split, but kept for robustness)
    punctuation_match = re.search(r"([!?.,'\"()\[\]{}:;.../\\~_-])$", word)
    punctuation = punctuation_match.group(1) if punctuation_match else ""
    word_without_punct = re.sub(r"[!?.,'\"()\[\]{}:;.../\\~_-]$", "", word)
    
    # If punctuation was stripped by the tokenization, we only proceed with the core word
    if punctuation:
        # If tree_tagger_split handles punctuation, this block should ideally only see words
        pass
    
    if not word_without_punct:
        return original_word

    lower_word = word_without_punct.lower()
    
    # Check if the full word is in the lexicon (no split if it is)
    if lower_word in lexicon_words:
        return original_word

    # Check for clitic suffixes ('nya', 'mu', 'ku')
    clitics = {'nya': 3, 'mu': 2, 'ku': 2}
    for clitic, length in clitics.items():
        if lower_word.endswith(clitic):
            root_word = word_without_punct[:-length]
            if root_word.lower() in lexicon_words:
                return f"{root_word} -{clitic}" 
    
    # Check for 'ku' prefix
    if lower_word.startswith('ku') and len(word_without_punct) > 2:
        root_word = word_without_punct[2:]
        if root_word.lower() in lexicon_words:
            return f"ku- {root_word}"
            
    # Return the word as is
    return original_word

# --- 4. Main Streamlit Application Function (Updated Output) ---

@st.cache_resource 
def read_lexicon(lexicon_file: str) -> Set[str]:
    # (Function implementation remains the same)
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


def main():
    st.title("🇮🇩 Indonesian Tokeniser (TreeTagger Style)")
    st.markdown("---")

    lexicon_set = read_lexicon(LEXICON_FILENAME)
    
    if not lexicon_set:
        st.warning("Application requires the lexicon to run. Please check file path.")
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
            st.markdown("This output performs: Clitic separation (`rumah -nya`), Punctuation separation (`besar !`), Abbreviation handling (`U.S.A.`), and Tag preservation (`<tag>`).")
            
            st.code(final_processed_text, language='text')
            
            final_tokens = final_processed_text.split()
            st.subheader("Token List (One Token Per Line)")
            # Display tokens vertically, like the original TreeTagger output format
            st.code('\n'.join(final_tokens), language='text')
            
        else:
            st.warning("Please enter some text to process.")

if __name__ == "__main__":
    main()
