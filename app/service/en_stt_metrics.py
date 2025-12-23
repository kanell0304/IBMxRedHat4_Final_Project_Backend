from typing import Dict, Any
import string


# 영어 모의면접용 간단한 STT 메트릭 계산
def compute_en_stt_metrics(stt_result:Dict[str, Any])->Dict[str, Any]:
    all_words=[]

    for res in stt_result.get("results", []):
        for alt in res.get("alternatives", []):
            words=alt.get("words", [])
            all_words.extend(words)

    if not all_words:
        return {
            "speech_rate":0.0,
            "pause_ratio":0.0,
            "filler_count":0
        }
    
    def parse_time(time_str:str)->float:
        return float(time_str.rstrip('s'))
    
    start_time=parse_time(all_words[0]["startTime"])
    end_time=parse_time(all_words[-1]["endTime"])
    total_duration=end_time-start_time

    if total_duration<=0:
        total_duration=1.0

    
    # speech rate(WPM)
    cleaned_tokens = []
    for w in all_words:
        token = (w.get("word", "") or "").lower().strip().strip(string.punctuation)
        if token:
            cleaned_tokens.append(token)

    word_count = len(cleaned_tokens)
    speech_rate = (word_count / total_duration) * 60.0

    # pause ratio
    pause_threshold=0.7 # 0.7초 이상 gap을 pause로 간주
    total_pause_time=0.0

    
    for i in range(len(all_words)-1):
        current_end=parse_time(all_words[i]["endTime"])
        next_start=parse_time(all_words[i+1]["startTime"])
        gap=next_start-current_end

        if gap>=pause_threshold:
            total_pause_time+=gap

    pause_ratio=total_pause_time/total_duration if total_duration>0 else 0.0


    # filler words 카운트
    HARD_FILLERS={"uh", "um", "er", "ah", "hmm", "mm", "uhh", "umm"}
    SOFT_FILLERS={"like", "well", "so", "okay", "right", "actually", "basically"}

    hard_filler_count=0
    soft_filler_count=0

    for word_info in all_words:
        raw_word=word_info.get("word", "")
        word=raw_word.lower().strip().strip(string.punctuation)

        if not word:
            continue

        if word in HARD_FILLERS:
            hard_filler_count+=1
        elif word in SOFT_FILLERS:
            soft_filler_count+=1

    return {
        "speech_rate":round(speech_rate, 2),
        "pause_ratio":round(pause_ratio, 3),
        "filler":{
            "hard":hard_filler_count,
            "soft":soft_filler_count,
        },
    }
