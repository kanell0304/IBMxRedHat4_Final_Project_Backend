from typing import Dict


# 간단한 피드백용 프롬프트
def build_brief_prompt(result: Dict, scores: Dict) -> str:
    # 감정 정보 추출
    emotion_text = ""
    if result.get('emotion_scores'):
        anxious = result['emotion_scores'].get('Anxious', 0)
        embarrassed = result['emotion_scores'].get('Embarrassed', 0)
        emotion_text = f"\n- 감정 분석: 긴장({anxious:.1f}%), 당황({embarrassed:.1f}%)"
    
    return f"""
다음 발표 분석 결과를 바탕으로 2-3문장의 간단한 피드백을 제공하세요.

**분석 결과**:
- 전체 발표 시간: {result['duration_min']:.1f}분
- 음량 점수: {scores['volume_score']}/100 (평균: {result['avg_volume_db']:.1f}dB)
- 발화 속도 점수: {scores['speed_score']}/100
- 피치 점수: {scores['pitch_score']}/100 (억양 변화: {result['pitch_std']:.1f}Hz)
- 침묵 비율: {result['silence_ratio']*100:.1f}% (점수: {scores['silence_score']}/100)
- 종합 점수: {scores['overall_score']}/100{emotion_text}

**요구사항**:
- 가장 잘한 점 1가지와 개선할 점 1가지를 간결하게 언급
- 격려와 구체적 조언 포함
"""

# 자세한 피드백용 프롬프트
def build_detailed_prompt(result: Dict, scores: Dict) -> str:
    # 감정 정보 추출
    emotion_text = ""
    if result.get('emotion_scores'):
        anxious = result['emotion_scores'].get('Anxious', 0)
        embarrassed = result['emotion_scores'].get('Embarrassed', 0)
        emotion_text = f"\n- 감정 분석: 긴장 {anxious:.1f}%, 당황 {embarrassed:.1f}%"
        
        # 6개 전체 감정도 표시 (선택적)
        if result.get('all_emotion_scores'):
            all_emotions = result['all_emotion_scores']
            emotion_details = ", ".join([f"{k}: {v:.1f}%" for k, v in all_emotions.items()])
            emotion_text += f" (전체: {emotion_details})"
    
    return f"""
다음 발표 분석 결과를 바탕으로 상세한 피드백을 JSON 형식으로 제공하세요.

**분석 수치**:
- 발표 시간: {result['duration_min']:.1f}분 (목표 대비)
- 음량: 평균 {result['avg_volume_db']:.1f}dB, 최대 {result['max_volume_db']:.1f}dB (점수: {scores['volume_score']}/100)
- 발화 속도: {result.get('speech_rate_actual', 'N/A')} 음절/초 (점수: {scores['speed_score']}/100)
- 피치: 평균 {result['avg_pitch']:.1f}Hz, 변화폭 {result['pitch_std']:.1f}Hz (점수: {scores['pitch_score']}/100)
- 침묵: {result['silence_ratio']*100:.1f}%, {result['silence_duration']:.1f}초 (점수: {scores['silence_score']}/100)
- 명료도(ZCR): {result['avg_zcr']:.3f} (점수: {scores['clarity_score']}/100)
- 에너지 변화: {result['energy_std']:.3f}{emotion_text}

**출력 형식** (JSON):
{{
  "summary": "전반적인 발표 평가 (3-4문장)",
  "strengths": "잘한 점 상세 분석 (3-4개 항목)",
  "improvements": "개선이 필요한 점 상세 분석 (3-4개 항목)",
  "detailed_advice": "구체적이고 실행 가능한 조언 (항목별로)"
}}

**기준**:
- 음량: -20dB 전후가 이상적, -30dB 이하는 너무 작음, -10dB 이상은 너무 큼
- 발화 속도: 4.5 음절/초가 이상적, 3.5-5.5 범위가 적절
- 침묵 비율: 15% 전후가 이상적, 5% 이하는 너무 빠름, 30% 이상은 너무 느림
- 피치 변화: 40Hz 전후가 이상적 (단조로움 방지)
- 감정: 긴장도가 높을수록 불안함을 나타내며, 당황도가 높을수록 당황스러운 상태를 나타냅니다. 이 감정들은 발표 시 부정적인 영향을 미칠 수 있으므로, 필요하다면 이와 관련된 조언을 포함하세요.
"""