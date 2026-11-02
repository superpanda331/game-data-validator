"""AI에게 보여 줄 '읽기 쉬운 표(뷰)'를 만드는 도구. (직접 고칠 필요 없음 — 읽고 이해만 하면 돼요)

왜 필요한가?
    원본 테이블은 키(ID)로만 연결돼 있어서 AI가 맥락을 알 수 없어요.
      Item 행:      name_key = ITEM_NAME_1012          ← 이름이 뭔지 모름
      DropGroup 행: item_id = 1050, drop_rate = 0.5    ← 그 아이템이 전설인지 모름
    그래서 사람이 엑셀에서 VLOOKUP으로 옆에 정보를 붙여 보듯이,
    관련 테이블의 정보를 옆 칸에 붙인 '뷰'를 만들어 AI에게 보여 줘요.

중요한 점:
    뷰에는 키(name_key 등)와 그 키가 가리키는 텍스트(이름·설명)를 나란히 보여 줘요.
    '이름'·'설명' 칸은 실제로는 StringTable에 들어 있는 값이에요.
    AI가 "이 설명이 이상하다"고 하면, 오류 위치는 Item이 아니라 StringTable의 그 행이에요.
    to_source() 함수가 뷰의 위치를 → 원본 테이블의 위치로 되돌려 줘요.
"""
import pandas as pd


def _lookup(df, key_col, val_col):
    """key_col 값 → val_col 값 사전. (중복 키는 첫 번째 값을 사용)"""
    d = {}
    for k, v in zip(df[key_col], df[val_col]):
        if pd.notna(k) and k not in d:
            d[k] = v
    return d


def _excel_rows(df):
    return [i + 2 for i in df.index]


def build_views(tables):
    """테이블별 AI용 뷰를 만든다. {테이블명: DataFrame}"""
    st = tables["StringTable"]
    text = _lookup(st, "string_key", "ko")                     # 키 → 한국어 텍스트
    item, mon, quest, reward = tables["Item"], tables["Monster"], tables["Quest"], tables["Reward"]

    def t(key):
        if pd.isna(key):
            return "(키 없음)"
        return text.get(key, "(StringTable에 없음)")

    item_name = {k: t(v) for k, v in _lookup(item, "item_id", "name_key").items()}
    item_grade = _lookup(item, "item_id", "grade")
    item_type = _lookup(item, "item_id", "type")
    mon_name = {k: t(v) for k, v in _lookup(mon, "monster_id", "name_key").items()}
    quest_lv = _lookup(quest, "quest_id", "level_req")
    reward_quest_lv = _lookup(quest, "reward_group_id", "level_req")

    views = {}
    views["Item"] = pd.DataFrame({
        "excel_row": _excel_rows(item), "item_id": item["item_id"],
        "name_key": item["name_key"], "이름": item["name_key"].map(t),
        "desc_key": item["desc_key"], "설명": item["desc_key"].map(t),
        "grade": item["grade"], "type": item["type"], "level_req": item["level_req"],
        "price": item["price"], "max_stack": item["max_stack"], "tradable": item["tradable"],
    })
    views["Monster"] = pd.DataFrame({
        "excel_row": _excel_rows(mon), "monster_id": mon["monster_id"],
        "name_key": mon["name_key"], "이름": mon["name_key"].map(t),
        "level": mon["level"], "region": mon["region"], "hp": mon["hp"],
        "atk": mon["atk"], "defense": mon["defense"], "exp": mon["exp"],
    })
    drop = tables["DropGroup"]
    views["DropGroup"] = pd.DataFrame({
        "excel_row": _excel_rows(drop), "drop_group_id": drop["drop_group_id"], "item_id": drop["item_id"],
        "아이템_이름": drop["item_id"].map(lambda x: item_name.get(x, "(없는 아이템)")),
        "아이템_등급": drop["item_id"].map(lambda x: item_grade.get(x, "-")),
        "아이템_종류": drop["item_id"].map(lambda x: item_type.get(x, "-")),
        "drop_rate": drop["drop_rate"], "min_count": drop["min_count"], "max_count": drop["max_count"],
    })
    views["Quest"] = pd.DataFrame({
        "excel_row": _excel_rows(quest), "quest_id": quest["quest_id"],
        "name_key": quest["name_key"], "이름": quest["name_key"].map(t),
        "level_req": quest["level_req"], "prev_quest_id": quest["prev_quest_id"],
        "선행퀘스트_level_req": quest["prev_quest_id"].map(lambda x: quest_lv.get(x, "-")),
        "target_monster_id": quest["target_monster_id"],
        "처치대상_이름": quest["target_monster_id"].map(lambda x: mon_name.get(x, "(없는 몬스터)")),
        "target_count": quest["target_count"],
    })
    views["Reward"] = pd.DataFrame({
        "excel_row": _excel_rows(reward), "reward_group_id": reward["reward_group_id"],
        "퀘스트_level_req": reward["reward_group_id"].map(lambda x: reward_quest_lv.get(x, "-")),
        "item_id": reward["item_id"],
        "아이템_이름": reward["item_id"].map(lambda x: item_name.get(x, "(없는 아이템)")),
        "count": reward["count"], "gold": reward["gold"], "exp": reward["exp"],
    })
    return views


# 뷰의 '텍스트 칸' → (원본 테이블의 키 컬럼, 키 접두어, ID 컬럼)
#   AI는 '이름' 대신 'name_key'처럼 명세의 컬럼명으로 답하기도 해서 둘 다 등록해 둬요.
_ITEM_NAME = ("name_key", "ITEM_NAME_", "item_id")
_ITEM_DESC = ("desc_key", "ITEM_DESC_", "item_id")
_MON_NAME = ("name_key", "MONSTER_NAME_", "monster_id")
_QUEST_NAME = ("name_key", "QUEST_NAME_", "quest_id")
TEXT_COLUMNS = {
    "Item": {"이름": _ITEM_NAME, "name_key": _ITEM_NAME, "설명": _ITEM_DESC, "desc_key": _ITEM_DESC},
    "Monster": {"이름": _MON_NAME, "name_key": _MON_NAME},
    "Quest": {"이름": _QUEST_NAME, "name_key": _QUEST_NAME},
}


def to_source(tables, table, excel_row, column):
    """뷰에서의 오류 위치 → 원본 테이블에서의 위치 (table, excel_row, column).

    예) to_source(tables, "Item", 13, "설명")
        → Item 13행의 desc_key가 "ITEM_DESC_1012" 이므로
        → ("StringTable", <그 키가 있는 행>, "ko")
    텍스트 칸이 아니면 그대로 돌려줘요.
    """
    info = TEXT_COLUMNS.get(table, {}).get(column)
    if info is None:
        return table, excel_row, column
    key_col, prefix, id_col = info
    row = tables[table].loc[excel_row - 2]
    key = row[key_col]
    if key != f"{prefix}{row[id_col]}":      # 키 자체가 잘못 연결된 경우 → 원본 키 칸이 문제
        return table, excel_row, key_col
    st = tables["StringTable"]
    hits = st.index[st["string_key"] == key]
    if len(hits) == 0:                       # StringTable에 키가 없으면 원본 키 칸을 가리킴
        return table, excel_row, key_col
    return "StringTable", int(hits[0]) + 2, "ko"
