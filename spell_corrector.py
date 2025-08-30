from spellchecker import SpellChecker
from textblob import TextBlob
from difflib import get_close_matches
import pandas as pd
from rapidfuzz import process, fuzz

# Load dataset
df = pd.read_csv("data/database_data.csv")

# Extract all unique keywords (lowercased, stripped)
keywords = set()
for col in df.columns:
    for val in df[col].dropna():
        for word in str(val).replace(",", " ").split():
            keywords.add(word.strip().lower())

keywords = list(keywords)

def correct_spelling(user_input, threshold=60):
    corrected_words = []
    for word in user_input.lower().split():
        match, score, _ = process.extractOne(word, keywords, scorer=fuzz.ratio)
        if score >= threshold:
            corrected_words.append(match)
        else:
            corrected_words.append(word)
    return " ".join(corrected_words)

class SpellCorrector:
    def __init__(self, threshold=60):
        self.threshold = threshold
        self.keywords = set()
        # Load dataset and build domain vocabulary
        df = pd.read_csv('data/database_data.csv')
        for col in df.columns:
            self.keywords.add(col.strip().lower())
            for val in df[col].dropna():
                for w in str(val).replace('"', '').replace("'", '').replace(',', ' ').split():
                    w_clean = ''.join([c for c in w if c.isalpha()])
                    if w_clean:
                        self.keywords.add(w_clean.lower())
        self.keywords.update([
            "weave", "composition", "quality", "agent", "customer", "quantity", "order", "confirmed", "sold", "type",
            "plain", "cotton", "premium", "stand", "linen", "spandex", "satin"
        ])
        self.keywords = list(self.keywords)

    def correct(self, text):
        import string
        from textblob import TextBlob
        text_nopunct = text.translate(str.maketrans('', '', string.punctuation))
        corrected_words = []
        for word in text_nopunct.split():
            lw = word.lower()
            # Exact match in domain keywords
            if lw in self.keywords:
                corrected_words.append(word)
            else:
                match, score, _ = process.extractOne(lw, self.keywords, scorer=fuzz.ratio)
                if score >= self.threshold and match in self.keywords:
                    corrected_words.append(match)
                else:
                    # Fallback to TextBlob for general spelling correction
                    tb_word = str(TextBlob(word).correct())
                    corrected_words.append(tb_word)
        result = ' '.join(corrected_words)
        return result
