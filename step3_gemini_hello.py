"""3단계: Gemini API 연결을 확인하고, AI에게 Index 시트를 읽혀 본다."""
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from common import ERROR_DIR, load_index

load_dotenv(Path(__file__).parent / ".env")
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

if not API_KEY or "여기에" in API_KEY:
    raise SystemExit("❌ .env 파일에 GEMINI_API_KEY를 넣어 주세요. (README의 'API 키 발급' 참고)")

client = genai.Client(api_key=API_KEY)

# 1) 연결 확인
try:
    reply = client.models.generate_content(model=MODEL, contents="한 문장으로 인사해 줘.")
except Exception as e:
    print(f"❌ 호출 실패: {e}\n")
    print("사용 가능한 모델 목록 (이 중 하나를 .env의 GEMINI_MODEL에 넣어 보세요):")
    for m in client.models.list():
        if "generateContent" in (m.supported_actions or []):
            print("  -", m.name.replace("models/", ""))
    raise SystemExit(1)
print(f"✅ 연결 성공 ({MODEL}): {reply.text.strip()}\n")

# 2) AI에게 Index 시트를 읽히고 검증 포인트를 정리하게 하기
ix = load_index("Item", ERROR_DIR)
index_text = "\n".join(f"- {r.컬럼명} ({r.자료형}): {r.용도}" for r in ix.itertuples())
prompt = f"""너는 게임 데이터 검증 담당자야.
아래는 Item 테이블의 Index(컬럼 명세)야. 자료형 범위: int는 -2,147,483,648~2,147,483,647, long은 64비트 정수.

{index_text}

이 명세를 기준으로, 데이터를 검사할 때 확인해야 할 항목을 컬럼별로 한 줄씩 정리해 줘."""
reply = client.models.generate_content(model=MODEL, contents=prompt)
print("🤖 AI가 정리한 Item 검증 포인트:\n")
print(reply.text)
