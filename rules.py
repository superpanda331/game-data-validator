"""Index 시트의 '용도' 문장에서 검증 규칙을 뽑는 함수 모음.
(step2_read_index.py에서 쓰던 parse_rules를 다른 파일에서도 쓸 수 있게 옮겨 둔 것)"""
import re


def parse_rules(col: str, dtype: str, use: str) -> dict:
    """용도 문장에서 기계가 읽을 수 있는 규칙만 뽑는다. 못 뽑은 내용은 AI가 판단할 몫."""
    rule = {"type": dtype}
    if "PK" in use or "중복 불가" in use:
        rule["unique"] = True
    m = re.search(r"(?:FK|참조 테이블)\s*→\s*(\w+)\.(\w+)", use)
    if m:
        rule["ref"] = (m.group(1), m.group(2))          # 예: ("Item", "item_id")
    m = re.search(r"허용값\s*:\s*([^\n]+)", use)
    if m:
        rule["allowed"] = [v.strip() for v in m.group(1).split("/")]
    m = re.search(r"범위\s*(\d+)\s*~\s*(\d+)", use)
    if m:
        rule["range"] = (int(m.group(1)), int(m.group(2)))
    m = re.search(r"(\d+)\s*이상", use)
    if m and "range" not in rule:
        rule["min"] = int(m.group(1))
    if "양의 정수" in use and "min" not in rule:
        rule["min"] = 1                               # 양의 정수 = 1 이상
    m = re.search(r"([a-z]+_[a-z_]+)\s*이상", use)
    if m and m.group(1) != col:
        rule["gte_col"] = m.group(1)                  # 예: max_count는 "min_count 이상"
    m = re.search(r"형식\s*:\s*([A-Z_]+)\{(\w+)\}", use)
    if m:
        rule["format"] = (m.group(1), m.group(2))     # 예: ("ITEM_NAME_", "item_id")
    if "0 초과 1 이하" in use:
        rule["range"] = (0, 1)
        rule["exclusive_min"] = True                  # 0은 안 됨 (0 초과)
    if "없으면 0" in use:
        rule["zero_means_none"] = True                # 0 = "참조 없음" (참조 검사에서 제외)
    return rule


def build_all_rules(indexes: dict) -> dict:
    """{테이블명: {컬럼명: 규칙}} 형태로 모든 규칙을 만든다."""
    return {
        name: {r["컬럼명"]: parse_rules(r["컬럼명"], r["자료형"], r["용도"]) for _, r in ix.iterrows()}
        for name, ix in indexes.items()
    }
