# 게임 데이터 검증 AI

게임 기획 데이터 테이블의 잘못된 값을 **규칙 + AI**로 찾아내는 도구.

## 폴더 구조

```
game-data-validator/
├─ data/
│  ├─ data_error/      검증 대상 (오류를 심은 버전)
│  ├─ data_clean/      정상 버전 (오탐 확인용)
│  └─ answer_key.xlsx  정답표 (검증기를 다 만든 뒤에 열어 보기)
├─ common.py           테이블·Index 읽기 공통 함수
├─ step0_check_env.py  환경 점검
├─ step1_load_tables.py  테이블 읽기 + 형식 점검
├─ step2_read_index.py   Index 시트에서 규칙 추출
├─ step3_gemini_hello.py Gemini 연결 + AI에게 Index 읽히기
├─ requirements.txt
└─ .env.example        API 키 설정 예시
```

## 처음 세팅 (Windows 기준, 한 번만)

1. **Python 설치**: https://www.python.org/downloads/ 에서 3.12 이상 설치
   - 설치 첫 화면에서 **"Add python.exe to PATH" 체크** (꼭!)
2. **VS Code 설치**: https://code.visualstudio.com/ → 실행 후 왼쪽 확장(Extensions)에서 **Python** 설치
3. 이 폴더를 원하는 위치에 압축 해제 → VS Code에서 **파일 > 폴더 열기**로 이 폴더 열기
4. VS Code 상단 메뉴 **터미널 > 새 터미널** 열고 아래를 한 줄씩 실행

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python step0_check_env.py
```

> `activate`에서 "스크립트를 실행할 수 없습니다" 오류가 나면 아래를 한 번 실행한 뒤 다시 시도:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

> 터미널 줄 앞에 `(.venv)`가 보이면 가상환경이 켜진 상태. VS Code를 새로 열면 `.venv\Scripts\activate`를 다시 실행.

## Gemini API 키 발급

1. https://aistudio.google.com/ 접속 → Google 계정 로그인
2. **Get API key → Create API key** 클릭 → 키 복사
3. 이 폴더의 `.env.example` 파일을 복사해 이름을 **`.env`** 로 변경
4. `.env` 안의 `여기에_API_키를_붙여_넣으세요` 부분을 복사한 키로 교체

> `.env`는 GitHub에 올리지 않기. (`.gitignore`에 이미 제외 처리됨).

## 실행 순서

```powershell
python step0_check_env.py      # 환경 점검 → 전부 ✅ 인지 확인
python step1_load_tables.py    # 6개 테이블 읽기 + Index 형식 점검
python step2_read_index.py     # Index 용도 문장에서 규칙 추출
python step3_gemini_hello.py   # Gemini 연결 + AI가 Index 읽고 검증 포인트 정리
```

- step3에서 모델 오류가 나면 화면에 나오는 **사용 가능한 모델 목록** 중 하나를 `.env`의 `GEMINI_MODEL`에 넣고 다시 실행.
