from langdetect import detect

def detect_lang(text: str) -> str:
    try:
        lang = detect(text)
        return lang if lang in ["hi", "en"] else "hi-en"
    except:
        return "unknown"
