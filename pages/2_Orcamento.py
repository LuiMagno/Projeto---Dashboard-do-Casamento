"""
Orçamento: item, preço estipulado, método de pagamento, pagamentos por mês, totais.
Total Pago = soma das colunas mensais. A ser pago = Total a Pagar − Total Pago.
"""
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.data import (
    ORCAMENTO_MESES,
    KEY_ORCAMENTO,
    FILE_ORCAMENTO,
    ORCAMENTO_COL_A_SER_PAGO,
    apply_data_editor_changes,
    init_session_state,
    normalize_orcamento_df,
    orcamento_para_export,
    orcamento_data_editor_defaults,
)
from utils.sheets import render_save_to_google_sheets_button


def _fmt_brl(v: float) -> str:
    raw = f"{float(v):,.2f}"
    return "R$ " + raw.replace(",", "@").replace(".", ",").replace("@", ".")


def _fig_barras_pago_falta(items_df: pd.DataFrame, title: str) -> Optional[go.Figure]:
    """Barras empilhadas: base = Total Pago, topo = falta pagar (máx. 0). Rótulos em R$."""
    if items_df is None or len(items_df) == 0:
        return None
    pago = pd.to_numeric(items_df["Total Pago"], errors="coerce").fillna(0.0)
    tap = pd.to_numeric(items_df["Total a Pagar"], errors="coerce").fillna(0.0)
    falta = (tap - pago).clip(lower=0.0)
    if float(pago.sum() + falta.sum()) <= 0:
        return None
    labels = items_df["Item"].astype(str).tolist()
    pago_l = pago.tolist()
    falta_l = falta.tolist()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Pago",
            x=labels,
            y=pago_l,
            text=[_fmt_brl(v) if v > 0 else "" for v in pago_l],
            textposition="auto",
            marker_color="#1B5E20",
            textfont=dict(size=11),
        )
    )
    fig.add_trace(
        go.Bar(
            name="Falta pagar",
            x=labels,
            y=falta_l,
            text=[_fmt_brl(v) if v > 0 else "" for v in falta_l],
            textposition="auto",
            marker_color="#E65100",
            textfont=dict(size=11),
        )
    )
    fig.update_layout(
        barmode="stack",
        title=title,
        xaxis_tickangle=-40,
        height=440,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(b=140, t=80),
        yaxis_title="R$",
    )
    return fig


st.set_page_config(page_title="Orçamento | Dashboard Casamento", page_icon="💰", layout="wide")
init_session_state()

st.title("💰 Orçamento")
st.caption(
    "Preenche por linha: preço combinado, método de pagamento e **valores pagos em cada mês**. "
    "**Total Pago** é a soma automática desses meses. **A ser pago** é calculado (legenda abaixo da tabela)."
)

df_base = normalize_orcamento_df(st.session_state[KEY_ORCAMENTO]).reset_index(drop=True)
tp_view = pd.to_numeric(df_base["Total Pago"], errors="coerce").fillna(0.0)
tap_view = pd.to_numeric(df_base["Total a Pagar"], errors="coerce").fillna(0.0)
df_display = df_base.copy()
df_display.insert(
    df_display.columns.get_loc("Total a Pagar") + 1,
    ORCAMENTO_COL_A_SER_PAGO,
    tap_view - tp_view,
)


def _apply_orcamento():
    state = st.session_state.get(f"editor_{KEY_ORCAMENTO}")
    defaults = orcamento_data_editor_defaults()
    if not isinstance(state, dict):
        apply_data_editor_changes(KEY_ORCAMENTO, {}, default_value_for_new_rows=defaults)
        return
    apply_data_editor_changes(KEY_ORCAMENTO, state, default_value_for_new_rows=defaults)


st.subheader("Visão geral")
col_est, col_pago = st.columns(2)

with col_est:
    if len(df_base) > 0 and pd.to_numeric(df_base["Preço estipulado"], errors="coerce").fillna(0).sum() > 0:
        c_num = df_base.copy()
        c_num["Preço estipulado"] = pd.to_numeric(c_num["Preço estipulado"], errors="coerce").fillna(0)
        por_item = c_num[c_num["Item"].astype(str).str.strip() != ""]
        por_item = por_item[por_item["Preço estipulado"] > 0]
        if len(por_item) > 0:
            fig = px.pie(
                por_item,
                values="Preço estipulado",
                names="Item",
                title="Preço estipulado por item",
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Preenche **Preço estipulado** em pelo menos um item para ver este gráfico.")
    else:
        st.caption("Adiciona linhas com preço estipulado para ver este gráfico.")

with col_pago:
    if len(df_base) > 0:
        c_pago = df_base.copy()
        c_pago["Total Pago"] = pd.to_numeric(c_pago["Total Pago"], errors="coerce").fillna(0)
        por_pago = c_pago[c_pago["Item"].astype(str).str.strip() != ""]
        por_pago = por_pago[por_pago["Total Pago"] > 0]
        if len(por_pago) > 0:
            fig_pago = px.pie(
                por_pago,
                values="Total Pago",
                names="Item",
                title="Já pago por item (parte do total já pago)",
            )
            fig_pago.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pago, use_container_width=True)
        else:
            st.caption("Regista valores nos **meses** (soma = Total Pago) para ver este gráfico.")
    else:
        st.caption("Sem linhas de orçamento.")

if len(df_base) > 0:
    df_b = df_base[df_base["Item"].astype(str).str.strip() != ""].copy()
    tp_b = pd.to_numeric(df_b["Total Pago"], errors="coerce").fillna(0)
    tap_b = pd.to_numeric(df_b["Total a Pagar"], errors="coerce").fillna(0)
    df_b = df_b[(tp_b > 0) | (tap_b > 0)]
    fig_b = _fig_barras_pago_falta(df_b, "Pago vs falta pagar por item")
    if fig_b is not None:
        st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.caption("Preenche **Total a Pagar** ou **meses** para ver as barras.")
else:
    st.caption("Sem dados para barras.")

st.divider()

money_fmt = {"format": "%.2f", "min_value": 0.0, "step": 1.0}
column_config = {
    "Item": st.column_config.TextColumn("Item", width="large"),
    "Preço estipulado": st.column_config.NumberColumn("Preço estipulado (R$)", **money_fmt),
    "Método de Pgto": st.column_config.TextColumn("Método de Pgto", width="small"),
}
for m in ORCAMENTO_MESES:
    column_config[m] = st.column_config.NumberColumn(m, width="small", **money_fmt)
column_config["Total Pago"] = st.column_config.NumberColumn(
    "Total Pago (R$) = soma dos meses",
    disabled=True,
    help="Soma automática das colunas jan.–nov. Atualiza ao editar qualquer mês.",
    **money_fmt,
)
column_config["Total a Pagar"] = st.column_config.NumberColumn("Total a Pagar (R$)", **money_fmt)
column_config[ORCAMENTO_COL_A_SER_PAGO] = st.column_config.NumberColumn(
    "A ser pago (R$) = Total a Pagar − Total Pago",
    disabled=True,
    help="Atualiza ao mudar Total a Pagar ou os valores nos meses.",
    format="%.2f",
    step=1.0,
)

st.data_editor(
    df_display,
    key=f"editor_{KEY_ORCAMENTO}",
    use_container_width=True,
    num_rows="dynamic",
    column_config=column_config,
    hide_index=True,
    on_change=_apply_orcamento,
)

st.caption(
    "**Total Pago:** soma dos valores em *jan./2026* … *nov./26*. "
    "**A ser pago:** *Total a Pagar* − *Total Pago*."
)

if len(df_base) > 0:
    total_stip = float(pd.to_numeric(df_base["Preço estipulado"], errors="coerce").fillna(0).sum())
    total_pago = float(tp_view.sum())
    total_a_pagar = float((tap_view - tp_view).sum())
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total estipulado", _fmt_brl(total_stip))
    with m2:
        st.metric("Total pago (já pago)", _fmt_brl(total_pago))
    with m3:
        st.metric("Total a pagar", _fmt_brl(total_a_pagar), help="Soma da coluna A ser pago (Total a Pagar − Total Pago, por linha).")

render_save_to_google_sheets_button("orcamento")

st.divider()
st.subheader("Exportar esta secção")
csv = orcamento_para_export(st.session_state[KEY_ORCAMENTO]).to_csv(index=False)
st.download_button("Descarregar CSV (Orçamento)", csv, file_name=FILE_ORCAMENTO, mime="text/csv")
