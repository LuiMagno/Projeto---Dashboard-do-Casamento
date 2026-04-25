"""
Checklist de tarefas: tarefa, responsável, data limite, concluída.
"""
import pandas as pd
import streamlit as st

from utils.data import (
    init_session_state,
    KEY_TAREFAS,
    FILE_TAREFAS,
    apply_data_editor_changes,
)
from utils.sheets import render_save_to_google_sheets_button

st.set_page_config(page_title="Tarefas | Dashboard Casamento", page_icon="✅", layout="wide")
init_session_state()

st.title("✅ Tarefas")
st.caption("Lista de tarefas antes do dia. Marca como Sim quando estiver concluída.")

def _apply_tarefas():
    state = st.session_state.get(f"editor_{KEY_TAREFAS}")
    apply_data_editor_changes(KEY_TAREFAS, state if isinstance(state, dict) else {})

df = st.session_state[KEY_TAREFAS].reset_index(drop=True)

st.data_editor(
    df,
    key=f"editor_{KEY_TAREFAS}",
    use_container_width=True,
    num_rows="dynamic",
    on_change=_apply_tarefas,
    column_config={
        "Concluída": st.column_config.SelectboxColumn(
            "Concluída",
            options=["Não", "Sim"],
            required=True,
            width="medium",
        ),
    },
)

c = st.session_state[KEY_TAREFAS]
if len(c) > 0 and "Concluída" in c.columns:
    concl = (c["Concluída"].astype(str).str.strip().str.lower() == "sim").sum()
    st.metric("Concluídas", f"{concl} / {len(c)}")

render_save_to_google_sheets_button("tarefas")

st.divider()
st.subheader("Exportar esta secção")
csv = st.session_state[KEY_TAREFAS].to_csv(index=False)
st.download_button("Descarregar CSV (Tarefas)", csv, file_name=FILE_TAREFAS, mime="text/csv")
