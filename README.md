# Dashboard do Casamento

Dashboard interativo em Streamlit para organizar o casamento: convidados, orçamento, tarefas, fornecedores e cronograma do dia.

## Como correr em local

É melhor usar um **ambiente virtual (venv)** para não misturar as dependências com o resto do teu Python. Usa um nome do projeto para distinguir de outros envs.

1. **Cria e ativa o ambiente virtual** (na pasta do projeto):

   No **PowerShell** (Windows):
   ```powershell
   py -m venv dashboard_casamento_env
   .\dashboard_casamento_env\Scripts\Activate.ps1
   ```
   Se `py` não funcionar, usa `python -m venv dashboard_casamento_env` (com o Python que tiveres no PATH).

   No **cmd** (Windows): `dashboard_casamento_env\Scripts\activate.bat`

   No **Linux/macOS**: `python3 -m venv dashboard_casamento_env` e depois `source dashboard_casamento_env/bin/activate`

2. **Instala as dependências** (com o venv ativado):
   ```powershell
   pip install -r requirements.txt
   ```

3. **Arranca a app**:
   ```powershell
   streamlit run app.py
   ```

4. Abre no browser o URL que o Streamlit mostrar (normalmente http://localhost:8501).

Quando o venv está ativo, o prompt costuma mostrar `(dashboard_casamento_env)` no início da linha. Para sair do venv: `deactivate`.

## Guardar e restaurar dados

- **Exportar:** Na página inicial, clica em "Exportar tudo (CSV)" e depois em "Descarregar ZIP com todos os CSV". Guarda o ficheiro no teu PC.
- **Importar:** Na página inicial, usa o campo "Importar backup (ZIP com CSV)" e escolhe um ficheiro ZIP exportado antes. Os dados são restaurados e a página atualiza.

Em cada secção (Convidados, Orçamento, etc.) também podes exportar só essa secção em CSV.

## Google Sheets (sincronizar dados na nuvem)

Para ter os dados numa Google Sheet (acessível de qualquer sítio e partilhável):

1. **Google Cloud Console:** Cria um projeto em [console.cloud.google.com](https://console.cloud.google.com/). Ativa a **Google Sheets API** e a **Google Drive API** (APIs e serviços → Biblioteca).

2. **Conta de serviço:** Em *IAM e administração* → *Contas de serviço*, cria uma conta (ex.: "dashboard-casamento"). Em *Chaves*, adiciona uma chave *JSON* e descarrega o ficheiro. Guarda-o em sítio seguro.

3. **Partilha a folha:** Cria uma nova Google Sheet (ou usa uma existente). No botão **Partilhar**, adiciona o **email da conta de serviço** (vem no JSON, ex.: `xxx@yyy.iam.gserviceaccount.com`) com permissão **Editor**.

4. **ID da folha:** No URL da Google Sheet aparece `.../d/ID_DA_FOLHA/edit`. Copia esse `ID_DA_FOLHA` e cola-o na app, na secção "Google Sheets".

5. **Secrets (credenciais):**
   - **Em local:** Cria a pasta `.streamlit` na raiz do projeto e dentro um ficheiro `secrets.toml`. Cola o conteúdo do ficheiro JSON da conta de serviço numa única chave, por exemplo:
     ```toml
     google_credentials_json = '''
     {"type": "service_account", "project_id": "...", "private_key_id": "...", "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n", "client_email": "...", "client_id": "..."}
     '''
     ```
     (Podes colar o JSON entre aspas triplas; escapa as aspas internas se necessário, ou guarda o JSON num ficheiro e em código lê-lo — para simplificar, no Streamlit Cloud podes usar o editor de Secrets que aceita JSON.)
   - **No Streamlit Cloud:** No teu app em share.streamlit.io, vai a *Settings* → *Secrets* e cola o mesmo conteúdo (por exemplo a chave `google_credentials_json` com o valor do JSON completo).

6. Na app: preenche o **ID da Google Sheet**, clica em **Carregar do Google Sheets** para importar o que está na folha, ou edita nas abas e depois **Guardar no Google Sheets** para enviar as alterações.

A Google Sheet deve ter (ou a app cria) 5 folhas com os nomes: **Convidados**, **Orçamento**, **Tarefas**, **Fornecedores**, **Cronograma**. As colunas devem coincidir com as da app (ao carregar pela primeira vez podes usar "Guardar no Google Sheets" com dados de exemplo para criar a estrutura).

## Deploy no Streamlit Community Cloud (gratuito)

Guia passo a passo (primeiro push no GitHub, Cloud e Secrets): ver **[DEPLOY_GITHUB_STREAMLIT.md](DEPLOY_GITHUB_STREAMLIT.md)**.

Resumo:

1. Faz push deste projeto para um repositório no GitHub (público ou privado).
2. Entra em [share.streamlit.io](https://share.streamlit.io) e faz login (por exemplo com GitHub).
3. Clica em **New app**.
4. Escolhe:
   - **Repository:** o teu repositório
   - **Branch:** normalmente `main`
   - **Main file path:** `app.py`
5. Clica em **Deploy**. A app fica disponível em `https://<nome>.streamlit.app`.
6. Em **Settings** → **Secrets**, configura `google_credentials_json` (e opcionalmente `google_spreadsheet_id` para pré-preencher o ID da folha na app).

Nota: No plano gratuito os dados não ficam guardados no servidor entre sessões. Usa "Exportar tudo" para guardar um backup e "Importar" quando abrires a app noutro dispositivo ou após a app ter estado parada.
