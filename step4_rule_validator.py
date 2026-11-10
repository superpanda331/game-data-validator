"""4단계 (1주차): 규칙 기반 검증기

Index 시트에서 뽑은 규칙(rules.py)으로 데이터를 검사하고, 찾은 오류를 엑셀로 저장한다.

실행:
    python step4_rule_validator.py           # 오류 데이터(data_error) 검사
    python step4_rule_validator.py --clean   # 정상 데이터(data_clean) 검사 → 0건이어야 정상
채점:
    python evaluate.py output/rule_result.xlsx

학습 과정:
    - 1주차: 미션 1(빈 값 검사)을 예시로 보고, 미션 2~8을 직접 구현
    - 추가: Index 문장을 해석하는 조건부 규칙(미션 9) 구현
    - 3주차: 웹 화면에서 부를 수 있도록 validate_rules() 함수로 분리
"""
import sys
from pathlib import Path

import pandas as pd

from common import CLEAN_DIR, ERROR_DIR, ROOT, TYPE_RANGES, load_all
from rules import build_all_rules

# ── 오류 기록 ────────────────────────────────────────────────────────
errors = []                           # 찾은 오류를 여기에 모은다
COLUMNS = ["table", "excel_row", "column", "error_type", "value", "message"]


def add_error(table, row_idx, column, error_type, value, message):
    """오류 하나를 기록한다. row_idx는 pandas 행 번호(0부터) → 엑셀 행 번호로 바꿔서 저장."""
    errors.append({
        "table": table,
        "excel_row": row_idx + 2,     # pandas 0번 행 = 엑셀 2행 (1행은 헤더)
        "column": column,
        "error_type": error_type,
        "value": value,
        "message": message,
    })


def is_blank(v):
    """빈 칸이면 True. (엑셀 빈 칸은 pandas에서 NaN으로 읽힘)"""
    return pd.isna(v) or (isinstance(v, str) and v.strip() == "")


def is_int_value(v):
    """정수로 볼 수 있는 값이면 True. 예: 10 → True, 10.0 → True, 10.5 → False, "10" → False"""
    if isinstance(v, bool):
        return False
    return isinstance(v, int) or (isinstance(v, float) and v.is_integer())


# ── 미션 1 (예시로 제공): 빈 값 ──────────────────────────────
# 모든 칸에서 빈 값을 찾는다.
# 학습 포인트: df[col].items() 로 (행 번호, 값)을 하나씩 꺼내는 기본 반복 구조
def check_required(table, df):
    for col in df.columns:                    # 모든 컬럼을 돌면서
        for i, v in df[col].items():          # 그 컬럼의 (행 번호, 값)을 하나씩 꺼내
            if is_blank(v):                   # 비어 있으면
                add_error(table, i, col, "빈 값", v, f"{col} 값이 비어 있음")


# ── 미션 2: 중복 값 ──────────────────────────────────────────────
# Index에 "PK" 또는 "중복 불가"가 있는 컬럼은 같은 값이 두 번 나오면 안 된다. (두 번째부터 오류)
# 학습 포인트: duplicated(keep="first")는 칸 전체에 써야 한다 (값 하나에는 쓸 수 없음)
def check_unique(table, df, col):
    dup = df[col].duplicated(keep="first")

    for i, v in df[col].items():
        if dup[i] and not is_blank(v):
            add_error(table, i, col, "중복 값",v,f"{col} 값이 중복되어 있음")


# ── 미션 3: 자료형 ────────────────────────────────────────────────
#   int / long → 정수이고 TYPE_RANGES의 (최소, 최대) 안에 있어야 함
#   float      → 숫자이고 C# float 범위 안에 있어야 함 (게임 클라이언트 기준)
#   bool       → 0 또는 1이어야 함
#   string, enum → 자료형 검사 없음 (enum은 미션 4에서 확인)
# 학습 포인트: isinstance로 자료형 확인. 빈 값은 미션 1에서 잡으므로 건너뜀
def check_type(table, df, col, dtype):    
    for i, v in df[col].items():
        ok = True
        if is_blank(v) or dtype == "string" or dtype == "enum":
            continue
        elif dtype in ("int","long"):
            low, high = TYPE_RANGES[dtype]
            if not is_int_value(v) or v < low or v > high: ok = False
        elif dtype == "float":
            low, high = TYPE_RANGES[dtype]
            if not isinstance(v,(int,float)) or v < low or v > high: ok = False
        elif dtype == "bool":
            if not v in (0,1): ok = False

        if not ok:
            add_error(table, i, col, "자료형과 일치하지 않는 값 사용",v,f"{col}에 자료형과 일치하지 않는 값 '{v}' 사용")            


# ── 미션 4: 허용값 (enum) ──────────────────────────────────
# 값이 Index의 허용값 목록 안에 있어야 한다.
# 학습 포인트: "목록 안에 없다"는 v not in allowed
def check_allowed(table, df, col, allowed):
    for i, v in df[col].items():
        if v not in allowed and not is_blank(v):
            add_error(table, i, col, "허용되지 않은 값 사용",v,f"{col}에 허용되지 않은 값 '{v}' 사용")


# ── 미션 5: 범위 ──────────────────────────────────────────────────
# rule의 "range": (최소, 최대) 또는 "min": 최소 를 확인한다.
# "exclusive_min"이 True면 최솟값 자체도 허용하지 않는다. (예: drop_rate는 0 초과)
# 학습 포인트: rule.get()은 키가 없으면 None을 돌려줘서 안전하게 확인할 수 있음
def check_range(table, df, col, rule):
    for i, v in df[col].items():
        ok = True
        if not isinstance(v, (int, float)):
            continue
        elif rule.get("range") is not None: # range에 대한 코드 처리
            low, high = rule["range"]
            if rule.get("exclusive_min"):
                if v <= low or v > high:
                    ok = False
            else:
                if v < low or v > high:
                    ok = False
        elif rule.get("min") is not None:
            low = rule["min"]
            if v < low:
                ok = False

        if not ok:
            add_error(table, i, col, "범위에 맞지 않는 값 사용",v,f"{col}에 범위에 맞지 않는 값 {v} 사용")


# ── 미션 6: 참조 무결성 ──────────────────────────────────────────
# rule["ref"] = ("참조할 테이블", "참조할 컬럼") — 값이 그 테이블·컬럼에 실제로 있어야 한다.
# "zero_means_none"이 True면 0은 "참조 없음"으로 허용한다. (예: 선행 퀘스트 없음)
# 학습 포인트: 참조 대상 값을 set으로 모아 두면 "안에 있는지" 확인이 빠름
def check_ref(table, df, col, rule, tables):
    ref_table, ref_col = rule["ref"]
    valid = set(tables[ref_table][ref_col].dropna())
    
    for i, v in df[col].items():
        if is_blank(v):
            continue
        if rule.get("zero_means_none") and v == 0:
            continue
        if v not in valid:
            add_error(table, i, col, "참조되지 않는 값 사용", v, f"{col}에 참조되지 않는 값 {v} 사용")


# ── 미션 7: 키 형식 ──────────────────────────────────────────────
# rule["format"] = ("ITEM_NAME_", "item_id") 라면
# 값이 "ITEM_NAME_" + (같은 행의 item_id) 와 같아야 한다.
# 학습 포인트: df.at[i, 칸이름] 으로 같은 행의 다른 칸 값 꺼내기
def check_format(table, df, col, rule):
    rule_format, rule_col = rule["format"]
    for i, v in df[col].items():
        if is_blank(v):
            continue
        if v != (rule_format + str(df.at[i, rule_col])):
            add_error(table, i, col, "스트링 키 형식에 맞지 않는 값 사용", v, f"{col}에 스트링 키 형식에 맞지 않는 값 사용")


# ── 미션 8 (보너스): 컬럼 간 조건 ────────────────────────────
# rule["gte_col"] = "min_count" 라면, 이 컬럼(max_count) 값이 min_count 이상이어야 한다.
# 학습 포인트: 두 값이 모두 숫자일 때만 비교 (글자가 섞이면 비교 오류)
def check_gte_col(table, df, col, rule):
    rule_col = rule["gte_col"]
    for i, v in df[col].items():
        if is_blank(v):
            continue
        if isinstance(v,(int, float)) and isinstance(df.at[i, rule_col],(int, float)) :
            if v < df.at[i, rule_col] :
                add_error(table, i, col, "최소 값 데이터보다 최대 값 데이터에 더 작은 값 사용", v, f"{col}에 최소 값 {df.at[i, rule_col]}보다 작은 최대 값 {v} 사용")


# ── 미션 9 (추가): 조건부 값 ──────────────────────────────────
# rule["cond"] = ("type", {"무기": 1, "방어구": 1, "소모품": 99, "재료": 999}) 라면
# 같은 행의 type 값으로 정답을 찾아, 이 칸 값과 같은지 확인한다.
# 학습 포인트: 사전은 행 번호가 아니라 칸 안의 값(키)으로 찾는다 — values[key]
def check_cond(table, df, col, rule):
    cond_col, values = rule["cond"]
    for i, v in df[col].items():
        key = df.at[i, cond_col]
        if not isinstance(v,(int, float)) or key not in values:
            continue
        expected = values[key]
        if v != expected:
            add_error(table, i, col, "조건에 맞지 않는 값", v, f"{cond_col}이 {key}인 경우 {col}은 {expected} 이여야 함")


# ── 실행: 모든 테이블 × 모든 컬럼에 규칙 적용 ────────────────
# 3주차: 웹 화면에서 부를 수 있도록 함수로 분리
# 학습 포인트: 함수가 바깥 변수(tables, RULES)에 기대지 않고 매개변수로 받도록 정리,
#             errors.clear()로 버튼을 여러 번 눌러도 결과가 쌓이지 않게 함
def validate_rules(tables, indexes):
    errors.clear()
    rules = build_all_rules(indexes)

    for table, df in tables.items():
        check_required(table, df)
        for col, rule in rules[table].items():
            if rule.get("unique"):
                check_unique(table, df, col)
            check_type(table, df, col, rule["type"])
            if "allowed" in rule:
                check_allowed(table, df, col, rule["allowed"])
            if "range" in rule or "min" in rule:
                check_range(table, df, col, rule)
            if "ref" in rule:
                check_ref(table, df, col, rule, tables)
            if "format" in rule:
                check_format(table, df, col, rule)
            if "gte_col" in rule:
                check_gte_col(table, df, col, rule)
            if "cond" in rule:
                check_cond(table, df, col, rule)

    return pd.DataFrame(errors, columns=COLUMNS)

# ── 터미널에서 직접 실행할 때만: 결과 출력과 저장 ──────────────
if __name__ == "__main__" :
    folder = CLEAN_DIR if "--clean" in sys.argv else ERROR_DIR
    tables, indexes = load_all(folder)
    result = validate_rules(tables, indexes)

    print(f"검사 대상: {folder.name}")
    print(f"찾은 오류: {len(result)}건\n")
    if len(result):
        print(result["error_type"].value_counts().to_string())

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    out_name = "rule_result_clean.xlsx" if "--clean" in sys.argv else "rule_result.xlsx"
    result.to_excel(out_dir / out_name, index=False)
    print(f"\n저장: output/{out_name}")
