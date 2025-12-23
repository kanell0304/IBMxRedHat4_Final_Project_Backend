# 발표 음성 파일을 분석한 결과의 기준(일반적인 기준 이라고 하네요ㅇㅇ)

class PresentationStandards:

    # 음량 (dB)
    VOLUME_IDEAL = -20.0  # 이상적인 평균 음량
    VOLUME_MIN = -30.0  # 최소 허용 음량
    VOLUME_MAX = -10.0  # 최대 허용 음량

    # 피치 (Hz)
    PITCH_IDEAL_MALE = 120.0  # 남성 이상적인 피치
    PITCH_IDEAL_FEMALE = 210.0  # 여성 이상적인 피치
    PITCH_STD_IDEAL = 40.0  # 이상적인 억양 변화
    PITCH_STD_MIN = 20.0  # 최소 억양 변화
    PITCH_STD_MAX = 80.0  # 최대 억양 변화

    # 발화 속도 (음절/초)
    SPEECH_RATE_IDEAL = 4.5  # 이상적인 발화 속도
    SPEECH_RATE_MIN = 3.5  # 최소 발화 속도
    SPEECH_RATE_MAX = 5.5  # 최대 발화 속도

    # 침묵 비율
    SILENCE_RATIO_IDEAL = 0.15  # 이상적인 침묵 비율 (15%)
    SILENCE_RATIO_MIN = 0.05  # 최소 침묵 비율
    SILENCE_RATIO_MAX = 0.30  # 최대 침묵 비율

    # 명료도 (ZCR)
    ZCR_IDEAL = 0.07
    ZCR_MIN = 0.04
    ZCR_MAX = 0.10