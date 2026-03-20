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

# Colunas esperadas por tabela (para sanitizar e evitar coluna "index" do data_editor)
COLUNAS_ESPERADAS = {
    KEY_TAREFAS: ["Tarefa", "Responsável", "Data limite", "Concluída"],
    KEY_FORNECEDORES: ["Nome", "Serviço", "Contacto", "Preço", "Utilizado", "Notas"],
    KEY_CRONOGRAMA: ["Hora", "Atividade", "Local", "Notas"],
}


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
    cols = COLUNAS_ESPERADAS.get(data_key, df.columns.tolist())
    defaults = default_value_for_new_rows or {}

    # 1) edited_rows: {row_index: {col: value}}
    for idx, changes in editor_state.get("edited_rows", {}).items():
        if idx < 0 or idx >= len(df):
            continue
        for col, val in changes.items():
            if col in df.columns:
                df.iloc[idx, df.columns.get_loc(col)] = val

    # 2) deleted_rows: apagar por posição (ordem decrescente para não deslocar índices)
    for idx in sorted(editor_state.get("deleted_rows", []), reverse=True):
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

    if data_key in COLUNAS_ESPERADAS:
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
    return out.reset_index(drop=True)


def _empty_convidados():
    return pd.DataFrame(
        columns=["Nome", "Contacto", "Confirmação", "Mesa", "Notas"]
    ).astype({"Nome": str, "Contacto": str, "Confirmação": str, "Mesa": str, "Notas": str})


def _empty_orcamento():
    return pd.DataFrame(
        columns=["Categoria", "Descrição", "Valor previsto", "Valor real", "Estado"]
    ).astype({
        "Categoria": str, "Descrição": str,
        "Valor previsto": float, "Valor real": float,
        "Estado": str,
    })


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
    return pd.DataFrame([
        ["Catering", "Jantar e bebidas", 8500.0, 8200.0, "Pago"],
        ["Catering", "Bolo", 450.0, 450.0, "Pago"],
        ["Fotografia", "Fotógrafo + vídeo", 1800.0, 0.0, "Previsto"],
        ["Flores", "Decoração e bouquet", 1200.0, 1100.0, "Pago"],
        ["Local", "Aluguer da quinta", 3500.0, 3500.0, "Pago"],
        ["Música", "DJ", 600.0, 0.0, "Previsto"],
        ["Convites", "Impressão e envio", 250.0, 250.0, "Pago"],
    ], columns=["Categoria", "Descrição", "Valor previsto", "Valor real", "Estado"])


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
        zf.writestr(FILE_ORCAMENTO, st.session_state[KEY_ORCAMENTO].to_csv(index=False))
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
                st.session_state[KEY_ORCAMENTO] = df
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
