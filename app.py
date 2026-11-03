import pandas as pd
import streamlit as st

from common import CLEAN_DIR, ERROR_DIR, load_all
from step4_rule_validator import validate_rules
from step5_ai_validator import validate_ai

st.set_page_config(page_title="게임 데이터 검증 AI", layout="wide")
st.title("게임 데이터 검증 AI")
st.write("기획 데이터 테이블의 오류를 검증 코드 + AI로 찾는 툴입니다.")

# ── 입력 ─────────────────────────────────────────────
choice = st.radio("검사할 데이터", ["오류 데이터 (샘플)", "정상 데이터 (샘플)"])
folder = ERROR_DIR if choice.startswith("오류") else CLEAN_DIR
use_ai = st.checkbox("AI 검증 포함 (Gemini 5회 호출, 30초 정도 걸립니다.)")

# ── ① 버튼 블록: 눌렀을 때만 검증하고 결과를 저장 ──────────
if st.button("검증 시작", type="primary"):
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
    result["value"] = result["value"].fillna("").astype(str)   # 숫자·글자가 섞인 칸 → 글자로 통일

    st.session_state["result"] = result             # 미션 1: session_state에 "result"로 저장
    st.session_state["checked"] = choice             # 어떤 데이터를 검사했는지도 기억

# ── ② 결과 블록: 매번 실행, 저장된 결과가 있으면 표시 ──────
if "result" in st.session_state:                                           # 미션 2: 저장된 결과가 있는지 확인
    result = st.session_state["result"]
    st.subheader(f"검사 결과: {st.session_state['checked']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("전체", len(result))
    c2.metric("규칙", (result["source"] == "규칙").sum())                         # 미션 3: source가 "규칙"인 행 개수
    c3.metric("AI", (result["source"] == "AI").sum())                           #         source가 "AI"인 행 개수

    st.dataframe(result, hide_index=True)