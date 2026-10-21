"""0단계: 개발 환경이 제대로 준비됐는지 확인한다."""
import importlib
import os
import sys
from pathlib import Path

ok = True
print(f"Python 버전: {sys.version.split()[0]}", "✅" if sys.version_info >= (3, 10) else "❌ 3.10 이상 필요")
ok &= sys.version_info >= (3, 10)

for pkg, mod in [("pandas", "pandas"), ("openpyxl", "openpyxl"), ("google-genai", "google.genai"), ("python-dotenv", "dotenv")]:
    try:
        importlib.import_module(mod)
        print(f"패키지 {pkg}: ✅")
    except ImportError:
        print(f"패키지 {pkg}: ❌  →  pip install -r requirements.txt")
        ok = False

root = Path(__file__).parent
for d in ["data/data_error", "data/data_clean"]:
    n = len(list((root / d).glob("*.xlsx")))
    print(f"{d}: 엑셀 {n}개", "✅" if n else "❌ 데이터 폴더를 확인하세요")
    ok &= n > 0

try:
    from dotenv import load_dotenv
    load_dotenv(root / ".env")
except ImportError:
    pass
key = os.getenv("GEMINI_API_KEY", "")
print("Gemini API 키:", "✅ 설정됨" if key and "여기에" not in key else "⚠️ 아직 없음 (.env 파일에 넣어 주세요. 3단계 전까지만 하면 됩니다)")

print("\n" + ("🎉 기본 환경 준비 완료! step1_load_tables.py 를 실행해 보세요." if ok else "❌ 위 항목을 먼저 해결해 주세요."))
