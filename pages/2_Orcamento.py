"""
Orçamento: categoria, descrição, valor previsto, valor real, estado.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data import (
    init_session_state,
    KEY_ORCAMENTO,
    FILE_ORCAMENTO,
)

st.set_page_config(page_title="Orçamento | Dashboard Casamento", page_icon="💰", layout="wide")
init_session_state()

st.title("💰 Orçamento")
st.caption("Regista despesas por categoria. Estado: Previsto ou Pago.")

# Gráfico de pizza: preenchimento do orçamento por categoria (valor previsto)
c = st.session_state[KEY_ORCAMENTO]
if len(c) > 0 and "Categoria" in c.columns and "Valor previsto" in c.columns:
    c_num = c.copy()
    c_num["Valor previsto"] = pd.to_numeric(c_num["Valor previsto"], errors="coerce").fillna(0)
    por_categoria = c_num.groupby("Categoria", as_index=False)["Valor previsto"].sum()
    por_categoria = por_categoria[por_categoria["Valor previsto"] > 0]
    if len(por_categoria) > 0:
        fig = px.pie(
            por_categoria,
            values="Valor previsto",
            names="Categoria",
            title="Orçamento por categoria (valor previsto)",
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Adiciona linhas com valor previsto para ver o gráfico.")
else:
    st.caption("Adiciona dados para ver o gráfico de pizza por categoria.")

st.divider()

df = st.session_state[KEY_ORCAMENTO]

edited = st.data_editor(
    df,
    key=f"editor_{KEY_ORCAMENTO}",
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Valor previsto": st.column_config.NumberColumn(format="%.2f €"),
        "Valor real": st.column_config.NumberColumn(format="%.2f €"),
        "Estado": st.column_config.SelectboxColumn(
            "Estado",
            options=["Previsto", "Pago"],
            required=True,
            width="medium",
        ),
    },
)

if edited is not None:
    st.session_state[KEY_ORCAMENTO] = edited

# Totais
c = st.session_state[KEY_ORCAMENTO]
if len(c) > 0:
    for col in ["Valor previsto", "Valor real"]:
        if col in c.columns:
            c[col] = pd.to_numeric(c[col], errors="coerce").fillna(0)
    total_prev = c["Valor previsto"].sum()
    total_real = c["Valor real"].sum()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total previsto", f"{total_prev:.2f} €")
    with col2:
        st.metric("Total real", f"{total_real:.2f} €")

st.divider()
st.subheader("Exportar esta secção")
csv = st.session_state[KEY_ORCAMENTO].to_csv(index=False)
st.download_button("Descarregar CSV (Orçamento)", csv, file_name=FILE_ORCAMENTO, mime="text/csv")
