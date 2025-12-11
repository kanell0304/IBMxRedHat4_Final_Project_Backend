from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models.interview import InterviewAnswer



async def compute_interview_stt_metrics(
        interview_id:int,
        db:AsyncSession,
)->Dict[str, Any]:
    result=await db.execute(
        select(InterviewAnswer).where(InterviewAnswer.i_id==interview_id)
    )
    answers:List[InterviewAnswer]=list(result.scalars().all())


    if not answers:
        return {
            "num_answers": 0,
            "total_duration_sec": 0.0,
            "avg_speech_rate_wpm": 0.0,
            "total_pause_count": 0,
            "avg_pause_duration": 0.0,
            "avg_silence_ratio": 0.0,
            "avg_confidence": 0.0,
            "avg_low_conf_ratio": 0.0,
        }
    

    total_duration=0.0
    total_wpm=0.0
    total_pause_count=0

    pause_durations:List[float]=[]
    silence_ratios:List[float]=[]
    confidences:List[float]=[]
    low_conf_ratios:List[float]=[]

    valid_count=0

    for ans in answers:
        metrics=getattr(ans, "stt_metrics_json", None)
        if not metrics:
            continue

        valid_count+=1

        total_duration+=float(metrics.get("duration_sec", 0.0))
        total_wpm+=float(metrics.get("speech_rate_wpm", 0.0))
        total_pause_count += int(metrics.get("pause_count", 0))

        pause_durations.append(float(metrics.get("avg_pause_duration", 0.0)))
        silence_ratios.append(float(metrics.get("silence_ratio", 0.0)))
        confidences.append(float(metrics.get("avg_confidence", 0.0)))
        low_conf_ratios.append(float(metrics.get("low_conf_ratio", 0.0)))


    if valid_count==0:
        return {
            "num_answers": len(answers),
            "total_duration_sec": 0.0,
            "avg_speech_rate_wpm": 0.0,
            "total_pause_count": 0,
            "avg_pause_duration": 0.0,
            "avg_silence_ratio": 0.0,
            "avg_confidence": 0.0,
            "avg_low_conf_ratio": 0.0,
        }
    
    return {
        "num_answers": len(answers),
        "total_duration_sec": round(total_duration, 2),
        "avg_speech_rate_wpm": round(total_wpm / valid_count, 2),
        "total_pause_count": total_pause_count,
        "avg_pause_duration": round(sum(pause_durations) / valid_count, 2),
        "avg_silence_ratio": round(sum(silence_ratios) / valid_count, 2),
        "avg_confidence": round(sum(confidences) / valid_count, 2),
        "avg_low_conf_ratio": round(sum(low_conf_ratios) / valid_count, 2),
    }