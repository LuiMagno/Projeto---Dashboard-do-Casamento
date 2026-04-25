"""
Inicialização dos dados em session_state e funções de export/import (Solução 1).
"""
import io
import zipfile
import pandas as pd
import streamlit as st

# Chaves no session_state
KEY_CONVIDADOS = "df_convidados"
KEY_ORCAMENTO = "df_orcamento"
KEY_TAREFAS = "df_tarefas"
KEY_FORNECEDORES = "df_fornecedores"
KEY_CRONOGRAMA = "df_cronograma"

# Nomes dos ficheiros no ZIP
FILE_CONVIDADOS = "convidados.csv"
FILE_ORCAMENTO = "orcamento.csv"
FILE_TAREFAS = "tarefas.csv"
FILE_FORNECEDORES = "fornecedores.csv"
FILE_CRONOGRAMA = "cronograma.csv"

# Orçamento: Total Pago = soma das colunas mensais (calculado). A ser pago calculado no export / UI.
ORCAMENTO_MESES = [
    "jan./2026",
    "fev./26",
    "mar./26",
    "abr./26",
    "mai./26",
    "jun./26",
    "jul./26",
    "ago./26",
    "set./26",
    "out./26",
    "nov./26",
]
ORCAMENTO_COLS_EDIT = (
    ["Item", "Preço estipulado", "Método de Pgto"]
    + ORCAMENTO_MESES
    + ["Total Pago", "Total a Pagar"]
)
ORCAMENTO_NUMERIC_COLS = ["Preço estipulado"] + ORCAMENTO_MESES + ["Total Pago", "Total a Pagar"]
# Coluna só calculada (não guardada em session_state): Total a Pagar - Total Pago
ORCAMENTO_COL_A_SER_PAGO = "A ser pago"


def orcamento_data_editor_defaults() -> dict:
    """Valores por omissão para novas linhas do data_editor do orçamento."""
    out = {c: 0.0 for c in ORCAMENTO_NUMERIC_COLS}
    out["Item"] = ""
    out["Método de Pgto"] = ""
    return out


def _orcamento_backfill_meses_from_total_pago(df: pd.DataFrame) -> pd.DataFrame:
    """
    CSV antigo: Total Pago preenchido e meses vazios → coloca esse valor em jan./2026
    para não perder dados ao passar a somar só pelos meses.
    """
    out = df.copy()
    if not all(m in out.columns for m in ORCAMENTO_MESES) or "Total Pago" not in out.columns:
        return out
    for i in range(len(out)):
        msum = float(pd.to_numeric(out[ORCAMENTO_MESES].iloc[i], errors="coerce").fillna(0.0).sum())
        tp_old = float(pd.to_numeric(out["Total Pago"].iloc[i], errors="coerce") or 0)
        if msum == 0 and tp_old > 0:
            out.iat[i, out.columns.get_loc("jan./2026")] = tp_old
    return out


def _orcamento_set_total_pago_from_meses(df: pd.DataFrame) -> pd.DataFrame:
    """Total Pago = soma das colunas jan.–nov."""
    out = df.copy()
    if not all(m in out.columns for m in ORCAMENTO_MESES) or "Total Pago" not in out.columns:
        return out
    m = out[ORCAMENTO_MESES].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    out["Total Pago"] = m.sum(axis=1)
    return out


def coerce_orcamento_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Garante tipos numéricos e recalcula Total Pago a partir dos meses."""
    if df is None:
        return _empty_orcamento()
    out = df.copy()
    for c in ORCAMENTO_NUMERIC_COLS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
    for c in ("Item", "Método de Pgto"):
        if c in out.columns:
            out[c] = out[c].fillna("").astype(str)
    if all(c in out.columns for c in ORCAMENTO_COLS_EDIT):
        out = out[ORCAMENTO_COLS_EDIT]
    out = _orcamento_backfill_meses_from_total_pago(out)
    out = _orcamento_set_total_pago_from_meses(out)
    return out


def orcamento_para_export(df: pd.DataFrame) -> pd.DataFrame:
    """Orçamento com coluna calculada A ser pago (CSV, ZIP, Google Sheets)."""
    base = normalize_orcamento_df(df)
    out = base.copy()
    tp = pd.to_numeric(out["Total Pago"], errors="coerce").fillna(0.0)
    tap = pd.to_numeric(out["Total a Pagar"], errors="coerce").fillna(0.0)
    out[ORCAMENTO_COL_A_SER_PAGO] = tap - tp
    i = ORCAMENTO_COLS_EDIT.index("Total a Pagar") + 1
    head = list(ORCAMENTO_COLS_EDIT[:i])
    tail = list(ORCAMENTO_COLS_EDIT[i:])
    final_cols = head + [ORCAMENTO_COL_A_SER_PAGO] + tail
    return out[final_cols]


def normalize_orcamento_df(df: pd.DataFrame) -> pd.DataFrame:
    """Garante colunas do novo orçamento; migra esquema antigo (Categoria / Valor previsto, …)."""
    if df is None:
        return _empty_orcamento()

    df = df.copy()
    if len(df) == 0:
        return _empty_orcamento()
    if "Categoria" in df.columns and "Valor previsto" in df.columns:
        rows = []
        for _, r in df.iterrows():
            cat = str(r.get("Categoria", "")).strip()
            desc = str(r.get("Descrição", "")).strip()
            item = " - ".join(p for p in (cat, desc) if p)
            stip = float(pd.to_numeric(r.get("Valor previsto"), errors="coerce") or 0)
            vr = float(pd.to_numeric(r.get("Valor real"), errors="coerce") or 0)
            est = str(r.get("Estado", "")).strip()
            row = {c: 0.0 for c in ORCAMENTO_COLS_EDIT if c not in ("Item", "Método de Pgto")}
            row["Item"] = item
            row["Método de Pgto"] = ""
            row["Preço estipulado"] = stip
            if est == "Pago" and vr > 0:
                row["jan./2026"] = vr
            if est == "Pago":
                row["Total a Pagar"] = max(0.0, stip - vr)
            else:
                row["Total a Pagar"] = max(0.0, stip) if stip else 0.0
            rows.append(row)
        return coerce_orcamento_numeric(pd.DataFrame(rows))

    n = len(df)
    data: dict = {}
    for c in ORCAMENTO_COLS_EDIT:
        if c in df.columns:
            data[c] = df[c].tolist()
        else:
            data[c] = ["" if c in ("Item", "Método de Pgto") else 0.0] * n
    out = pd.DataFrame(data)
    return coerce_orcamento_numeric(out)


def _orcamento_row(
    item: str,
    stip: float = 0.0,
    metodo: str = "",
    meses: dict | None = None,
    total_a_pagar: float = 0.0,
) -> dict:
    meses = meses or {}
    row = {c: 0.0 for c in ORCAMENTO_COLS_EDIT if c not in ("Item", "Método de Pgto")}
    row["Item"] = item
    row["Método de Pgto"] = metodo
    row["Preço estipulado"] = float(stip)
    row["Total a Pagar"] = float(total_a_pagar)
    for m in ORCAMENTO_MESES:
        row[m] = float(meses.get(m, 0.0))
    return row


# Colunas esperadas por tabela (para sanitizar e evitar coluna "index" do data_editor)
COLUNAS_ESPERADAS = {
    KEY_CONVIDADOS: ["Nome", "Contacto", "Confirmação", "Mesa", "Notas"],
    KEY_TAREFAS: ["Tarefa", "Responsável", "Data limite", "Concluída"],
    KEY_FORNECEDORES: ["Nome", "Serviço", "Contacto", "Preço", "Utilizado", "Notas"],
    KEY_CRONOGRAMA: ["Hora", "Atividade", "Local", "Notas"],
}

_CONVIDADOS_CONFIRMACAO_OK = {"sim", "não", "nao", "pendente"}


def _filter_convidados_deleted_rows(df: pd.DataFrame, deleted_ints: list[int]) -> list[int]:
    """
    O data_editor com SelectboxColumn(required=True) pode enviar deleted_rows para
    linhas ainda sem valor em Confirmação ao editar outra linha. Não apagamos
    essas linhas se tiverem qualquer outro campo preenchido.
    """
    out: list[int] = []
    for idx in deleted_ints:
        if idx < 0 or idx >= len(df):
            continue
        row = df.iloc[idx]
        c = str(row.get("Confirmação", "")).strip().lower()
        if c in _CONVIDADOS_CONFIRMACAO_OK:
            out.append(idx)
            continue
        nome = str(row.get("Nome", "")).strip()
        contacto = str(row.get("Contacto", "")).strip()
        mesa = str(row.get("Mesa", "")).strip()
        notas = str(row.get("Notas", "")).strip()
        if nome or contacto or mesa or notas:
            continue
        out.append(idx)
    return out


def apply_data_editor_changes(
    data_key: str,
    editor_state: dict,
    default_value_for_new_rows: dict | None = None,
) -> None:
    """
    Aplica as alterações do data_editor (edited_rows, added_rows, deleted_rows)
    ao DataFrame em st.session_state[data_key]. Evita o bug de sobrescrever
    o dataframe com o return value do widget (que faz as linhas desaparecerem).
    """
    if data_key not in st.session_state or not isinstance(editor_state, dict):
        return
    df = st.session_state[data_key].copy()
    if data_key == KEY_ORCAMENTO:
        df = normalize_orcamento_df(df)
        cols = list(ORCAMENTO_COLS_EDIT)
    else:
        cols = COLUNAS_ESPERADAS.get(data_key, df.columns.tolist())
    defaults = default_value_for_new_rows or {}

    # Alguns eventos do data_editor (especialmente ao editar uma linha recém-criada)
    # podem chegar como edited_rows com índices > len(df) e sem added_rows. Em vez
    # de ignorar (o que "apaga" visualmente a linha), estendemos o df com linhas vazias.
    edited_keys = list(editor_state.get("edited_rows", {}).keys())
    edited_ints: list[int] = []
    for k in edited_keys:
        try:
            edited_ints.append(int(k))
        except (TypeError, ValueError):
            continue
    max_idx = max(edited_ints) if edited_ints else -1
    if max_idx >= len(df):
        missing = (max_idx + 1) - len(df)
        if missing > 0:
            blank_row = {c: defaults.get(c, "" if data_key != KEY_ORCAMENTO else 0.0) for c in cols}
            df = pd.concat([df, pd.DataFrame([blank_row] * missing)], ignore_index=True)

    # 1) edited_rows: {row_index: {col: value}} (índices podem vir como str do estado do widget)
    for idx_raw, changes in editor_state.get("edited_rows", {}).items():
        try:
            idx = int(idx_raw)
        except (TypeError, ValueError):
            continue
        if idx < 0:
            continue
        for col, val in changes.items():
            if data_key == KEY_ORCAMENTO and col == "Total Pago":
                continue
            if col in df.columns:
                df.iloc[idx, df.columns.get_loc(col)] = val

    # 2) deleted_rows: apagar por posição (ordem decrescente para não deslocar índices)
    deleted_raw = editor_state.get("deleted_rows", [])
    deleted_ints = []
    for x in deleted_raw:
        try:
            deleted_ints.append(int(x))
        except (TypeError, ValueError):
            continue
    if data_key == KEY_CONVIDADOS:
        deleted_ints = _filter_convidados_deleted_rows(df, deleted_ints)
    for idx in sorted(deleted_ints, reverse=True):
        if 0 <= idx < len(df):
            df = df.drop(df.index[idx]).reset_index(drop=True)

    # 3) added_rows: lista de linhas (dict ou lista de valores)
    for row in editor_state.get("added_rows", []):
        if isinstance(row, dict):
            new_row = [str(row.get(c, defaults.get(c, ""))) for c in cols]
        else:
            row_list = list(row) if hasattr(row, "__iter__") and not isinstance(row, str) else [row]
            new_row = [str(row_list[i]) if i < len(row_list) else str(defaults.get(cols[i], "")) for i in range(len(cols))]
        df = pd.concat([df, pd.DataFrame([new_row], columns=cols)], ignore_index=True)

    if data_key == KEY_ORCAMENTO:
        st.session_state[data_key] = coerce_orcamento_numeric(df.reset_index(drop=True))
    elif data_key in COLUNAS_ESPERADAS:
        st.session_state[data_key] = prepare_table_df(data_key, df)
    else:
        st.session_state[data_key] = df.reset_index(drop=True)


def prepare_table_df(key: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove coluna 'index' se o data_editor tiver adicionado, mantém só colunas esperadas,
    reset_index(drop=True). Evita o bug de aparecer coluna 'index 0' e perder dados.
    """
    if key not in COLUNAS_ESPERADAS:
        return df.reset_index(drop=True)
    cols = COLUNAS_ESPERADAS[key]
    out = df.copy()
    if "index" in out.columns:
        out = out.drop(columns=["index"])
    for c in cols:
        if c not in out.columns:
            out[c] = ""
    out = out[cols].fillna("").astype(str)
    if key == KEY_CONVIDADOS and "Confirmação" in out.columns:
        s = out["Confirmação"].astype(str).str.strip()
        low = s.str.lower()
        out["Confirmação"] = s.where(low.isin(_CONVIDADOS_CONFIRMACAO_OK), "Pendente")
    return out.reset_index(drop=True)


def _empty_convidados():
    return pd.DataFrame(
        columns=["Nome", "Contacto", "Confirmação", "Mesa", "Notas"]
    ).astype({"Nome": str, "Contacto": str, "Confirmação": str, "Mesa": str, "Notas": str})


def _empty_orcamento():
    return pd.DataFrame({c: pd.Series(dtype="float64" if c in ORCAMENTO_NUMERIC_COLS else "object") for c in ORCAMENTO_COLS_EDIT})


def _empty_tarefas():
    return pd.DataFrame(
        columns=["Tarefa", "Responsável", "Data limite", "Concluída"]
    ).astype({"Tarefa": str, "Responsável": str, "Data limite": str, "Concluída": str})


def _empty_fornecedores():
    return pd.DataFrame(
        columns=["Nome", "Serviço", "Contacto", "Preço", "Utilizado", "Notas"]
    ).astype({"Nome": str, "Serviço": str, "Contacto": str, "Preço": str, "Utilizado": str, "Notas": str})


def _empty_cronograma():
    return pd.DataFrame(
        columns=["Hora", "Atividade", "Local", "Notas"]
    ).astype({"Hora": str, "Atividade": str, "Local": str, "Notas": str})


def _mock_convidados():
    return pd.DataFrame([
        ["Maria Silva", "912 345 678", "Sim", "1", "Familia noiva"],
        ["João Santos", "923 456 789", "Sim", "1", ""],
        ["Ana Costa", "934 567 890", "Pendente", "2", ""],
        ["Pedro Oliveira", "945 678 901", "Não", "", "Não pode vir"],
        ["Catarina Ferreira", "956 789 012", "Sim", "2", "Vegetariana"],
        ["Miguel Alves", "967 890 123", "Pendente", "3", ""],
    ], columns=["Nome", "Contacto", "Confirmação", "Mesa", "Notas"])


def _mock_orcamento():
    rows = [
        _orcamento_row("Banda - ", stip=10_000.0),
        _orcamento_row("Cerimonialista - Katia", meses={"jan./2026": 860.0}, total_a_pagar=4_300.0),
        _orcamento_row("Fotógrafo - ", stip=3_000.0),
        _orcamento_row(
            "Maquiagem - PH MAKE",
            meses={"mar./26": 648.0, "abr./26": 2_160.0},
            total_a_pagar=2_160.0,
        ),
        _orcamento_row(
            "Celebrante - Toia Vasconcelos",
            meses={"fev./26": 500.0},
            total_a_pagar=1_000.0,
        ),
        _orcamento_row(
            "Decoração - Comemore Eventos",
            meses={"jan./2026": 4_350.0},
            total_a_pagar=14_500.0,
        ),
        _orcamento_row("Presente Padrinho - ", meses={"jan./2026": 21_960.0}),
        _orcamento_row("Presente Madrinha - "),
        _orcamento_row("Alianças - "),
        _orcamento_row("Guardanapo - "),
        _orcamento_row("Chinelas - "),
        _orcamento_row("Dia da Noiva - "),
        _orcamento_row("Bem Casado - ", stip=1_300.0),
        _orcamento_row("DJ - ", stip=3_000.0),
        _orcamento_row("Doces - ", stip=3_800.0),
        _orcamento_row("Convites"),
    ]
    return coerce_orcamento_numeric(pd.DataFrame(rows))


def _mock_tarefas():
    return pd.DataFrame([
        ["Reservar local", "Noiva", "2024-06-01", "Sim"],
        ["Escolher catering", "Noivo", "2024-07-15", "Sim"],
        ["Contratar fotógrafo", "Noiva", "2024-08-01", "Não"],
        ["Enviar convites", "Ambos", "2024-09-01", "Não"],
        ["Confirmar decoração", "Noiva", "2024-09-15", "Não"],
        ["Lista de presentes", "Noivo", "2024-08-30", "Não"],
    ], columns=["Tarefa", "Responsável", "Data limite", "Concluída"])


def _mock_fornecedores():
    return pd.DataFrame([
        ["Quinta das Flores", "Local", "212 345 678", "3500 €", "Sim", "Inclui estacionamento"],
        ["Sabores do Campo", "Catering", "213 456 789", "8500 €", "Sim", ""],
        ["Luz & Cor", "Fotografia", "914 567 890", "1800 €", "Não", "Inclui álbum"],
        ["Flores da Maria", "Flores", "915 678 901", "1200 €", "Sim", ""],
        ["DJ Sound", "Música", "916 789 012", "600 €", "Sim", ""],
    ], columns=["Nome", "Serviço", "Contacto", "Preço", "Utilizado", "Notas"])


def _mock_cronograma():
    return pd.DataFrame([
        ["14:00", "Chegada dos convidados", "Jardim", "Aperitivos"],
        ["15:00", "Cerimónia", "Capela", ""],
        ["16:00", "Fotos de grupo", "Jardim", ""],
        ["17:30", "Jantar", "Salão", ""],
        ["20:00", "Bolo e discursos", "Salão", ""],
        ["21:00", "Festa", "Salão", "DJ"],
    ], columns=["Hora", "Atividade", "Local", "Notas"])


def load_mock_data():
    """Preenche session_state com dados de exemplo para teste."""
    init_session_state()
    st.session_state[KEY_CONVIDADOS] = _mock_convidados()
    st.session_state[KEY_ORCAMENTO] = _mock_orcamento()
    st.session_state[KEY_TAREFAS] = _mock_tarefas()
    st.session_state[KEY_FORNECEDORES] = _mock_fornecedores()
    st.session_state[KEY_CRONOGRAMA] = _mock_cronograma()


def clear_all_data():
    """Limpa todos os dados (volta às tabelas vazias)."""
    st.session_state[KEY_CONVIDADOS] = _empty_convidados()
    st.session_state[KEY_ORCAMENTO] = _empty_orcamento()
    st.session_state[KEY_TAREFAS] = _empty_tarefas()
    st.session_state[KEY_FORNECEDORES] = _empty_fornecedores()
    st.session_state[KEY_CRONOGRAMA] = _empty_cronograma()
    if "_export_zip" in st.session_state:
        del st.session_state["_export_zip"]


def init_session_state():
    """Garante que todos os DataFrames existem em st.session_state."""
    if KEY_CONVIDADOS not in st.session_state:
        st.session_state[KEY_CONVIDADOS] = _empty_convidados()
    if KEY_ORCAMENTO not in st.session_state:
        st.session_state[KEY_ORCAMENTO] = _empty_orcamento()
    else:
        st.session_state[KEY_ORCAMENTO] = normalize_orcamento_df(st.session_state[KEY_ORCAMENTO])
    if KEY_TAREFAS not in st.session_state:
        st.session_state[KEY_TAREFAS] = _empty_tarefas()
    if KEY_FORNECEDORES not in st.session_state:
        st.session_state[KEY_FORNECEDORES] = _empty_fornecedores()
    elif "Utilizado" not in st.session_state[KEY_FORNECEDORES].columns:
        # Nova referência (não alterar in-place) para não confundir o data_editor
        old = st.session_state[KEY_FORNECEDORES]
        new = old.copy()
        new["Utilizado"] = "Não"
        st.session_state[KEY_FORNECEDORES] = new
    if KEY_CRONOGRAMA not in st.session_state:
        st.session_state[KEY_CRONOGRAMA] = _empty_cronograma()


def export_all_csv():
    """Exporta todos os DataFrames para CSV dentro de um ZIP. Retorna BytesIO ou None."""
    init_session_state()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(FILE_CONVIDADOS, st.session_state[KEY_CONVIDADOS].to_csv(index=False))
        zf.writestr(
            FILE_ORCAMENTO,
            orcamento_para_export(st.session_state[KEY_ORCAMENTO]).to_csv(index=False),
        )
        zf.writestr(FILE_TAREFAS, st.session_state[KEY_TAREFAS].to_csv(index=False))
        zf.writestr(FILE_FORNECEDORES, st.session_state[KEY_FORNECEDORES].to_csv(index=False))
        zf.writestr(FILE_CRONOGRAMA, st.session_state[KEY_CRONOGRAMA].to_csv(index=False))
    buf.seek(0)
    return buf


def import_from_uploaded(uploaded_file):
    """
    Lê um ZIP com os CSV e preenche session_state.
    Retorna (success: bool, message: str).
    """
    try:
        with zipfile.ZipFile(uploaded_file, "r") as zf:
            names = zf.namelist()
            if FILE_CONVIDADOS in names:
                df = pd.read_csv(zf.open(FILE_CONVIDADOS))
                st.session_state[KEY_CONVIDADOS] = df
            if FILE_ORCAMENTO in names:
                df = pd.read_csv(zf.open(FILE_ORCAMENTO))
                st.session_state[KEY_ORCAMENTO] = normalize_orcamento_df(df)
            if FILE_TAREFAS in names:
                df = pd.read_csv(zf.open(FILE_TAREFAS))
                st.session_state[KEY_TAREFAS] = df
            if FILE_FORNECEDORES in names:
                df = pd.read_csv(zf.open(FILE_FORNECEDORES))
                st.session_state[KEY_FORNECEDORES] = df
            if FILE_CRONOGRAMA in names:
                df = pd.read_csv(zf.open(FILE_CRONOGRAMA))
                st.session_state[KEY_CRONOGRAMA] = df
        return True, "Dados importados com sucesso. A página vai atualizar."
    except Exception as e:
        return False, f"Erro ao importar: {e}"
