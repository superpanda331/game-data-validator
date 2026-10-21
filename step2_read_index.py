"""2단계: Index 시트의 '용도' 문장에서 검증 규칙을 뽑아 본다.
여기서 뽑은 규칙이 1주차 규칙 기반 검증기의 재료가 된다."""
from common import ERROR_DIR, load_all

tables, indexes = load_all(ERROR_DIR)


# parse_rules 함수는 rules.py로 옮겼어요 (step4에서도 같이 쓰기 위해).
from rules import parse_rules


all_rules = {}
for name, ix in indexes.items():
    print(f"\n[{name}]")
    all_rules[name] = {}
    for _, r in ix.iterrows():
        rule = parse_rules(r["컬럼명"], r["자료형"], r["용도"])
        all_rules[name][r["컬럼명"]] = rule
        extra = {k: v for k, v in rule.items() if k != "type"}
        print(f"  {r['컬럼명']:<18} {r['자료형']:<7} {extra if extra else '(자료형만 확인)'}")

n = sum(len(v) for v in all_rules.values())
n_ref = sum("ref" in r for t in all_rules.values() for r in t.values())
print(f"\n총 {n}개 컬럼에서 규칙 추출 완료 (참조 관계 {n_ref}개)")
print("다음 단계: 이 규칙으로 실제 데이터를 검사하는 검증기를 만듭니다 (1주차).")
