from sqlalchemy.orm import Session
from ..database.models.minigame import MiniGameSentence, DifficultyLevel

DEFAULT_SENTENCES = [
    # Easy
    {"sentence": "안녕하세요", "difficulty": DifficultyLevel.EASY, "category": "인사"},
    {"sentence": "오늘 날씨가 좋네요", "difficulty": DifficultyLevel.EASY, "category": "일상"},
    {"sentence": "감사합니다", "difficulty": DifficultyLevel.EASY, "category": "인사"},
    {"sentence": "반갑습니다", "difficulty": DifficultyLevel.EASY, "category": "인사"},
    {"sentence": "저는 학생입니다", "difficulty": DifficultyLevel.EASY, "category": "소개"},

    # Medium
    {"sentence": "내가 그린 기린 그림은 잘 그린 기린 그림이고",
     "difficulty": DifficultyLevel.MEDIUM, "category": "발음"},
    {"sentence": "간장 공장 공장장은 강 공장장이고",
     "difficulty": DifficultyLevel.MEDIUM, "category": "발음"},
    {"sentence": "저기 계신 저분이 박 법학박사이시고",
     "difficulty": DifficultyLevel.MEDIUM, "category": "발음"},
    {"sentence": "뜀박질하는 뜀박질 선수",
     "difficulty": DifficultyLevel.MEDIUM, "category": "발음"},
    {"sentence": "도토리가 토토로리를 토토로토토로",
     "difficulty": DifficultyLevel.MEDIUM, "category": "발음"},

    # Hard
    {"sentence": "철수 책상 철책상 책상다리 철책상다리",
     "difficulty": DifficultyLevel.HARD, "category": "빨리말하기"},
    {"sentence": "경찰청 철창살은 외철창살이고 검찰청 철창살은 쌍철창살이다",
     "difficulty": DifficultyLevel.HARD, "category": "발음"},
    {"sentence": "상표 붙인 큰 콩깡통은 깐 콩깡통이고 상표 붙인 작은 콩깡통은 안 깐 콩깡통이다",
     "difficulty": DifficultyLevel.HARD, "category": "빨리말하기"},
    {"sentence": "저기 계신 저분이 박 법학박사이시고 여기 계신 이분이 백 법학박사이시다",
     "difficulty": DifficultyLevel.HARD, "category": "긴문장"},
]


def init_default_sentences(db: Session):
    for data in DEFAULT_SENTENCES:
        existing = db.query(MiniGameSentence).filter(
            MiniGameSentence.sentence == data["sentence"]
        ).first()

        if not existing:
            sentence = MiniGameSentence(**data)
            db.add(sentence)

    db.commit()
    print(f"기본 문제 {len(DEFAULT_SENTENCES)}개 초기화 완료")