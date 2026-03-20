"""
Cronograma do dia: hora, atividade, local, notas.
Mesmo fluxo que Tarefas: não alterar o DataFrame antes do data_editor.
"""
import pandas as pd
import streamlit as st

from utils.data import (
    init_session_state,
    KEY_CRONOGRAMA,
    FILE_CRONOGRAMA,
    apply_data_editor_changes,
)

st.set_page_config(page_title="Cronograma | Dashboard Casamento", page_icon="📅", layout="wide")
init_session_state()

st.title("📅 Cronograma do dia")
st.caption("Horário do dia do casamento. Ordena por hora (ex.: 09:00, 14:30).")

def _apply_cronograma():
    state = st.session_state.get(f"editor_{KEY_CRONOGRAMA}")
    apply_data_editor_changes(KEY_CRONOGRAMA, state if isinstance(state, dict) else {})

df = st.session_state[KEY_CRONOGRAMA].reset_index(drop=True)

st.data_editor(
    df,
    key=f"editor_{KEY_CRONOGRAMA}",
    use_container_width=True,
    num_rows="dynamic",
    on_change=_apply_cronograma,
    column_config={
        "Hora": st.column_config.TextColumn(
            "Hora",
            width="medium",
        ),
    },
)

c = st.session_state[KEY_CRONOGRAMA]
if len(c) > 0 and "Hora" in c.columns:
    st.metric("Total de entradas", len(c))

st.divider()
st.subheader("Exportar esta secção")
csv = st.session_state[KEY_CRONOGRAMA].to_csv(index=False)
st.download_button("Descarregar CSV (Cronograma)", csv, file_name=FILE_CRONOGRAMA, mime="text/csv")
