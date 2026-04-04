"""
Dashboard do Casamento - Página inicial.
Use a barra lateral para navegar entre Convidados, Orçamento, Tarefas, Fornecedores e Cronograma.
"""
import streamlit as st

from utils.data import (
    init_session_state,
    export_all_csv,
    import_from_uploaded,
    load_mock_data,
    clear_all_data,
    KEY_CONVIDADOS,
    KEY_ORCAMENTO,
    KEY_TAREFAS,
    KEY_FORNECEDORES,
    KEY_CRONOGRAMA,
)

st.set_page_config(
    page_title="Dashboard do Casamento",
    page_icon="💒",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

# Modo de dados (vazios vs exemplo) — só reage quando o utilizador muda a caixa
if "data_mode" not in st.session_state:
    st.session_state["data_mode"] = "Vazios"

st.title("💒 Dashboard do Casamento")
st.markdown("Organiza convidados, orçamento, tarefas, fornecedores e cronograma num só sítio.")
st.divider()

st.subheader("Dados de teste")
opcao = st.selectbox(
    "Usar dados:",
    ["Vazios", "Dados de exemplo"],
    index=0 if st.session_state["data_mode"] == "Vazios" else 1,
    help="Escolhe 'Dados de exemplo' para ver o dashboard preenchido e testar.",
)
if opcao != st.session_state["data_mode"]:
    st.session_state["data_mode"] = opcao
    if opcao == "Dados de exemplo":
        load_mock_data()
    else:
        clear_all_data()
    st.rerun()

st.subheader("Exportar e importar dados")
st.caption("Guarda uma cópia de todos os dados no teu PC ou restaura a partir de ficheiros exportados.")

col1, col2 = st.columns(2)

with col1:
    if st.button("📥 Exportar tudo (CSV)", use_container_width=True):
        zip_buffer = export_all_csv()
        if zip_buffer:
            st.session_state["_export_zip"] = zip_buffer.getvalue()
    if "_export_zip" in st.session_state:
        st.download_button(
            label="Descarregar ZIP com todos os CSV",
            data=st.session_state["_export_zip"],
            file_name="dashboard_casamento_backup.zip",
            mime="application/zip",
            use_container_width=True,
            key="dl_zip_all",
        )

with col2:
    uploaded = st.file_uploader(
        "Importar backup (ZIP com CSV)",
        type=["zip"],
        help="Escolhe um ficheiro ZIP exportado anteriormente por esta app.",
    )
    if uploaded is not None:
        success, msg = import_from_uploaded(uploaded)
        if success:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

st.divider()
st.subheader("Google Sheets")
st.caption("Sincroniza os dados com uma folha de cálculo Google. Configura as credenciais em Secrets (ver README).")
if "spreadsheet_id" not in st.session_state:
    default_id = ""
    if hasattr(st, "secrets") and st.secrets and "google_spreadsheet_id" in st.secrets:
        default_id = str(st.secrets.get("google_spreadsheet_id", "")).strip()
    st.session_state["spreadsheet_id"] = default_id

spreadsheet_id = st.text_input(
    "ID da Google Sheet",
    value=st.session_state["spreadsheet_id"],
    placeholder="Ex.: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    help="Encontra-se no URL da folha: docs.google.com/spreadsheets/d/ESTE_ID/edit",
)
if spreadsheet_id.strip():
    st.session_state["spreadsheet_id"] = spreadsheet_id.strip()

try:
    from utils.sheets import (
        credentials_secrets_hint,
        load_from_sheets,
        save_to_sheets,
        sheets_available,
    )

    if sheets_available():
        col_gs1, col_gs2 = st.columns(2)
        with col_gs1:
            if st.button("📥 Carregar do Google Sheets", use_container_width=True) and spreadsheet_id.strip():
                try:
                    data = load_from_sheets(spreadsheet_id.strip())
                    st.session_state[KEY_CONVIDADOS] = data.get(KEY_CONVIDADOS, st.session_state[KEY_CONVIDADOS])
                    st.session_state[KEY_ORCAMENTO] = data.get(KEY_ORCAMENTO, st.session_state[KEY_ORCAMENTO])
                    st.session_state[KEY_TAREFAS] = data.get(KEY_TAREFAS, st.session_state[KEY_TAREFAS])
                    st.session_state[KEY_FORNECEDORES] = data.get(KEY_FORNECEDORES, st.session_state[KEY_FORNECEDORES])
                    st.session_state[KEY_CRONOGRAMA] = data.get(KEY_CRONOGRAMA, st.session_state[KEY_CRONOGRAMA])
                    st.success("Dados carregados do Google Sheets. A página vai atualizar.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with col_gs2:
            if st.button("📤 Guardar no Google Sheets", use_container_width=True) and spreadsheet_id.strip():
                try:
                    save_to_sheets(
                        spreadsheet_id.strip(),
                        {
                            KEY_CONVIDADOS: st.session_state[KEY_CONVIDADOS],
                            KEY_ORCAMENTO: st.session_state[KEY_ORCAMENTO],
                            KEY_TAREFAS: st.session_state[KEY_TAREFAS],
                            KEY_FORNECEDORES: st.session_state[KEY_FORNECEDORES],
                            KEY_CRONOGRAMA: st.session_state[KEY_CRONOGRAMA],
                        },
                    )
                    st.success("Dados guardados no Google Sheets.")
                except Exception as e:
                    st.error(str(e))
    else:
        has_sheet_id = bool(spreadsheet_id.strip()) or (
            hasattr(st, "secrets")
            and st.secrets
            and str(st.secrets.get("google_spreadsheet_id", "")).strip()
        )
        if has_sheet_id:
            st.warning(
                "O **ID da Google Sheet** já está definido, mas a app **não conseguiu ler as credenciais** "
                "(`google_credentials_json` nos Secrets, ou JSON inválido após colar). "
                "Confirma que a chave se chama exatamente `google_credentials_json`, que o valor é JSON válido "
                "(experimenta uma única linha minificada), guarda os Secrets e reinicia a app. "
                "Vê também os **logs** da app no Streamlit Cloud se o erro persistir."
            )
            hint = credentials_secrets_hint()
            if hint:
                st.error(hint)
        with st.expander("Como configurar o Google Sheets"):
            st.markdown("""
1. **Google Cloud:** Cria um projeto em [Google Cloud Console](https://console.cloud.google.com/), ativa a **Google Sheets API** e a **Google Drive API**.
2. **Conta de serviço:** Em *IAM e administração* → *Contas de serviço*, cria uma conta e gera uma chave JSON. Descarrega o ficheiro.
3. **Partilha a folha:** Abre a tua Google Sheet e partilha-a (botão Partilhar) com o **email da conta de serviço** (ex.: `xxx@yyy.iam.gserviceaccount.com`) com permissão **Editor**.
4. **Secrets (local):** Cria `.streamlit/secrets.toml` e cola o conteúdo do JSON sob a chave `google_credentials_json` (como string) ou usa as chaves individuais em `[google_credentials]`.
5. **Streamlit Cloud:** No deploy, em *Settings* → *Secrets*, adiciona a mesma estrutura.
6. O **ID da folha** vem do URL do Google Sheets (`.../d/ID_DA_FOLHA/edit`) ou da chave opcional `google_spreadsheet_id` nos Secrets — não do URL `streamlit.app`.
            """)
except ImportError:
    st.warning("Para usar Google Sheets, instala: `pip install gspread google-auth`")

st.divider()
st.markdown("**Navegação:** usa o menu à esquerda para aceder a cada secção.")
