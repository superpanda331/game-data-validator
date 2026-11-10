"""AI용 표에 '계산 칸'과 '요약 통계'를 추가하는 도구. (2주차 보완 미션: 계산은 코드가, 판단은 AI가)

왜 필요한가?
    3차 실행에서 AI가 100 × 49^1.4 를 15,350으로 잘못 계산했다. (실제 약 23,240)
    → 계산은 코드가 하고, AI는 계산된 숫자를 보고 '판단'만 하게 만든다.
    사람이 엑셀로 검수할 때 수식 칸이나 피벗 테이블을 먼저 만드는 것과 같다.

확인 방법 (AI 호출 없이 무료로 확인):
    python ai_calc.py              # 오류 데이터로 계산 칸 확인
    python ai_calc.py --clean      # 정상 데이터로 계산 칸 확인

"""
import pandas as pd


# ── 미션 A: 몬스터 공식 칸 ──────────────────────────────────────
#   hp_공식값 = 100 × level^1.4,  exp_공식값 = 10 × level^1.2
#   *_공식대비% = 실제값 ÷ 공식값 × 100
# 확인: 오크 전사(9행) hp_공식대비% = 1251, 얼음 늑대(18행) = 6 / 정상 데이터는 89~110
# 학습 포인트: pandas는 칸 전체를 한 번에 계산함 (반복문 불필요)
#             "10레벨"처럼 글자가 섞인 칸은 pd.to_numeric(errors="coerce")로 먼저 숫자로 바꿔야 함
def add_monster_formula(view):
    view = view.copy()          # 원본 표를 건드리지 않도록 복사본에 작업

    level = pd.to_numeric(view["level"], errors="coerce")
    hp = pd.to_numeric(view["hp"], errors="coerce")
    exp = pd.to_numeric(view["exp"], errors="coerce")
    
    view["hp_공식값"] = (100 * level ** 1.4).round()
    view["hp_공식대비%"] = (hp / view["hp_공식값"] * 100).round()
    view["exp_공식값"] = (10 * level ** 1.2).round()
    view["exp_공식대비%"] = (exp / view["exp_공식값"] * 100).round()
    return view


# ── 미션 B: 같은 등급·종류의 가격 중앙값과 비율 ──────────────
#   같은등급종류_가격중앙값 = 같은 grade·type 아이템들의 price 중앙값
#   가격_중앙값대비%       = price ÷ 중앙값 × 100
# 확인: 낡은 투구(8행) = 750000, 태초의 검(46행) = 0 / 정상 데이터는 18~327
# 학습 포인트: groupby + transform — 묶어서 계산한 값을 원래 행마다 다시 붙임
#             평균 대신 중앙값: 이상치 하나가 평균을 크게 흔들기 때문
def add_price_ratio(view):
    view = view.copy()

    price = pd.to_numeric(view["price"],errors="coerce")

    view["같은등급종류_가격중앙값"] = price.groupby([view["grade"], view["type"]]).transform("median")
    view["가격_중앙값대비%"] = (price / view["같은등급종류_가격중앙값"] * 100).round()
    
    return view


# ── 미션 C: 요약 통계표 ──────────────────────────────────────────
# group_cols로 묶어서 value_col의 개수·중앙값·최소·최대를 계산하고 CSV 글자로 돌려준다.
#   예) DropGroup을 (아이템_종류, 아이템_등급)으로 묶으면 "방어구,전설 0.5"처럼 튀는 값이 한눈에 보임
# 학습 포인트: groupby + agg (엑셀 피벗 테이블), reset_index()로 그룹 이름을 일반 칸으로 꺼내기
def make_summary(view, group_cols, value_col):
    values = pd.to_numeric(view[value_col], errors="coerce")
    summary = values.groupby([view[c] for c in group_cols]).agg(["count", "median", "min", "max"])
    summary = summary.reset_index()
    
    return summary.to_csv(index=False, lineterminator="\n")


# ── 계산 칸 붙이기 / 테이블별 요약표 (제공 코드) ────────────
def add_calc_columns(views):
    """build_views()로 만든 표들에 계산 칸을 추가한다."""
    views["Monster"] = add_monster_formula(views["Monster"])
    views["Item"] = add_price_ratio(views["Item"])
    return views


SUMMARY_SPEC = {                                   # 테이블: (묶을 칸들, 요약할 값 칸)
    "Item": (["grade", "type"], "price"),
    "DropGroup": (["아이템_종류", "아이템_등급"], "drop_rate"),
}


def summary_text(table, view):
    """프롬프트에 넣을 요약 통계 글자. 요약 대상이 아니면 '(없음)'."""
    if table not in SUMMARY_SPEC:
        return "(없음)"
    group_cols, value_col = SUMMARY_SPEC[table]
    return make_summary(view, group_cols, value_col)


# ── 확인용 실행 (python ai_calc.py) ──────────────
if __name__ == "__main__":
    import sys
    from ai_views import build_views
    from common import CLEAN_DIR, ERROR_DIR, load_all

    pd.set_option("display.width", 250)
    folder = CLEAN_DIR if "--clean" in sys.argv else ERROR_DIR
    tables, _ = load_all(folder)
    views = add_calc_columns(build_views(tables))
    print(f"[{folder.name}]\n")
    print(views["Monster"].drop(columns=["name_key", "region", "atk", "defense"], errors="ignore").to_string(index=False))
    print()
    cols = [c for c in ["excel_row", "이름", "grade", "type", "price", "같은등급종류_가격중앙값", "가격_중앙값대비%"]
            if c in views["Item"].columns]
    print(views["Item"][cols].to_string(index=False))
    print("\n[DropGroup 요약]\n" + summary_text("DropGroup", views["DropGroup"]))
