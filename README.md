STEACH 프로젝트 Backend

STEACH: 이용자의 말투, 억양, 부적절한 표현등을 감지하여 이용자에게 피드백을 제공하는 서비스 <br>

프로젝트 구성원: 이경준(팀장), 하태호(부팀장), 김가현, 손연서

구성원 담당 파트
- 이경준: 발표분석(Wav2Vec2), 미니게임(Google STT), 로그인/회원가입/비밀번호 재설정, 커뮤니티, 관리자 페이지
- 하태호: 모의면접(Google STT, BERT), Rag, ChromaDB
- 김가현: 모의면접(Google STT, BERT), Rag, ChromaDB
- 손연서: 대화분석(Google STT, BERT)

기술스택
Frontend: React + Vite, Tailwind CSS
Backend: Python, FastAPI, SQLAlchemy, Alembic
AI/ML: PyTorch, Wav2Vec2(meta), Whisper(openai), OpenAI API, Google STT, BERT
Database: MySQL, ChromaDB
Infra(CI/CD): AWS(Route53, ALB, ECS, ECR, RDS, S3), Docker, GitHub Actions

서비스: 모의면접(Google STT, BERT), 대화분석(Google STT, BERT), 발표분석(Wav2Vec2, Scikit-Learn, Librosa), 미니게임(Google STT), 커뮤니티 <br>
- 모의 면접: 예상 질문 제시 -> 이용자가 실시간 녹음 -> Google STT 텍스트 변환 -> BERT 부적절한 표현 감지 -> 통합 피드백 + 질문별 피드백 제공 <br>
- 대화 분석: 녹음 파일 업로드 -> Google STT 텍스트 변환 -> BERT 부적절한 표현 감지 -> 통합 피드백 제공 <br>
- 발표 분석: 녹음 파일 업로드 -> Librosa 말하기 속도, 억양, 피치, 발화 등 분석 / Wav2Vec2 벡터화 후 학습된 Scikit-Learn으로 감정 분류(불안, 당황) -> 통합 피드백 + 상세 피드백 제공 <br>
- 미니게임: 게임 모드(문제수/제한시간), 난이도 선택 -> 이용자가 실시간 녹음 후 제출 -> 해당 세션이 끝나면 통합 피드백(점수-정확도) 제공 <br>

발표분석 Scikit-Learn에 이용된 학습 데이터 셋 출처: https://aihub.or.kr














가상환경 설치 가이드
- conda create -n {환경명} python=3.10 pip -y
- conda activate {환경명}
<br><br>
- python -m pip install --upgrade pip
- pip install -r requirements.txt

다음 링크에서 ffmpeq 수동 설치
https://www.gyan.dev/ffmpeg/builds/
다운로드 받은 파일안의 내용들(bin, doc, presets, LICENSE, README.txt)을 

C://ffmpeq/
경로에 안에 복사해서 넣기

powershell을 관리자 권한으로 실행(환경 변수 추가)
- [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\ffmpeg\bin", "User")

다시 powershell 창을 새로 켠 후 설치 확인
- ffmpeg -version

서버 실행
- uvicorn main:app --port=8081 --reload
