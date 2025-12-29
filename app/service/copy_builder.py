from typing import List, Dict, Any, Optional
from app.database.schemas.interview import WeaknessDetail, MetricChange


# 약점 라벨에 대한 개선 가이드 생성
def build_improvement_guide(
        label_name:str,
        context:Optional[Dict[str, Any]]=None,
        use_llm:bool=False
)->str:
    if use_llm:
        pass

    guide_map={
        "slang": "격식 있는 표준어로 대체하여 연습하세요.",
        "filler": "답변 전 3초 생각하고 또박또박 말하는 연습을 하세요.",
        "biased": "중립적이고 객관적인 언어 사용을 습관화하세요.",
        "curse": "감정 조절 후 공손한 표현으로 바꾸는 연습을 하세요.",
        "formality_inconsistency": "면접에서는 일관되게 존댓말('-습니다')을 사용하세요.",
        "disfluency_repetition": "문장을 머릿속으로 완성한 후 말하는 연습을 하세요.",
        "vague": "구체적인 수치와 사례를 들어 명확하게 표현하세요.",
        "ending_da": "'-다' 대신 '-습니다' 종결형을 사용하세요.",
    }
    return guide_map.get(label_name, "의식적으로 개선하려 노력하세요.")


# 약점 분석 전체 요약 문장 생성
def build_weakness_summary(
        weaknesses:List[WeaknessDetail],
        total_interview:int,
        top_trend: Optional[str]=None,
        use_llm:bool=False
)->str:
    if use_llm:
        pass

    if not weaknesses:
        return f"총 {total_interview}회 인터뷰 분석 결과, 특별한 약점이 발견되지 않았습니다."
    
    top_weakness=weaknesses[0]
    trend_text = f" {top_trend}" if top_trend else ""
    return (
        f"총 {total_interview}회 인터뷰에서 '{top_weakness.label_display_name}'이(가) "
        f"{top_weakness.occurrence_count}회 발견되었습니다.{trend_text} {top_weakness.improvement_guide}"
    )


# 지표 변화 요약 문장 생성
def build_metric_change_summary(
        changes:List[MetricChange],
        total_interview:int,
        use_llm:bool=False
)->str:
    if use_llm:
        pass

    if not changes:
        return f"총 {total_interview}회 인터뷰 완료. 최근 3회와 이전 3회 사이에 큰 변화가 없습니다."


    positive = [c for c in changes if c.is_positive]
    negative = [c for c in changes if not c.is_positive]

    if positive and not negative:
        return f"최근 3회 동안 {positive[0].metric_name}이(가) {abs(positive[0].change_percent):.1f}% 개선되었습니다!"
    elif negative and not positive:
        return f"최근 3회 동안 {negative[0].metric_name}이(가) {abs(negative[0].change_percent):.1f}% 악화되었습니다. 주의가 필요합니다."
    else:
        return f"{positive[0].metric_name} 개선 ({abs(positive[0].change_percent):.1f}%), {negative[0].metric_name} 주의 필요 ({abs(negative[0].change_percent):.1f}%)"


# 유사 답변 힌트 메시지 생성
def build_similar_answer_hint_message(
    similarity: float,
    use_llm: bool = False
) -> str:
    
    if use_llm:
        pass

    return f"이전에 비슷한 답변을 한 적이 있어요. (유사도:{similarity*100:.0f}%)"


# BERT 라벨의 한글 표시명 반환
def get_label_display_name(label_name: str) -> str:
    
    mapping = {
        "slang": "비속어/은어",
        "filler": "군말/망설임",
        "biased": "편향적 표현",
        "curse": "욕설",
        "formality_inconsistency": "격식 불일치",
        "disfluency_repetition": "반복/더듬기",
        "vague": "모호한 표현",
        "ending_da": "'-다' 종결형 (반말)",
    }
    return mapping.get(label_name, label_name.replace("_", " ").title())
