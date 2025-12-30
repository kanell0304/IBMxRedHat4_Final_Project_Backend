from typing import Dict


def build_english_interview_prompt(
        transcript:str,
        stt_metrics:Dict,
        qa_list:list
)->str:
    speech_rate=float(stt_metrics.get("speech_rate", 0.0) or 0.0)
    pause_ratio=float(stt_metrics.get("pause_ratio", 0.0) or 0.0)

    filler_hard=0
    filler_soft=0
    filler_obj=stt_metrics.get("filler")
    if isinstance(filler_obj, dict):
        filler_hard=int(filler_obj.get("hard", 0) or 0)
        filler_soft=int(filler_obj.get("soft", 0) or 0)
    else:
        filler_hard=int(stt_metrics.get("filler_count", 0) or 0)

    qa_lines=[]
    for i, qa in enumerate(qa_list, 1):
        qa_lines.append(f"Q{i}: {qa.get('question', '')}")
        qa_lines.append(f"A{i}: {qa.get('answer', '')}")
        qa_lines.append("")
    qa_block="\n".join(qa_lines)

    prompt=f"""You are an experienced English interview coach evaluating a mock interview performance.

[INTERVIEW TRANSCRIPT]
{transcript}

[Q&A PAIRS]
{qa_block}

[SPEECH METRICS]
- Speaking rate (WPM): {speech_rate:.2f}
- Pause ratio: {pause_ratio:.1%}
- Hard fillers (uh/um/er/ah): {filler_hard} times
- Soft fillers (like/so/well): {filler_soft} times

[SCORING CRITERIA - Must apply strictly]

**Content Quality (50 points)**
- Relevance to question (0-15 pts)
  * 13-15: Directly addresses all aspects of the question
  * 10-12: Addresses main question but misses some points
  * 7-9: Partially relevant, some deviation
  * 0-6: Off-topic or minimal relevance

- Structure & Logic (0-15 pts)
  * 13-15: Clear introduction/body/conclusion with logical flow
  * 10-12: Organized but some transitions are weak
  * 7-9: Basic structure but disjointed
  * 0-6: No clear structure

- Specificity & Examples (0-20 pts)
  * 17-20: Multiple concrete examples with details
  * 13-16: Some examples but lacking depth
  * 9-12: Vague or generic statements
  * 0-8: No specific examples

**Fluency & Delivery (30 points)**
- Speaking Rate (0-10 pts)
  * 9-10: 140-170 WPM (optimal)
  * 7-8: 120-139 or 171-190 WPM (acceptable)
  * 4-6: 100-119 or 191-210 WPM (too slow/fast)
  * 0-3: <100 or >210 WPM (problematic)

- Pauses & Flow (0-10 pts)
  * 9-10: Pause ratio 0-15% (smooth)
  * 7-8: Pause ratio 15-25% (acceptable)
  * 4-6: Pause ratio 25-35% (choppy)
  * 0-3: Pause ratio >35% (very disjointed)

- Filler Words (0-10 pts)
  * 9-10: 0-2 hard fillers, 0-5 soft fillers
  * 7-8: 3-5 hard fillers, 6-10 soft fillers
  * 4-6: 6-10 hard fillers, 11-15 soft fillers
  * 0-3: >10 hard fillers or >15 soft fillers

**Language & Grammar (20 points)**
- Grammar accuracy (0-10 pts)
  * 9-10: No errors or only minor slips
  * 7-8: Few errors, meaning clear
  * 4-6: Multiple errors affecting clarity
  * 0-3: Frequent errors impeding understanding

- Vocabulary & Expression (0-10 pts)
  * 9-10: Varied, professional vocabulary
  * 7-8: Adequate vocabulary, some repetition
  * 4-6: Limited vocabulary, frequent repetition
  * 0-3: Very basic or inappropriate words

[GRADING SCALE]
- 90-100: S (Outstanding - Ready for top companies)
- 80-89: A (Strong - Minor improvements needed)
- 70-79: B (Good - Solid performance with room to grow)
- 60-69: C (Average - Needs significant practice)
- Below 60: D (Weak - Major improvements required)

[REQUIREMENTS]
1. Calculate the EXACT score (0-100) by adding points from each category above
2. Provide grade (S/A/B/C/D) based on the score
3. Write 3 comments in Korean:
   - Content quality (structure, relevance, specificity)
   - Delivery & fluency (cite exact metrics: WPM={speech_rate:.0f}, pause={pause_ratio:.0%}, fillers={filler_hard})
   - Overall assessment
4. Write 2-3 improvements in Korean:
   - Must be SPECIFIC and ACTIONABLE
   - Focus on the LOWEST scoring categories
   - If content is weak: suggest structure frameworks or example-building techniques
   - If delivery is weak: suggest pacing exercises or filler reduction methods
   - If grammar/vocab is weak: suggest language learning resources

Output ONLY valid JSON. No other text.
{{
  "score": <number>,
  "comments": [
    "<comment 1>",
    "<comment 2>",
    "<comment 3>"
  ],
  "improvements": [
    "<improvement 1>",
    "<improvement 2>",
    "<optional improvement 3>"
  ]
}}
"""
    return prompt.strip()


ENGLISH_SYSTEM_MESSAGE="""You are a professional English interview evaluator.
Score strictly according to the rubric provided.
Output ONLY valid JSON with no additional text."""
