"""공통 함수: 테이블과 Index 시트를 읽어 온다."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
ERROR_DIR = DATA_DIR / "data_error"   # 검증 대상 (오류를 심은 버전)
CLEAN_DIR = DATA_DIR / "data_clean"   # 정상 버전 (오탐 확인용)

# Index 시트에서 쓰는 자료형 6종과 범위
TYPE_RANGES = {
    "int": (-2_147_483_648, 2_147_483_647),
    "long": (-9_223_372_036_854_775_808, 9_223_372_036_854_775_807),
    "float" : ((-3.4*(10**38)),(3.4*(10**38)))
}
VALID_TYPES = {"int", "long", "float", "bool", "string", "enum"}


def table_names(folder: Path = ERROR_DIR) -> list[str]:
    """폴더 안의 테이블 이름 목록 (파일명 = 테이블명)."""
    return sorted(p.stem for p in folder.glob("*.xlsx") if not p.name.startswith("~$"))


def load_table(name: str, folder: Path = ERROR_DIR) -> pd.DataFrame:
    """데이터 시트를 읽는다. 시트 순서와 상관없이 '테이블명' 시트를 읽는다.
    dtype=object: 엑셀에 적힌 값을 그대로 가져온다 ("10레벨" 같은 잘못된 값도 숫자로 바꾸지 않음)."""
    return pd.read_excel(folder / f"{name}.xlsx", sheet_name=name, dtype=object)


def load_index(name: str, folder: Path = ERROR_DIR) -> pd.DataFrame:
    """Index 시트(컬럼명 / 자료형 / 용도)를 읽는다. 첫 빈 행 아래 내용(참고표 등)은 무시."""
    ix = pd.read_excel(folder / f"{name}.xlsx", sheet_name="Index", dtype=str)
    ix = ix[["컬럼명", "자료형", "용도"]]
    blank = ix["컬럼명"].isna()
    if blank.any():
        ix = ix.loc[: blank.idxmax() - 1]
    ix["컬럼명"] = ix["컬럼명"].str.strip()
    ix["자료형"] = ix["자료형"].str.strip().str.lower()
    ix["용도"] = ix["용도"].fillna("").str.strip()
    return ix.reset_index(drop=True)


def load_all(folder: Path = ERROR_DIR) -> tuple[dict, dict]:
    """모든 테이블과 Index를 한 번에 읽는다. (tables, indexes) 반환."""
    tables, indexes = {}, {}
    for name in table_names(folder):
        tables[name] = load_table(name, folder)
        indexes[name] = load_index(name, folder)
    return tables, indexes
