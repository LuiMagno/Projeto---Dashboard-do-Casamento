"""
Ligação ao Google Sheets (Solução 2).
Lê e escreve os dados do dashboard numa folha de cálculo Google.
Credenciais: st.secrets ou ficheiro JSON na pasta do projeto.
"""
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from .data import (
    KEY_CONVIDADOS,
    KEY_ORCAMENTO,
    KEY_TAREFAS,
    KEY_FORNECEDORES,
    KEY_CRONOGRAMA,
    ORCAMENTO_COL_A_SER_PAGO,
    ORCAMENTO_NUMERIC_COLS,
    orcamento_para_export,
)

# Nomes das folhas (abas) na Google Sheet — devem coincidir com estes nomes
SHEET_NAMES = {
    KEY_CONVIDADOS: "Convidados",
    KEY_ORCAMENTO: "Orçamento",
    KEY_TAREFAS: "Tarefas",
    KEY_FORNECEDORES: "Fornecedores",
    KEY_CRONOGRAMA: "Cronograma",
}


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_credentials_source():
    """
    Obtém a fonte das credenciais. Preferir ficheiro (caminho normal).
    Retorna (caminho_ficheiro, None) ou (None, dict) ou (None, None).
    Ordem: 1) ficheiro em secrets/env/projeto  2) dict em secrets
    """
    # 1. Caminho em secrets
    if hasattr(st, "secrets") and st.secrets and "google_credentials_file" in st.secrets:
        path = Path(st.secrets["google_credentials_file"])
        if path.is_file():
            return (path, None)

    # 2. Variável de ambiente (padrão Google)
    path_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path_env:
        p = Path(path_env)
        if p.is_file():
            return (p, None)

    # 3. Ficheiro JSON na pasta do projeto — preferir credentials.json
    project_dir = Path(os.getcwd())
    credentials_file = project_dir / "credentials.json"
    if credentials_file.is_file():
        try:
            data = json.loads(credentials_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("type") == "service_account" and "private_key" in data:
                return (credentials_file, None)
        except Exception:
            pass
    for f in sorted(project_dir.glob("*.json")):
        if f.name == "credentials.json":
            continue  # já tentámos acima
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("type") == "service_account" and "private_key" in data:
                return (f, None)
        except Exception:
            continue

    # 4. Dict a partir de secrets (Streamlit Cloud / secrets.toml com JSON colado)
    if hasattr(st, "secrets") and st.secrets:
        try:
            if "google_credentials_json" in st.secrets:
                return (None, json.loads(st.secrets["google_credentials_json"]))
            if "google_credentials" in st.secrets:
                return (None, dict(st.secrets["google_credentials"]))
        except Exception:
            pass

    return (None, None)


def _normalize_private_key(creds_dict: dict) -> dict:
    """Corrige a chave privada quando usamos dict (secrets)."""
    if not creds_dict or "private_key" not in creds_dict:
        return creds_dict
    key = creds_dict.get("private_key", "")
    if not isinstance(key, str):
        return creds_dict
    key = key.replace("\\n", "\n").replace("\t", "")
    out = dict(creds_dict)
    out["private_key"] = key
    return out


def sheets_available() -> bool:
    """Indica se as credenciais do Google Sheets estão configuradas."""
    path, data = _get_credentials_source()
    return path is not None or data is not None


def _get_client():
    """Cria cliente gspread. Usa ficheiro JSON quando existir (caminho normal)."""
    import gspread
    from google.oauth2.service_account import Credentials

    path, creds_dict = _get_credentials_source()
    if path is None and creds_dict is None:
        return None

    if path is not None:
        credentials = Credentials.from_service_account_file(str(path), scopes=SCOPES)
    else:
        creds_dict = _normalize_private_key(creds_dict)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

    return gspread.authorize(credentials)


def _ensure_worksheets(sh):
    """Garante que existem as 5 folhas com os nomes esperados; cria se faltarem."""
    existing = {ws.title for ws in sh.worksheets()}
    for name in SHEET_NAMES.values():
        if name not in existing:
            sh.add_worksheet(title=name, rows=200, cols=30)
            existing.add(name)


def _load_from_sheets_impl(spreadsheet_id: str) -> dict:
    """Implementação da leitura (sem cache)."""
    gc = _get_client()
    if not gc:
        raise RuntimeError("Credenciais do Google não configuradas. Ver secção Google Sheets.")
    sh = gc.open_by_key(spreadsheet_id)
    _ensure_worksheets(sh)
    result = {}
    for key, sheet_name in SHEET_NAMES.items():
        try:
            ws = sh.worksheet(sheet_name)
            rows = ws.get_all_values()
            if not rows:
                result[key] = pd.DataFrame()
                continue
            df = pd.DataFrame(rows[1:], columns=rows[0])
            if key == KEY_ORCAMENTO and len(df) > 0:
                for col in ORCAMENTO_NUMERIC_COLS + [ORCAMENTO_COL_A_SER_PAGO]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            result[key] = df
        except Exception as e:
            raise RuntimeError(f"Erro ao ler folha '{sheet_name}': {e}") from e
    return result


@st.cache_data(ttl=300)
def load_from_sheets(spreadsheet_id: str) -> dict:
    """
    Lê todas as folhas da Google Sheet (com cache de 5 min).
    spreadsheet_id: o ID da folha (parte do URL entre /d/ e /edit).
    """
    return _load_from_sheets_impl(spreadsheet_id)


def save_to_sheets(spreadsheet_id: str, data: dict) -> None:
    """
    Escreve os DataFrames em data (KEY_* -> DataFrame) nas folhas correspondentes.
    Substitui o conteúdo de cada folha.
    """
    gc = _get_client()
    if not gc:
        raise RuntimeError("Credenciais do Google não configuradas. Ver secção Google Sheets.")
    sh = gc.open_by_key(spreadsheet_id)
    _ensure_worksheets(sh)
    for key, sheet_name in SHEET_NAMES.items():
        if key not in data:
            continue
        df = data[key]
        if df is None or not isinstance(df, pd.DataFrame):
            continue
        if key == KEY_ORCAMENTO:
            df = orcamento_para_export(df)
        ws = sh.worksheet(sheet_name)
        # Escrever cabeçalhos + dados
        values = [df.columns.tolist()] + df.astype(str).fillna("").values.tolist()
        ws.clear()
        if values:
            ws.update("A1", values)
    # Invalidar cache para o próximo "Carregar" trazer dados atualizados
    load_from_sheets.clear()
