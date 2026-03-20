# GitHub + Streamlit Community Cloud (checklist)

Este projeto já tem `git` inicializado na pasta com um commit na branch `main`. Falta criar o repositório remoto no GitHub (no browser ou com [GitHub CLI](https://cli.github.com/)) e fazer o primeiro push.

## 1. Primeiro push para o GitHub

1. No GitHub: **New repository** — escolhe um nome (ex.: `dashboard-do-casamento`). **Não** marques "Add a README" (o projeto já tem um).
2. Na pasta do projeto, no PowerShell:

```powershell
cd "C:\Users\luimagno\Documents\GitHub\Projeto - Dashboard do Casamento"
git remote add origin https://github.com/TEU_UTILIZADOR/NOME_DO_REPO.git
git push -u origin main
```

Substitui `TEU_UTILIZADOR` e `NOME_DO_REPO`. Se pedir login, usa o método que o Git te sugerir (navegador ou token).

**Ficheiros que nunca devem ir para o GitHub** (já estão no `.gitignore`): `.streamlit/secrets.toml`, `credentials.json`, `projeto-dashboard-casamento-*.json`, pasta `dashboard_casamento_env/`.

## 2. Streamlit Community Cloud (grátis)

1. Abre [share.streamlit.io](https://share.streamlit.io) e entra com GitHub.
2. **New app** → repositório que acabaste de criar → branch **main** → **Main file path:** `app.py` → **Deploy**.
3. Se a app falhar por falta de credenciais Google, vai a **App settings** (ícone ⚙️) → **Secrets** e cola um bloco TOML como o do teu `secrets.toml` local (mínimo: JSON da conta de serviço).

Exemplo (adapta o JSON — uma linha ou multilinha com `'''` como no [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)):

```toml
google_credentials_json = '''
{ "type": "service_account", "project_id": "...", ... }
'''

# Opcional: ID da folha pré-preenchido na app
# google_spreadsheet_id = "1abc...xyz"
```

4. Na Google Sheet, partilha a folha com o **client_email** da conta de serviço (permissão **Editor**).

## 3. Verificação (smoke test)

Depois do deploy:

- [ ] Abre o URL `https://<nome>.streamlit.app` e confirma que a home carrega.
- [ ] Se usas Sheets: **Carregar do Google Sheets** / **Guardar no Google Sheets** sem erro.
- [ ] Lembra-te: no plano gratuito o estado em memória não persiste — usa **Exportar tudo (ZIP)** na app para backup e **Importar** quando precisares.
