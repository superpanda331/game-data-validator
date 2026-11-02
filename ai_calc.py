"""AI용 표에 '계산 칸'과 '요약 통계'를 추가하는 도구. (2주차 보완 미션)

왜 필요한가?
    3차 실행에서 AI가 100 × 49^1.4 를 15,350으로 잘못 계산했어요. (실제 약 23,240)
    → 계산은 코드가 하고, AI는 계산된 숫자를 보고 '판단'만 하게 만들어요.
    사람이 엑셀로 검수할 때 수식 칸이나 피벗 테이블을 먼저 만드는 것과 같아요.

확인 방법 (AI 호출 없이 무료로 확인):
    python ai_calc.py              # 오류 데이터로 계산 칸 확인
    python ai_calc.py --clean      # 정상 데이터로 계산 칸 확인

미션을 다 채운 뒤, step5_ai_validator.py 에 연결하는 방법은 맨 아래 설명을 보세요.
"""
import pandas as pd


# ── 미션 A: 몬스터 공식 칸 ────────────────────────────────────────────
# 목표: Monster 표에 4개 칸을 추가한다.
#   hp_공식값     = 100 × level^1.4     (반올림)
#   hp_공식대비%  = hp ÷ hp_공식값 × 100 (반올림)
#   exp_공식값    = 10 × level^1.2      (반올림)
#   exp_공식대비% = exp ÷ exp_공식값 × 100 (반올림)
#
# 핵심 개념 1: 칸 전체를 한 번에 계산하기
#   엑셀에서 수식을 맨 아래까지 드래그하듯, pandas는 칸 전체에 한 번에 계산돼요. 반복문이 필요 없어요.
#     view["새칸"] = view["A칸"] * 2        ← 모든 행이 한 번에 계산됨
#   거듭제곱은 **  (예: level ** 1.4),  반올림은 .round()
#
# 핵심 개념 2: 잘못된 값이 섞인 칸을 숫자로 바꾸기
#   level 칸에는 "10레벨" 같은 글자가 섞여 있어서 그대로 계산하면 오류가 나요.
#     level = pd.to_numeric(view["level"], errors="coerce")
#   errors="coerce" 는 "숫자로 못 바꾸는 값은 빈 값(NaN)으로 둬라"는 뜻이에요.
#   hp, exp 칸도 같은 방법으로 숫자로 바꿔서 쓰세요.
#
# 자가 확인 (오류 데이터): 오크 전사(9행) hp_공식대비% = 1251, 얼음 늑대(18행) = 6
#                         정상 데이터는 모든 % 가 89~110 사이
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


# ── 미션 B: 같은 등급·종류의 가격 중앙값과 비율 ──────────────────────
# 목표: Item 표에 2개 칸을 추가한다.
#   같은등급종류_가격중앙값 = 같은 grade·type 아이템들의 price 중앙값
#   가격_중앙값대비%       = price ÷ 같은등급종류_가격중앙값 × 100 (반올림)
#
# 핵심 개념: groupby + transform
#   엑셀 피벗처럼 '묶어서' 계산하되, 결과를 원래 행마다 다시 붙여 주는 방법이에요.
#     price.groupby([view["grade"], view["type"]]).transform("median")
#   → 행마다 "자기와 같은 grade·type 그룹의 중앙값"이 들어간 칸이 만들어져요.
#   (평균 대신 중앙값을 쓰는 이유: 이상치 하나가 평균을 크게 흔들기 때문이에요)
#   price 칸에도 "12,040" 같은 글자가 있으니 미션 A처럼 먼저 숫자로 바꾸세요.
#
# 자가 확인 (오류 데이터): 낡은 투구(8행) = 750000, 태초의 검(46행) = 0
#                         정상 데이터는 18~327 사이
def add_price_ratio(view):
    view = view.copy()

    price = pd.to_numeric(view["price"],errors="coerce")

    view["같은등급종류_가격중앙값"] = price.groupby([view["grade"], view["type"]]).transform("median")
    view["가격_중앙값대비%"] = (price / view["같은등급종류_가격중앙값"] * 100).round()
    
    return view


# ── 미션 C: 요약 통계표 만들기 ────────────────────────────────────────
# 목표: group_cols로 묶어서 value_col의 개수·중앙값·최소·최대를 계산하고, CSV 글자로 돌려준다.
#   예) DropGroup을 (아이템_등급, 아이템_종류)로 묶어 drop_rate 요약
#       아이템_등급,아이템_종류,count,median,min,max
#       전설,무기,1,0.002,0.002,0.002
#       전설,방어구,1,0.5,0.5,0.5          ← 한눈에 튀는 값이 보여요
#
# 핵심 개념: groupby + agg  (엑셀 피벗 테이블 그 자체)
#     values.groupby([view[c] for c in group_cols]).agg(["count", "median", "min", "max"])
#   → 그룹마다 한 줄씩 요약된 표가 나와요.
#   그다음 .reset_index() 로 그룹 이름을 일반 칸으로 꺼내고,
#   .to_csv(index=False, lineterminator="\n") 로 글자로 바꾸면 돼요. (미션 1에서 쓴 방법!)
#   value_col 칸도 미션 A처럼 먼저 숫자로 바꾸세요.
def make_summary(view, group_cols, value_col):
    values = pd.to_numeric(view[value_col], errors="coerce")
    summary = values.groupby([view[c] for c in group_cols]).agg(["count", "median", "min", "max"])
    summary = summary.reset_index()
    
    return summary.to_csv(index=False,lineterminator="\n")  # TODO


# ── 이미 완성: 계산 칸 붙이기 / 테이블별 요약표 ──────────────────────
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


# ── 자가 확인용 실행 (python ai_calc.py) ─────────────────────────────
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


# ── 다 채운 뒤: step5_ai_validator.py 에 연결하기 (세 군데 수정) ─────
# ① import 추가 (파일 위쪽)
#       from ai_calc import add_calc_columns, summary_text
# ② views 만드는 줄 바꾸기
#       views = add_calc_columns(build_views(tables))
# ③ make_prompt 안에 요약표 넣기
#       [데이터] 아래에  [참고 통계]  영역을 만들고  {summary_text(table, view)}  를 넣기
#   그리고 [판단 기준]도 새 칸에 맞게 다듬어 보세요.
#   예) "_공식대비% 칸이 있으면 직접 계산하지 말고 그 값을 사용해 판단"
