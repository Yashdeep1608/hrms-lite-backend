import json
from pathlib import Path
import logging


class Translator:
    def __init__(self, default_lang="en"):
        self.default_lang = default_lang
        self.supported_langs = ["en", "hi"]
        self.translations = self.load_translations()

    def load_translations(self):
        translations = {}
        base_path = Path(__file__).resolve().parent.parent / "locals"

        for lang in self.supported_langs:
            file = base_path / f"{lang}.json"
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        logging.warning(f"Translation file '{file}' is empty.")
                        continue
                    translations[lang] = json.loads(content)
            except Exception as e:
                logging.warning(f"Failed to load translation file '{file}': {e}")

        return translations

    def t(self, key: str, lang: str = None) -> str:
        lang = lang if lang in self.supported_langs else self.default_lang
        return (
                self.translations.get(lang, {}).get(key)
                or self.translations.get(self.default_lang, {}).get(key)
                or key
        )
