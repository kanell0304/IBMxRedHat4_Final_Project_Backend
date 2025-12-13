import asyncio
from app.database.database import AsyncSessionLocal
from app.service.answer_analysis_service import (
    i_process_answer,
    analyze_weakness_patterns,
    analyze_speech_style_evolution,
)

# chroma_service.py 테스트용

TEST_USER_ID = 1
TEST_ANSWER_IDS = [1,2,3,4]


async def main():
    async with AsyncSessionLocal() as db:
        # 1) 각 답변 처리
        for answer_id in TEST_ANSWER_IDS:
            print(f"\n=== i_process_answer({answer_id}) ===")
            result = await i_process_answer(answer_id, db)
            print(result)

        # 2) 약점 패턴
        print("\n\n=== analyze_weakness_patterns ===")
        weak = analyze_weakness_patterns(TEST_USER_ID)
        print(weak)

        # 3) 성장 추이 (전체)
        print("\n\n=== analyze_speech_style_evolution (전체) ===")
        evo_all = analyze_speech_style_evolution(TEST_USER_ID)
        print(evo_all)

        # 4) growth for 특정 질문 (1번)
        print("\n\n=== analyze_speech_style_evolution (question_no=1) ===")
        evo_q1 = analyze_speech_style_evolution(TEST_USER_ID, question_no=1)
        print(evo_q1)


if __name__ == "__main__":
    asyncio.run(main())
