from typing import Dict, Any, List

# 단어만 추출
def extract_words(stt_result: Dict[str, Any])->List[Dict[str, Any]]:
    
    words:List[Dict[str, Any]]=[]
    
    for item in stt_result.get("results", []):
        for alt in item.get("alternatives", []):
            for w in alt.get("words", []):
                words.append(w)
    return words

# STT 시간 문자열을 float으로 변환
def parse_time_to_sec(t:str)->float:
    if not t:
        return 0.0
    t=t.strip()

    if t.endswith("s"):
        t=t[:-1]

    try:
        return float(t)
    except ValueError:
        return 0.0
    
# STT 결과에서 신뢰도/객관성 메트릭 추출
def compute_stt_metrics(stt_result:Dict[str, Any])->Dict[str, Any]:
    words=extract_words(stt_result)
    if not words:
        return {
            "duration_sec":0.0,
            "num_words":0,
            "speech_rate_wpm":0.0,
            "pause_count":0,
            "avg_pause_duration":0.0,
            "max_pause_duration":0.0,
            "silence_ratio":0.0,
            "avg_confidence":0.0,
            "low_conf_ratio":0.0,
        }
    
    # 전체 시간, 단어 수, confidence
    start_times=[]
    end_times=[]
    confidences=[]

    for w in words:
        st=parse_time_to_sec(w.get("startTime", "0s"))
        et=parse_time_to_sec(w.get("endTime", "0s"))

        start_times.append(st)
        end_times.append(et)
        conf=w.get("confidence")

        if conf is not None:
            try:
                confidences.append(float(conf))
            except ValueError:
                pass

    duration_sec=max(end_times)-min(start_times) if end_times and start_times else 0.0
    num_words=len(words)
    minutes=duration_sec/60.0 if duration_sec>0 else 0.0
    speech_rate_wpm=num_words/minutes if minutes>0 else 0.0

    # pause 계산
    sorted_words=sorted(
        [
            (parse_time_to_sec(w.get("startTime", "0s")),
            parse_time_to_sec(w.get("endTime", "0s")))
            for w in words
        ],
        key=lambda x:x[0],
    )
        
    pauses:List[float]=[]
    total_silence=0.0

    # 0.7초 이상이면 의미 있는 멈춤
    PAUSE_THRESHOLD=0.7


    for i in range(len(sorted_words)-1):
        _, end_t=sorted_words[i]
        next_start, _=sorted_words[i+1]

        gap=next_start-end_t
        if gap>0:
            total_silence+=gap
            if gap>=PAUSE_THRESHOLD:
                pauses.append(gap)

    pause_count=len(pauses)
    avg_pause=sum(pauses)/len(pauses) if pauses else 0.0
    max_pause=max(pauses) if pauses else 0.0
    silence_ratio=total_silence/duration_sec if duration_sec>0 else 0.0

    # confidence 통계
    avg_conf=sum(confidences)/len(confidences) if confidences else 0.0
    low_conf=[c for c in confidences if c<0.8]
    low_conf_ratio=len(low_conf)/len(confidences) if confidences else 0.0


    return {
        "duration_sec":round(duration_sec, 2),
        "num_words":num_words,
        "speech_rate_wpm":round(speech_rate_wpm, 2),
        "pause_count":pause_count,
        "avg_pause_duration":round(avg_pause, 2),
        "max_pause_duration":round(max_pause, 2),
        "silence_ratio":round(silence_ratio, 2),
        "avg_confidence":round(avg_conf, 2),
        "low_conf_ratio":round(low_conf_ratio, 2),
    }


