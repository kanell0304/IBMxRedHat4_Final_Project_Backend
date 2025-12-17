from difflib import SequenceMatcher
import re


class ScoringService:

    @staticmethod
    def normalize_text(text: str) -> str:
        text = re.sub(r'\s+', '', text)
        return text.strip()

    @staticmethod
    def calculate_accuracy(original: str, recognized: str) -> float:
        original_norm = ScoringService.normalize_text(original)
        recognized_norm = ScoringService.normalize_text(recognized)

        if not original_norm or not recognized_norm:
            return 0.0

        similarity = SequenceMatcher(
            None,
            original_norm,
            recognized_norm
        ).ratio()

        return round(similarity * 100, 2)