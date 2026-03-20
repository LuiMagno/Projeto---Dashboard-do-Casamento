"""
Lista de fornecedores: nome, serviço, contacto, preço, utilizado (Sim/Não), notas.
"""
import pandas as pd
import streamlit as st

from utils.data import (
    init_session_state,
    KEY_FORNECEDORES,
    FILE_FORNECEDORES,
    apply_data_editor_changes,
)

st.set_page_config(page_title="Fornecedores | Dashboard Casamento", page_icon="🏪", layout="wide")
init_session_state()

st.title("🏪 Fornecedores")
st.caption("Adiciona e edita fornecedores: fotógrafo, catering, flores, etc.")

df = st.session_state[KEY_FORNECEDORES].reset_index(drop=True)

# Filtro por serviço
servicos = ["Todos"]
if "Serviço" in df.columns and len(df) > 0:
    unicos = df["Serviço"].astype(str).str.strip().dropna()
    unicos = sorted(unicos[unicos != ""].unique().tolist())
    servicos = servicos + unicos

filtro_servico = st.selectbox(
    "Filtrar por serviço",
    options=servicos,
    key="fornecedores_filtro_servico",
)

if filtro_servico != "Todos":
    mask = df["Serviço"].astype(str).str.strip() == filtro_servico
    display_df = df[mask].reset_index(drop=True)
    # Guardar mapeamento display index -> índice no dataframe completo (para o callback)
    st.session_state["_fornecedores_idx_map"] = df.index[mask].tolist()
    st.session_state["_fornecedores_filter_servico"] = filtro_servico
else:
    display_df = df
    st.session_state["_fornecedores_idx_map"] = None
    st.session_state["_fornecedores_filter_servico"] = None

def _apply_fornecedores():
    state = st.session_state.get(f"editor_{KEY_FORNECEDORES}")
    if not isinstance(state, dict):
        apply_data_editor_changes(KEY_FORNECEDORES, {}, default_value_for_new_rows={"Utilizado": "Não"})
        return
    idx_map = st.session_state.get("_fornecedores_idx_map")
    if idx_map is not None and len(idx_map) > 0:
        # Remapear índices da vista filtrada para índices do dataframe completo
        edited = state.get("edited_rows", {})
        new_edited = {idx_map[int(k)]: v for k, v in edited.items() if int(k) < len(idx_map)}
        deleted = state.get("deleted_rows", [])
        new_deleted = sorted([idx_map[i] for i in deleted if i < len(idx_map)], reverse=True)
        state = {"edited_rows": new_edited, "deleted_rows": new_deleted, "added_rows": state.get("added_rows", [])}
    defaults = {"Utilizado": "Não"}
    if st.session_state.get("_fornecedores_filter_servico"):
        defaults["Serviço"] = st.session_state["_fornecedores_filter_servico"]
    apply_data_editor_changes(KEY_FORNECEDORES, state, default_value_for_new_rows=defaults)

st.data_editor(
    display_df,
    key=f"editor_{KEY_FORNECEDORES}",
    use_container_width=True,
    num_rows="dynamic",
    on_change=_apply_fornecedores,
    column_config={
        "Serviço": st.column_config.TextColumn(
            "Serviço",
            width="medium",
        ),
        "Utilizado": st.column_config.SelectboxColumn(
            "Utilizado",
            options=["Sim", "Não"],
            required=True,
            width="medium",
        ),
    },
)

c = st.session_state[KEY_FORNECEDORES]
if len(c) > 0 and "Utilizado" in c.columns:
    st.metric("Total de fornecedores", len(c))

st.divider()
st.subheader("Exportar esta secção")
csv = st.session_state[KEY_FORNECEDORES].to_csv(index=False)
st.download_button("Descarregar CSV (Fornecedores)", csv, file_name=FILE_FORNECEDORES, mime="text/csv")
