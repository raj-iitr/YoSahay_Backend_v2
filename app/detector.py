from langdetect import detect

def detect_lang(text: str) -> str:
    try:
        logger.info(f"Detecting language for text: {text}")
        print(f"Detected language: {lang}")
        return lang if lang in ["hi", "en"] else "hi-en"
    except:
        return "unknown"
