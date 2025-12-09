from typing import Dict
from ..core.presentation_standards import PresentationStandards


# 발표 음성 분석 결과를 점수화
class PresentationScorer:

    # 값을 0-100 점수로 변환
    @staticmethod
    def normalize_score(value: float, ideal: float, min_val: float, max_val: float) -> int:

        if value < min_val:
            return max(0, int(50 * (value / min_val)))
        elif value > max_val:
            return max(0, int(50 * (max_val / value)))
        else:
            # ideal에 가까울수록 100점
            distance = abs(value - ideal)
            range_width = max_val - min_val
            score = 100 - int((distance / range_width) * 100)
            return max(0, min(100, score))

    # 분석 결과로부터 점수 채점
    @classmethod
    def calculate_scores(cls, result: Dict) -> Dict[str, int]:
        std = PresentationStandards

        # 음량 점수
        volume_score = cls.normalize_score(result['avg_volume_db'], std.VOLUME_IDEAL, std.VOLUME_MIN, std.VOLUME_MAX)

        # 피치 점수 (억양 변화 기준)
        pitch_score = cls.normalize_score(result['pitch_std'], std.PITCH_STD_IDEAL, std.PITCH_STD_MIN, std.PITCH_STD_MAX)

        # 말하기 속도 점수
        speech_rate = result.get('speech_rate_actual') or result.get('speech_rate_total')

        if speech_rate:
            speed_score = cls.normalize_score(speech_rate, std.SPEECH_RATE_IDEAL, std.SPEECH_RATE_MIN, std.SPEECH_RATE_MAX)
        else:
            speed_score = 50  # 기본값

        # 침묵 점수
        silence_score = cls.normalize_score(result['silence_ratio'], std.SILENCE_RATIO_IDEAL, std.SILENCE_RATIO_MIN, std.SILENCE_RATIO_MAX)

        # 명료도 점수
        clarity_score = cls.normalize_score(result['avg_zcr'], std.ZCR_IDEAL, std.ZCR_MIN, std.ZCR_MAX)

        # 종합 점수 (가중 평균)
        overall_score = int(volume_score * 0.2 + pitch_score * 0.25 + speed_score * 0.25 + silence_score * 0.15 + clarity_score * 0.15)

        return {
            'volume_score': volume_score, # 음량 점수
            'pitch_score': pitch_score, # 피치 점수
            'speed_score': speed_score, # 말하기 속도 점수
            'silence_score': silence_score, # 침묵 점수
            'clarity_score': clarity_score, # 명료도 점수
            'overall_score': overall_score # 종합 점수
        }