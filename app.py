import pandas as pd
import streamlit as st
import io
import tempfile

from common import CLEAN_DIR, ERROR_DIR, load_all
from step4_rule_validator import validate_rules
from step5_ai_validator import validate_ai
from pathlib import Path

def join_unique(values):
    texts = [str(v) for v in values if str(v) != ""]
    return " / ".join(dict.fromkeys(texts))


def merge_results(result):
    return result.groupby(["table","excel_row"], as_index = False).agg(
        column = ("column", join_unique),
        error_type = ("error_type", join_unique),
        value = ("value", join_unique),
        message = ("message", join_unique),
        source = ("source", join_unique)
    )

# 데이터 프레임을 엑셀 파일로 변환한 뒤 바이트로 변환하여 넘긴다.
def to_excel_bytes(df):
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()

REQUIRED = ["DropGroup", "Item", "Monster", "Quest", "Reward", "StringTable"]

# 실제로 유저가 검증할 파일을 임시 폴더에 저장한뒤 해당 임시 폴더를 검증하는 방식으로 사용
def load_uploaded(files):
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            (Path(tmp) / f.name).write_bytes(f.getvalue())
        return load_all(Path(tmp))

st.set_page_config(page_title="게임 데이터 검증 AI", layout="wide")
st.title("게임 데이터 검증 AI")
st.write("기획 데이터 테이블의 오류를 검증 코드 + AI로 찾는 툴입니다.")

# ── 입력 ─────────────────────────────────────────────
choice = st.radio("검사할 데이터", ["오류 데이터 (샘플)", "정상 데이터 (샘플)", "직접 업로드"])
folder = ERROR_DIR if choice.startswith("오류") else CLEAN_DIR

uploaded = []

if choice == "직접 업로드":
    uploaded = st.file_uploader(
        "검증할 테이블 엑셀 파일을 전부 올려주세요",
        type="xlsx",
        accept_multiple_files=True,
    )

use_ai = st.checkbox("AI 검증 포함 (Gemini 5회 호출, 30초 정도 걸립니다.)")

# ── ① 버튼 블록: 눌렀을 때만 검증하고 결과를 저장 ──────────
if st.button("검증 시작", type="primary"):
    if choice == "직접 업로드":
        names = [Path(f.name).stem for f in uploaded]
        missing = [t for t in REQUIRED if t not in names]
        if missing:
            st.error(f"다음 테이블이 필요합니다. ({', '.join(missing)})")
            st.stop()
        try:
            tables, indexes = load_uploaded(uploaded)
        except Exception as e:
            st.error(f"파일을 읽지 못했습니다. 시트 이름과 인덱스 시트를 확인해주세요. ({e})")
            st.stop()
    else:
        tables, indexes = load_all(folder)

    with st.spinner("규칙 검증 중..."):
        rule_df = validate_rules(tables, indexes)
        rule_df["source"] = "규칙"
    results = [rule_df]

    if use_ai:
        with st.spinner("AI 검증 중... (30초 정도 소요됩니다.)"):
            try:
                results.append(validate_ai(tables, indexes))
            except ValueError as e:              # API 키가 없을 때 (3-2에서 만든 메시지)
                st.error(str(e))

    result = pd.concat(results, ignore_index=True)
    result = result.fillna("")   
    result["value"] = result["value"].astype(str)   # 숫자·글자가 섞인 칸 → 글자로 통일

    st.session_state["result"] = result             # 미션 1: session_state에 "result"로 저장
    st.session_state["checked"] = choice             # 어떤 데이터를 검사했는지도 기억

# ── ② 결과 블록: 매번 실행, 저장된 결과가 있으면 표시 ──────
if "result" in st.session_state:                                           # 미션 2: 저장된 결과가 있는지 확인
    result = st.session_state["result"]
    st.subheader(f"검사 결과: {st.session_state['checked']}")

    merged = merge_results(result)
    merge = st.checkbox("같은 행 합쳐 보기", value=True)
    shown = merged if merge else result

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("오류 행", len(merged))
    c2.metric("규칙", (result["source"] == "규칙").sum())
    c3.metric("AI", (result["source"] == "AI").sum())
    c4.metric("규칙·AI 둘 다", (merged["source"] == "규칙 / AI").sum())
    
    f1, f2 = st.columns(2)
    sel_tables = f1.multiselect("테이블", sorted(shown["table"].unique()),placeholder="전체")
    sel_sources = f2.multiselect("출처", sorted(shown["source"].unique()),placeholder="전체")

    if sel_tables:
        shown = shown[shown["table"].isin(sel_tables)]
    if sel_sources:
        shown = shown[shown["source"].isin(sel_sources)]

    st.caption(f"{len(shown)}줄 표시 중")
    st.dataframe(shown, hide_index=True)

    # 다운로드 버튼 클릭 시 결과 파일을 변환하여 내려준다.
    st.download_button(
        "검증 파일 다운로드(EXCEL)",
        data= to_excel_bytes(shown),
        file_name= "validation_result.xlsx",
        mime= "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )