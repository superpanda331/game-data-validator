"""4단계 (1주차): 규칙 기반 검증기

Index 시트에서 뽑은 규칙(rules.py)으로 데이터를 검사하고, 찾은 오류를 엑셀로 저장한다.

실행:
    python step4_rule_validator.py           # 오류 데이터(data_error) 검사
    python step4_rule_validator.py --clean   # 정상 데이터(data_clean) 검사 → 0건이어야 정상
채점:
    python evaluate.py output/rule_result.xlsx

진행 방법:
    - 미션 1(check_required)은 예시로 완성돼 있어요. 이걸 보고 나머지 미션을 채우세요.
    - 아직 안 채운 함수는 `pass`(아무것도 안 함) 상태라서, 언제 실행해도 프로그램은 돌아가요.
    - 미션 하나를 끝낼 때마다 실행해서 찾은 개수가 '목표'와 같은지 확인하세요.
"""
import sys
from pathlib import Path

import pandas as pd

from common import CLEAN_DIR, ERROR_DIR, ROOT, TYPE_RANGES, load_all
from rules import build_all_rules

# ── 준비: 데이터와 규칙 읽기 ─────────────────────────────────────────
folder = CLEAN_DIR if "--clean" in sys.argv else ERROR_DIR
tables, indexes = load_all(folder)
RULES = build_all_rules(indexes)      # 예: RULES["Item"]["grade"] → {"type": "enum", "allowed": [...]}

errors = []                           # 찾은 오류를 여기에 모은다


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


# ── 미션 1 (예시, 완성됨): 빈 값 검사 ────────────────────────────────
# 목표: 오류 데이터에서 4건
def check_required(table, df):
    for col in df.columns:                    # 모든 컬럼을 돌면서
        for i, v in df[col].items():          # 그 컬럼의 (행 번호, 값)을 하나씩 꺼내
            if is_blank(v):                   # 비어 있으면
                add_error(table, i, col, "빈 값", v, f"{col} 값이 비어 있음")


# ── 미션 2: 중복 검사 ───────────────────────────────────────────────
# 목표: 3건
# 규칙: Index에 "PK" 또는 "중복 불가"가 있는 컬럼은 같은 값이 두 번 나오면 안 됨
# 힌트: df[col].duplicated(keep="first") 는 "앞에서 이미 나온 값이면 True"인 목록을 돌려줘요.
#       첫 번째로 나온 행은 정상, 두 번째부터 오류로 기록하면 돼요.
#       빈 값(NaN)은 미션 1에서 이미 잡으니 제외하세요.
def check_unique(table, df, col):
    dup = df[col].duplicated(keep="first")

    for i, v in df[col].items():
        if dup[i] and not is_blank(v):
            add_error(table, i, col, "중복 값",v,f"{col} 값이 중복되어 있음")




# ── 미션 3: 자료형 검사 ─────────────────────────────────────────────
# 목표: 6건
# 규칙:
#   int / long → is_int_value(v)가 True이고, TYPE_RANGES[dtype]의 (최소, 최대) 안에 있어야 함
#   float      → 숫자(int 또는 float)여야 함
#   bool       → 0 또는 1이어야 함
#   string, enum → 이 미션에서는 검사하지 않음
# 힌트: 빈 값은 건너뛰세요 (if is_blank(v): continue)
#       TYPE_RANGES["int"] 는 (-2147483648, 2147483647) 이에요.
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




# ── 미션 4: 허용값(enum) 검사 ───────────────────────────────────────
# 목표: 2건
# 규칙: 값이 allowed 목록 안에 있어야 함
# 힌트: 파이썬에서 "목록 안에 없다"는  v not in allowed  로 써요.
def check_allowed(table, df, col, allowed):
    for i, v in df[col].items():
        if v not in allowed and not is_blank(v):
            add_error(table, i, col, "허용되지 않은 값 사용",v,f"{col}에 허용되지 않은 값 '{v}' 사용")


# ── 미션 5: 범위 검사 ───────────────────────────────────────────────
# 목표: 5건
# 규칙: rule에 "range": (최소, 최대) 또는 "min": 최소 가 들어 있어요.
#       rule.get("exclusive_min")이 True면 최솟값 자체도 안 됨 (예: drop_rate는 0 초과)
# 힌트: 숫자가 아닌 값(문자열 등)은 미션 3에서 잡으니 건너뛰세요.
#       isinstance(v, (int, float)) 로 숫자인지 확인할 수 있어요.
#       rule.get("min") 은 "min"이 없으면 None을 돌려줘요.
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


# ── 미션 6: 참조 무결성 검사 ────────────────────────────────────────
# 목표: 11건
# 규칙: rule["ref"] = ("참조할 테이블", "참조할 컬럼")
#       값이 그 테이블·컬럼에 실제로 있어야 함
#       rule.get("zero_means_none")이 True면 0은 "참조 없음"이라 정상 (예: 선행 퀘스트 없음)
# 힌트: 참조 대상의 값 목록은  set(tables[ref_table][ref_col].dropna())  로 만들 수 있어요.
#       set은 "중복 없는 값 모음"이고, 안에 있는지 찾는 속도가 아주 빨라요.
def check_ref(table, df, col, rule): # 여기서 부터 수정 작업 필요
    ref_table, ref_col = rule["ref"]
    valid = set(tables[ref_table][ref_col].dropna())
    
    for i, v in df[col].items():
        if is_blank(v):
            continue
        if rule.get("zero_means_none") and v == 0:
            continue
        if v not in valid:
            add_error(table, i, col, "참조되지 않는 값 사용", v, f"{col}에 참조되지 않는 값 {v} 사용")

            


# ── 미션 7: 키 형식 검사 ────────────────────────────────────────────
# 목표: 6건
# 규칙: rule["format"] = ("ITEM_NAME_", "item_id") 라면
#       그 행의 값이 "ITEM_NAME_" + (같은 행의 item_id) 와 같아야 함
# 힌트: 같은 행의 다른 컬럼 값은  df.at[i, "item_id"]  로 꺼내요.
#       f"{prefix}{df.at[i, id_col]}" 로 기대값을 만들어 비교하세요.
def check_format(table, df, col, rule):
    #print(table,rule)
    rule_format, rule_col = rule["format"]
    for i, v in df[col].items():
        if is_blank(v):
            continue
        if v != (rule_format + str(df.at[i, rule_col])):
            add_error(table, i, col, "스트링 키 형식에 맞지 않는 값 사용", v, f"{col}에 스트링 키 형식에 맞지 않는 값 사용")
        #print(i, f"데이터 : {v}", rule_format, f"동일 행의 아이템 아이디 : {df.at[i, rule_col]}")


# ── 미션 8 (보너스): 컬럼 간 조건 검사 ─────────────────────────────
# 목표: 1건
# 규칙: rule["gte_col"] = "min_count" 라면, 이 컬럼(max_count) 값이 min_count 이상이어야 함
# 힌트: 두 값이 모두 숫자일 때만 비교하세요. 오류는 min_count 컬럼 쪽으로 기록해도 돼요.
def check_gte_col(table, df, col, rule):
    rule_col = rule["gte_col"]
    #print("로그 확인 ", rule_col)
    for i, v in df[col].items():
        if is_blank(v):
            continue
        if isinstance(v,(int, float)) and isinstance(df.at[i, rule_col],(int, float)) :
            if v < df.at[i, rule_col] :
                add_error(table, i, col, "최소 값 데이터보다 최대 값 데이터에 더 작은 값 사용", v, f"{col}에 최소 값 {df.at[i, rule_col]}보다 작은 최대 값 {v} 사용")



# ── 실행: 모든 테이블 × 모든 컬럼에 규칙 적용 (이미 완성) ──────────────
for table, df in tables.items():
    check_required(table, df)
    for col, rule in RULES[table].items():
        if rule.get("unique"):
            check_unique(table, df, col)
        check_type(table, df, col, rule["type"])
        if "allowed" in rule:
            check_allowed(table, df, col, rule["allowed"])
        if "range" in rule or "min" in rule:
            check_range(table, df, col, rule)
        if "ref" in rule:
            check_ref(table, df, col, rule)
        if "format" in rule:
            check_format(table, df, col, rule)
        if "gte_col" in rule:
            check_gte_col(table, df, col, rule)

# ── 결과 출력과 저장 ─────────────────────────────────────────────────
result = pd.DataFrame(errors, columns=["table", "excel_row", "column", "error_type", "value", "message"])
print(f"검사 대상: {folder.name}")
print(f"찾은 오류: {len(result)}건\n")
if len(result):
    print(result["error_type"].value_counts().to_string())

out_dir = ROOT / "output"
out_dir.mkdir(exist_ok=True)
out_name = "rule_result_clean.xlsx" if "--clean" in sys.argv else "rule_result.xlsx"
result.to_excel(out_dir / out_name, index=False)
print(f"\n저장: output/{out_name}")
