"""
Lista de convidados: nome, contacto, confirmação, mesa, notas.
"""
import pandas as pd
import streamlit as st

from utils.data import (
    init_session_state,
    KEY_CONVIDADOS,
    FILE_CONVIDADOS,
    apply_data_editor_changes,
)
from utils.sheets import render_save_to_google_sheets_button

st.set_page_config(page_title="Convidados | Dashboard Casamento", page_icon="👥", layout="wide")
init_session_state()

st.title("👥 Convidados")
st.caption(
    "Adiciona e edita convidados. **Confirmação:** Sim, Não ou Pendente. "
    "Valores vazios ou inválidos passam a **Pendente** ao atualizar a tabela."
)

def _apply_convidados():
    state = st.session_state.get(f"editor_{KEY_CONVIDADOS}")
    defaults = {"Confirmação": "Pendente"}
    apply_data_editor_changes(KEY_CONVIDADOS, state if isinstance(state, dict) else {}, default_value_for_new_rows=defaults)


df = st.session_state[KEY_CONVIDADOS].reset_index(drop=True)

st.data_editor(
    df,
    key=f"editor_{KEY_CONVIDADOS}",
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    on_change=_apply_convidados,
    column_config={
        "Confirmação": st.column_config.SelectboxColumn(
            "Confirmação",
            options=["Pendente", "Sim", "Não"],
            required=False,
            width="medium",
            help="Se deixares vazio, a app trata como Pendente ao gravar.",
        ),
    },
)

# Resumos
if len(st.session_state[KEY_CONVIDADOS]) > 0:
    c = st.session_state[KEY_CONVIDADOS]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", len(c))
    with col2:
        st.metric("Sim", len(c[c["Confirmação"].astype(str).str.strip().str.lower() == "sim"]))
    with col3:
        st.metric("Não", len(c[c["Confirmação"].astype(str).str.strip().str.lower() == "não"]))
    with col4:
        st.metric("Pendente", len(c[c["Confirmação"].astype(str).str.strip().str.lower() == "pendente"]))

render_save_to_google_sheets_button("convidados")

st.divider()
st.subheader("Exportar esta secção")
csv = st.session_state[KEY_CONVIDADOS].to_csv(index=False)
st.download_button("Descarregar CSV (Convidados)", csv, file_name=FILE_CONVIDADOS, mime="text/csv")
