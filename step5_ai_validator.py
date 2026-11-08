"""5단계 (2주차): AI 검증기

규칙 검증기(step4)가 놓친 '맥락이 필요한 오류'를 Gemini로 찾는다.
    예) 레벨 대비 HP가 튀는 몬스터, 등급에 안 맞는 가격, 무기인데 물약 설명, 오타 ...

실행:
    python step5_ai_validator.py --dry      # AI를 부르지 않고 프롬프트만 출력 (무료, 먼저 이걸로 확인!)
    python step5_ai_validator.py            # 오류 데이터(data_error) 검사
    python step5_ai_validator.py --clean    # 정상 데이터(data_clean) 검사 → 오탐 확인
채점:
    python evaluate.py output/combined_result.xlsx     # 규칙 + AI 합친 결과
    python evaluate.py output/ai_result.xlsx           # AI 결과만

진행 방법:
    미션 1 → --dry 로 프롬프트 확인 → 미션 2 → 미션 3 → 실행 → 채점 → 미션 4(프롬프트 개선) 반복
"""
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

from ai_views import build_views, to_source
from common import CLEAN_DIR, ERROR_DIR, ROOT, load_all

from ai_calc import add_calc_columns, summary_text

# ── 준비 ─────────────────────────────────────────────────────────────
load_dotenv(ROOT / ".env")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
AI_TABLES = ["Item", "Monster", "DropGroup", "Quest", "Reward"]
COLUMNS = ["table", "excel_row", "column", "error_type", "value", "message"]

TYPE_RANGE_TEXT = "int: -2,147,483,648 ~ 2,147,483,647 / long: 64비트 정수 / float: C# float(32비트) / bool: 0 또는 1"


# ── 미션 1: 프롬프트 만들기 ───────────────────────────────────────────
# 목표: AI에게 보낼 질문(문자열)을 만든다.
# 재료:
#   index_df : 이 테이블의 Index 시트 (컬럼명 / 자료형 / 용도)
#   view     : AI용 표 (excel_row 칸이 맨 앞에 있음)
# 프롬프트에 들어가야 할 것 (순서대로):
#   ① 역할:   "너는 게임 기획 데이터 검증 담당자야" 같은 한 줄
#   ② 명세:   Index 내용  → step3에서 만든 방식 그대로: "- 컬럼명 (자료형): 용도" 줄들
#   ③ 데이터: view 내용  → view.to_csv(index=False) 하면 표가 CSV 글자로 바뀌어요
#   ④ 요청:   무엇을 찾아야 하는지 (같은 등급·레벨대 다른 행과 비교해 튀는 값, 이름·설명이 맞지 않는 것, 오타 등)
#   ⑤ 출력 형식: 반드시 아래 JSON 배열로만 답하게 하기
#       [{"excel_row": 숫자, "column": "컬럼명", "reason": "이유"}]
#       오류가 없으면 []
# 힌트: 여러 줄 문자열은 f\"\"\" ... \"\"\" 로 쓰고, 안에 {변수}를 넣을 수 있어요.
#       TYPE_RANGE_TEXT도 명세에 같이 넣어 주면 좋아요.
def make_prompt(table, index_df, view):
    spec_text = "\n".join(f"- {r.컬럼명} ({r.자료형}): {r.용도}" for r in index_df.itertuples())
    data_text = view.to_csv(index=False,lineterminator="\n")

    prompt = f"""너는 게임 기획 데이터 검증 담당자야. {table} 테이블을 검사해 줘.

[자료형 범위]
{TYPE_RANGE_TEXT}

[컬럼 명세]
{spec_text}

[데이터]
{data_text}

[찾아야 할 것]
- 명세(자료형, 범위, 허용값, 조건)를 어긴 값
- 같은 등급·종류·레벨대의 다른 행과 비교해 지나치게 튀는 값
- 이름과 설명이 올바르게 매칭되지 않는 값
- 텍스트의 형태에서 오탈자로 판단되는 값

[판단 기준]
- index 시트에 있는 공식은 대략적인 내용으로 +(-) 25% 이내의 수치는 무시(그것보다 큰 수치는 오류로 판단)
    ㄴ 가격_중앙값대비%의 경우 15미만이거나 330초과 인경우 오류로 판단(해당 항목에 대하여 +- 25%는 적용하지 않음)
- 이름, 설명 텍스트가 문제인 경우 'column' 영역에 이름 또는 설명으로 작성
- 다른 행의 오류로 인해 문제가 발생된 것으로 판단되는 행은 보고하지 않고 원인이 되는 행만 보고
- OO대비% 등의 계산을 제공한 경우 해당 데이터를 참조하여 판단
- column에는 틀린 값이 실제로 들어 있는 칸을 적음 (오타가 이름에 있으면 이름)
- 퀘스트 이름과 처치 대상이 맞지 않으면 이름을 오류로 보고
- 한 항목에는 한 가지 문제만 적음. 한 행에 문제가 여러 개면 항목을 나눠서 보고

[참고 통계]
{summary_text(table, view)}

[출력 형식]
아래 JSON 배열로만 답해. 오류가 없으면 [] 로 답해.
[{{"excel_row": 숫자, "column": "컬럼명", "reason": "이유"}}]
"""
    return prompt


# ── 미션 2: AI 호출하고 JSON 읽기 ────────────────────────────────────
# 목표: prompt를 보내고, 돌아온 JSON 글자를 파이썬 리스트로 바꿔서 돌려준다.
# 힌트:
#   reply = client.models.generate_content(
#       model=MODEL,
#       contents=prompt,
#       config=types.GenerateContentConfig(
#           response_mime_type="application/json",   # "JSON으로만 답해" 강제
#           temperature=0,                           # 매번 최대한 같은 답 (재현성)
#       ),
#   )
#   reply.text 는 '[{"excel_row": 9, ...}]' 같은 글자예요.
#   json.loads(글자) 를 하면 파이썬 리스트로 바뀌어요.
#   AI가 형식을 어기면 json.loads에서 오류가 나요 → try / except 로 잡아서 빈 리스트 [] 를 돌려주세요.
def ask_ai(client, prompt):
    try:
        reply = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",   # "JSON으로만 답해" 강제
                temperature=0,                           # 매번 최대한 같은 답 (재현성)
            ),
        )
        items = json.loads(reply.text)
        if not isinstance(items, list):
            print("\n Ai 처리 실패 : 목록 형식이 아님")
            return None
        # print(reply.text)
        return items
    except Exception as e:
        print(f"\n Ai 처리 실패 : {e}")
        return None

    


# ── 미션 3: AI 답 검증하기 ────────────────────────────────────────────
# 목표: AI가 준 항목 중 '말이 되는 것'만 골라 결과 목록(found)에 담는다.
#       AI는 가끔 없는 행 번호나 없는 컬럼을 지어내요. 그대로 믿으면 안 돼요!
# 할 일 (항목 item 하나마다):
#   ① item에서 excel_row, column, reason 꺼내기   (item.get("excel_row") 처럼)
#   ② excel_row가 view["excel_row"] 안에 있는 숫자인지 확인 → 아니면 건너뛰기
#   ③ column이 view.columns 안에 있는지 확인          → 아니면 건너뛰기
#   ④ to_source(tables, table, excel_row, column) 으로 원본 위치로 바꾸기
#        (뷰의 '이름'·'설명' 칸은 실제로 StringTable에 있으니까요)
#   ⑤ found.append({...}) 로 저장
#        키: "table", "excel_row", "column", "error_type"("AI 판단"), "value"(원래 값), "message"(reason)
#        원래 값은 view에서 꺼내도 돼요:  view.loc[view["excel_row"] == excel_row, column].iloc[0]
# 힌트: 숫자가 아닌 excel_row(예: "9행")가 올 수도 있어요. isinstance(excel_row, int) 로 먼저 확인!
def check_ai_items(tables, table, view, items):
    found = []
    for item in items:
        excel_row = item.get("excel_row")
        column = item.get("column")
        reason = item.get("reason")

        if not isinstance(excel_row, int):
            continue
        if excel_row not in set(view["excel_row"]):
            continue
        if column not in view.columns:
            continue
        src_table, src_row, src_col = to_source(tables, table, excel_row, column)
        value = view.loc[view["excel_row"] == excel_row, column].iloc[0]

        found.append({"table" : src_table, "excel_row" : src_row, "column" : src_col, "error_type" : "AI 판단", "value" : value, "message" : reason})
    return found

# ── 실행 (이미 완성) ─────────────────────────────────────────────────
def validate_ai(tables, indexes, api_key=None):
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API 키가 없습니다. 화면에 키를 입력바랍니다.")
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=60_000),   # 60초 (단위: 밀리초)
    )
    views = add_calc_columns(build_views(tables))

    all_found = []
    failed = []                                              # 실패한 테이블 이름
    for table in AI_TABLES:
        prompt = make_prompt(table, indexes[table], views[table])
        print(f"[{table}] AI 검사 중...", end=" ", flush=True)
        items = ask_ai(client ,prompt)
        if items is None:
            failed.append(table)
            continue
        found = check_ai_items(tables, table, views[table], items)
        print(f"AI 답 {len(items)}건 → 검증 통과 {len(found)}건")
        all_found.extend(found)
        time.sleep(2)                        # 무료 요금제 호출 제한을 피하려고 잠깐 쉬기

    ai_df = pd.DataFrame(all_found, columns=COLUMNS)
    ai_df["source"] = "AI"
    return ai_df, failed


# ── 저장: AI 결과 / 규칙 + AI 합친 결과 ──────────────────────────────
if __name__ == "__main__":
    DRY_RUN = "--dry" in sys.argv
    CLEAN = "--clean" in sys.argv
    folder = CLEAN_DIR if CLEAN else ERROR_DIR
    tables, indexes = load_all(folder)

    if DRY_RUN:
        views = add_calc_columns(build_views(tables))
        for table in AI_TABLES:
            prompt = make_prompt(table, indexes[table], views[table])
            print(f"\n{'=' * 30} [{table}] 프롬프트 ({len(prompt)}자) {'=' * 30}\n{prompt}")
        sys.exit()

    ai_df, failed = validate_ai(tables, indexes)
    if failed:
        print(f"\n⚠️ AI 검사 실패: {', '.join(failed)}")

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    suffix = "_clean" if CLEAN else ""


    ai_df.to_excel(out_dir / f"ai_result{suffix}.xlsx", index=False)

    rule_path = out_dir / f"rule_result{suffix}.xlsx"
    if rule_path.exists():
        rule_df = pd.read_excel(rule_path)
        rule_df["source"] = "규칙"
        combined = pd.concat([rule_df, ai_df], ignore_index=True)
        combined.to_excel(out_dir / f"combined_result{suffix}.xlsx", index=False)
        print(f"\n규칙 {len(rule_df)}건 + AI {len(ai_df)}건 → output/combined_result{suffix}.xlsx")
    else:
        print(f"\n⚠️ {rule_path.name}이 없어요. 먼저 step4_rule_validator.py{' --clean' if CLEAN else ''} 를 실행하세요.")
    print(f"AI 결과: output/ai_result{suffix}.xlsx")
