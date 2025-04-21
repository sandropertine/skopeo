import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from modulo_importar_pdf_multidisciplinar import executar
from modulo_pdf_logo import gerar_relatorio_pdf

st.set_page_config(page_title="Skopeo - Sistema Escolar Multidisciplinar", layout="wide")

# Logo e nome da escola

# Funções de configuração persistente
CONFIG_FILE = "config.json"

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config = carregar_config()

if "nome_escola" not in st.session_state:
    st.session_state.nome_escola = config.get("nome_escola", "Skopeo - Sistema Escolar Multidisciplinar")
import base64

def carregar_logo_base64(caminho):
    with open(caminho, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

logo_skopeo_base64 = carregar_logo_base64("logo_skopeo.png")
logo_escola_base64 = ""
if os.path.exists("logo_escola.png"):
    logo_escola_base64 = carregar_logo_base64("logo_escola.png")

nome_escola = st.session_state.get("nome_escola", "Skopeo - Sistema Escolar Multidisciplinar")



# Estado de sessão

# Cabeçalho com nome da escola e logos (exibido apenas após login)
if "autenticado" in st.session_state and st.session_state.autenticado:
    st.markdown(f"""
        <div style='display: flex; align-items: center; justify-content: space-between;'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                {f"<img src='data:image/png;base64,{logo_escola_base64}' style='height: 60px;'>" if logo_escola_base64 else ""}
                <h2 style='margin: 0;'>{nome_escola}</h2>
            </div>
            <img src='data:image/png;base64,{logo_skopeo_base64}' style='height: 50px;'>
        </div>
    """, unsafe_allow_html=True)

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "email_login" not in st.session_state:
    st.session_state.email_login = config.get("email_login", "admin@escola.com")
if "senha_login" not in st.session_state:
    st.session_state.senha_login = config.get("senha_login", "1234")
if "nome_escola" not in st.session_state:
    st.session_state.nome_escola = config.get("nome_escola", "Skopeo - Sistema Escolar Multidisciplinar")
if "recomendacoes" not in st.session_state:
    st.session_state.recomendacoes = {
        "Aprovado": "Desempenho adequado. Manter acompanhamento regular.",
        "Reforço": "Encaminhar para apoio pedagógico e revisão de conteúdos.",
        "Reprovado": "Plano de recuperação individual. Avaliar causas da dificuldade."
    }

# Login
if not st.session_state.autenticado:
    st.image("logo_skopeo.png", width=150)
    st.title("🔐 Acesso Restrito - Coordenação")
    email = st.text_input("E-mail institucional")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if email.strip().lower() == "cp.pedromaciel@gmail.com" and senha.strip() == "1234":
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("E-mail ou senha incorretos.")
    st.stop()

# Botão de logout
st.sidebar.button("🚪 Sair", on_click=lambda: st.session_state.clear())

# Menu lateral
st.sidebar.title("Menu")
opcao = st.sidebar.radio("Escolha uma opção", ["Importar PDF", "Análise por Aluno", "Ranking da Turma", "Análise por Turma", "Configurações"])

# Importação
if opcao == "Importar PDF":
    df, trimestre = executar()
    if df is not None:
        st.success("Importação concluída com sucesso.")

# Análise do aluno
elif opcao == "Análise por Aluno":
    base_dir = "dados"
    if not os.path.exists(base_dir):
        st.warning("Nenhum dado encontrado.")
        st.stop()

    trimestres = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not trimestres:
        st.warning("Nenhum trimestre salvo.")
        st.stop()

    trimestre = st.selectbox("Selecione o trimestre", trimestres)
    caminho_trimestre = os.path.join(base_dir, trimestre)
    arquivos = os.listdir(caminho_trimestre)

    if not arquivos:
        st.warning("Nenhuma disciplina importada neste trimestre.")
        st.stop()

    dados_por_disciplina = {}
    nomes_unicos = set()
    for arq in arquivos:
        df = pd.read_csv(os.path.join(caminho_trimestre, arq))
        nome_disc = arq.replace(".csv", "").replace("_", " ").title()
        df["trimestre"] = trimestre
        dados_por_disciplina[nome_disc] = df
        nomes_unicos.update(df["nome"].tolist())

    aluno = st.selectbox("Selecione o aluno", sorted(nomes_unicos))

    st.subheader(f"📊 Desempenho Multidisciplinar - {aluno}")
    resumo = []
    notas = {}
    historico = []
    for nome_disc, df in dados_por_disciplina.items():
        if aluno in df["nome"].values:
            dados = df[df["nome"] == aluno].iloc[0]
            resumo.append([nome_disc, dados["nota"], dados["faltas"], dados["situação"]])
            notas[nome_disc] = dados["nota"]
            historico.append({"Disciplina": nome_disc, "Nota": dados["nota"], "Trimestre": dados["trimestre"]})

    if resumo:
        df_resumo = pd.DataFrame(resumo, columns=["Disciplina", "Nota", "Faltas", "Situação"])
        st.dataframe(df_resumo)

        col1, col2 = st.columns(2)
        with col1:
            fig_bar_faltas = px.bar(df_resumo, x="Disciplina", y="Faltas", title="Faltas por Disciplina")
            st.plotly_chart(fig_bar_faltas)

        with col2:
            fig_bar_notas = px.bar(df_resumo, x="Disciplina", y="Nota", title="Notas por Disciplina")
            st.plotly_chart(fig_bar_notas)

        fig_radar = px.line_polar(r=df_resumo["Nota"], theta=df_resumo["Disciplina"], line_close=True, title="Radar de Desempenho")
        st.plotly_chart(fig_radar)

        df_historico = pd.DataFrame(historico)
        fig_evolucao = px.line(df_historico, x="Disciplina", y="Nota", markers=True, title="Evolução por Trimestre", color="Trimestre")
        st.plotly_chart(fig_evolucao)

        media = df_resumo["Nota"].mean()
        if media >= 7:
            status = "Aprovado"
        elif media >= 5:
            status = "Reforço"
        else:
            status = "Reprovado"

        comentario = st.session_state.recomendacoes.get(status, "")
        st.markdown(f"**Média Geral:** `{media:.2f}`")
        st.markdown(f"**Situação:** `{status}`")
        st.info(comentario)

# Ranking da Turma (em breve)
elif opcao == "Ranking da Turma":
    base_dir = "dados"
    if not os.path.exists(base_dir):
        st.warning("Nenhum dado encontrado.")
        st.stop()

    trimestres = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not trimestres:
        st.warning("Nenhum trimestre salvo.")
        st.stop()

    trimestre = st.selectbox("Selecione o trimestre", trimestres)
    caminho_trimestre = os.path.join(base_dir, trimestre)
    arquivos = os.listdir(caminho_trimestre)

    if not arquivos:
        st.warning("Nenhuma disciplina importada neste trimestre.")
        st.stop()

    total_geral = []
    for arq in arquivos:
        df = pd.read_csv(os.path.join(caminho_trimestre, arq))
        total_geral.append(df)

    df_total = pd.concat(total_geral)
    medias_aluno = df_total.groupby("nome")["nota"].mean().reset_index(name="media")
    top_10 = medias_aluno.sort_values("media", ascending=False).head(10)

    criterio = st.selectbox("Classificar por", ["Média Geral", "Menos Faltas"])

    if criterio == "Média Geral":
        ranking = df_total.groupby("nome")["nota"].mean().reset_index(name="media")
        ranking = ranking.sort_values("media", ascending=False).head(10)
        st.markdown(f"## 🏆 Top 10 por Média - {trimestre}")
        st.dataframe(ranking.reset_index(drop=True))
        fig_top10 = px.bar(ranking.sort_values("media"), x="nome", y="media", title="Top 10 - Média Geral")
        st.plotly_chart(fig_top10)

    elif criterio == "Menos Faltas":
        ranking = df_total.groupby("nome")["faltas"].sum().reset_index(name="faltas")
        ranking = ranking.sort_values("faltas").head(10)
        st.markdown(f"## 🏆 Top 10 por Menos Faltas - {trimestre}")
        st.dataframe(ranking.reset_index(drop=True))
        fig_top10_faltas = px.bar(ranking.sort_values("faltas", ascending=True), x="nome", y="faltas", title="Top 10 - Menos Faltas")
        st.plotly_chart(fig_top10_faltas)

# Análise por Turma
elif opcao == "Análise por Turma":
    base_dir = "dados"
    if not os.path.exists(base_dir):
        st.warning("Nenhum dado encontrado.")
        st.stop()

    trimestres = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not trimestres:
        st.warning("Nenhum trimestre salvo.")
        st.stop()

    trimestre = st.selectbox("Selecione o trimestre", trimestres)
    caminho_trimestre = os.path.join(base_dir, trimestre)
    arquivos = os.listdir(caminho_trimestre)

    if not arquivos:
        st.warning("Nenhuma disciplina importada neste trimestre.")
        st.stop()

    st.markdown(f"## 📊 Indicadores da Turma - {trimestre}")

    total_geral = []
    for arq in arquivos:
        df = pd.read_csv(os.path.join(caminho_trimestre, arq))
        df["disciplina"] = arq.replace(".csv", "").replace("_", " ").title()
        total_geral.append(df)

    df_total = pd.concat(total_geral)

    # Filtro por disciplina
    disciplinas_disponiveis = sorted(df_total["disciplina"].unique())
    disciplinas_filtradas = st.multiselect("Filtrar por disciplina", disciplinas_disponiveis, default=disciplinas_disponiveis)
    df_total = df_total[df_total["disciplina"].isin(disciplinas_filtradas)]

    # Filtro por aluno
    alunos_disponiveis = sorted(df_total["nome"].unique())
    alunos_filtrados = st.multiselect("Filtrar por aluno", alunos_disponiveis, default=alunos_disponiveis)
    df_total = df_total[df_total["nome"].isin(alunos_filtrados)]

    # Filtro por turma (se disponível)
    turmas_disponiveis = sorted(df_total["turma"].unique()) if "turma" in df_total.columns else []
    if turmas_disponiveis:
        turma_selecionada = st.selectbox("Filtrar por turma", turmas_disponiveis)
        df_total = df_total[df_total["turma"] == turma_selecionada]
    else:
        turma_selecionada = "Todas"

    # Média por aluno
    medias_aluno = df_total.groupby("nome")["nota"].mean().reset_index(name="media")
    st.subheader(f"🏅 Ranking dos Alunos (por Média) - Turma: {turma_selecionada}")
    st.dataframe(medias_aluno.sort_values("media", ascending=False))

    # Comparativo entre turmas (se disponível)
    if "turma" in df_total.columns:
        df_geral = pd.concat(total_geral)  # usar todos os dados do trimestre
        df_geral = df_geral[df_geral["disciplina"].isin(disciplinas_filtradas)]
        df_geral = df_geral[df_geral["nome"].isin(alunos_filtrados)]
        medias_turmas = df_geral.groupby("turma")["nota"].mean().reset_index(name="media_geral")
        fig_turmas = px.bar(medias_turmas.sort_values("media_geral", ascending=False), x="turma", y="media_geral", title="Comparativo entre Turmas - Média Geral")
        st.plotly_chart(fig_turmas)

    # Gráfico de barra
    nome_pdf = st.text_input("Nome do arquivo PDF", value=f"relatorio_turma_{trimestre}.pdf")
    if st.button("📄 Gerar Relatório PDF da Turma Filtrada"):
        dados_pdf = []
        for nome in alunos_filtrados:
            media = medias_aluno.loc[medias_aluno["nome"] == nome, "media"].values[0]
            faltas = faltas_aluno.loc[faltas_aluno["nome"] == nome, "total_faltas"].values[0]
            dados_pdf.append([nome, f"{media:.2f}", int(faltas)])

        gerar_relatorio_pdf(dados_pdf + [["", "", ""]] + [["Comparativo entre Turmas"]] + medias_turmas.values.tolist(), nome_arquivo=nome_pdf)
        st.success(f"Relatório PDF '{nome_pdf}' gerado com sucesso!")

        with open(nome_pdf, "rb") as f:
            st.download_button(
                label="⬇️ Baixar Relatório PDF",
                data=f.read(),
                file_name=nome_pdf,
                mime="application/pdf"
            )

# Configurações
elif opcao == "Configurações":
    st.subheader("⚙️ Configurações do Sistema")
    st.markdown("Configure mensagens, parâmetros e identidade visual.")

    st.markdown("### ✏️ Mensagens Personalizadas")
    for chave in ["Aprovado", "Reforço", "Reprovado"]:
        nova_msg = st.text_area(f"Mensagem para situação: {chave}", value=st.session_state.recomendacoes.get(chave, ""))
        st.session_state.recomendacoes[chave] = nova_msg

    

    st.markdown("### 🏫 Identidade da Escola")
    nome_escola = st.text_input("Nome da escola", value=st.session_state.get("nome_escola", "Skopeo - Sistema Escolar Multidisciplinar"))
    st.session_state.nome_escola = nome_escola
    config["nome_escola"] = nome_escola
    salvar_config(config)
    st.markdown(f"Nome salvo: **{nome_escola}**")

    st.markdown("Faça upload da logo (PNG):")
    logo_upload = st.file_uploader("Upload da Logo", type=["png"])
    if logo_upload:
        with open("logo_escola.png", "wb") as f:
            f.write(logo_upload.read())
        config["logo_escola"] = "logo_escola.png"
        salvar_config(config)
        st.success("Logo atualizada com sucesso!")

    st.markdown("### 📤 Exportações")
    st.write("Mais opções de exportação serão disponibilizadas em breve.")
