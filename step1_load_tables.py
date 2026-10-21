"""1단계: 모든 테이블을 읽고, 데이터 시트와 Index 시트의 형식이 맞는지 점검한다."""
from common import ERROR_DIR, VALID_TYPES, load_all

tables, indexes = load_all(ERROR_DIR)
print(f"읽은 테이블 {len(tables)}개\n")

problems = 0
for name, df in tables.items():
    ix = indexes[name]
    print(f"[{name}] {len(df)}행 × {len(df.columns)}열")

    data_cols, index_cols = list(df.columns), list(ix["컬럼명"])
    missing_in_index = [c for c in data_cols if c not in index_cols]
    missing_in_data = [c for c in index_cols if c not in data_cols]
    bad_types = ix.loc[~ix["자료형"].isin(VALID_TYPES), ["컬럼명", "자료형"]].values.tolist()

    if missing_in_index:
        print(f"   ⚠️ Index에 설명이 없는 컬럼: {missing_in_index}")
    if missing_in_data:
        print(f"   ⚠️ Index에는 있는데 데이터에 없는 컬럼: {missing_in_data}")
    if bad_types:
        print(f"   ⚠️ 알 수 없는 자료형: {bad_types}")
    problems += len(missing_in_index) + len(missing_in_data) + len(bad_types)

tablename = "Item"
colname = "type"

print(f"\n미리보기 ({tablename} 앞 3행):")
print(tables[tablename].head(3).to_string())
print("\n" + ("✅ 데이터와 Index 형식이 모두 일치합니다." if problems == 0 else f"⚠️ 형식 문제 {problems}건을 확인하세요."))
print(tables[tablename][colname].value_counts())
