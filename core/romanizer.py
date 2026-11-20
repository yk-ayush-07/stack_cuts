"""romanizer.py: Transliterates Devanagari (Hindi) and foreign scripts into readable Roman/Latin English text.
Ensures short-form video captions (Reels, TikTok, Shorts) are legible to modern audiences.
"""
import re

# Devanagari vowel and consonant mappings
_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah'
}

_MATRAS = {
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ँ': 'n', 'ः': 'h', '्': ''
}

_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'f', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'क्ष': 'ksh', 'त्र': 'tr', 'ज्ञ': 'gy', 'श्र': 'shr',
    'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'ड़': 'd', 'ढ़': 'dh', 'फ़': 'f'
}

_COMMON_WORDS = {
    'भाई': 'bhai', 'क्या': 'kya', 'तूने': 'tune', 'तू': 'tu', 'यहाँ': 'yahan',
    'वहाँ': 'wahan', 'कैसे': 'kaise', 'हो': 'ho', 'गया': 'gaya', 'गई': 'gayi',
    'था': 'tha', 'थी': 'thi', 'थे': 'the', 'नहीं': 'nahi', 'हाँ': 'haan',
    'अरे': 'arey', 'ओपी': 'OP', 'ओरे': 'arey', 'खत्म': 'khatam', 'मार': 'maar',
    'चलो': 'chalo', 'देखा': 'dekha', 'देख': 'dekh', 'बोलो': 'bolo', 'सुनो': 'suno'
}

def is_devanagari(text: str) -> bool:
    """Check if the text contains Devanagari characters."""
    return bool(re.search(r'[\u0900-\u097F]', text))

def transliterate_devanagari(word: str) -> str:
    """Convert a Devanagari word into Roman/Latin letters."""
    if word in _COMMON_WORDS:
        return _COMMON_WORDS[word]

    res = []
    chars = list(word)
    i = 0
    n = len(chars)

    while i < n:
        c = chars[i]
        # Check two-char composite (nukta)
        if i + 1 < n and chars[i + 1] == '़':
            combo = c + chars[i + 1]
            if combo in _CONSONANTS:
                c = combo
                i += 1

        if c in _VOWELS:
            res.append(_VOWELS[c])
        elif c in _CONSONANTS:
            base = _CONSONANTS[c]
            # Check next char for matra or halant
            if i + 1 < n and chars[i + 1] in _MATRAS:
                res.append(base + _MATRAS[chars[i + 1]])
                i += 1
            elif i + 1 < n and chars[i + 1] == '्':  # Virama/halant (no implicit 'a')
                res.append(base)
                i += 1
            else:
                # Add implicit 'a' unless at end of word (Devanagari schwa convention)
                res.append(base + ('a' if i + 1 < n else ''))
        elif c in _MATRAS:
            res.append(_MATRAS[c])
        else:
            res.append(c)
        i += 1

    out = ''.join(res)
    # Clean up awkward double letters
    out = re.sub(r'aaa+', 'aa', out)
    out = re.sub(r'eee+', 'ee', out)
    return out

def romanize_text(text: str) -> str:
    """Transliterate words in text if they are written in Devanagari."""
    if not is_devanagari(text):
        return text

    words = text.split()
    converted = []
    for w in words:
        if is_devanagari(w):
            converted.append(transliterate_devanagari(w))
        else:
            converted.append(w)
    return ' '.join(converted)
