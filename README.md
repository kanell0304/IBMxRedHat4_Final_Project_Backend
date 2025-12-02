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