"""검증 결과를 정답표와 비교해 탐지율을 계산한다. (채점 도구 — 직접 고칠 필요 없음)

사용법:  python evaluate.py output/rule_result.xlsx
판정 기준: 같은 테이블의 같은 행(excel_row)을 오류로 짚었으면 '찾음'으로 본다.
"""
import sys
import pandas as pd
from common import DATA_DIR

result_path = sys.argv[1] if len(sys.argv) > 1 else "output/rule_result.xlsx"
ans = pd.read_excel(DATA_DIR / "answer_key.xlsx", sheet_name="정답표").dropna(subset=["category"])
res = pd.read_excel(result_path)

found_rows = set(zip(res["table"], res["excel_row"]))
ans["찾음"] = [(t, r) in found_rows for t, r in zip(ans["table"], ans["excel_row"])]
answer_rows = set(zip(ans["table"], ans["excel_row"]))
false_pos = res[[(t, r) not in answer_rows for t, r in zip(res["table"], res["excel_row"])]]

total, hit = len(ans), int(ans["찾음"].sum())
print(f"\n📊 전체 탐지율: {hit}/{total} ({hit / total:.0%})\n")
print("분류별 탐지율")
for cat, g in ans.groupby("category"):
    print(f"  {cat:<4}: {int(g['찾음'].sum())}/{len(g)}")

print(f"\n오탐 (정답표에 없는 행을 오류로 판단): {len(false_pos)}건")
if len(false_pos):
    print(false_pos.to_string(index=False))

missed = ans[~ans["찾음"]][["error_id", "table", "excel_row", "column", "category", "description"]]
print(f"\n놓친 오류 {len(missed)}건")
print(missed.to_string(index=False))
