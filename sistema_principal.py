
import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from modulo_importar_pdf_multidisciplinar import executar
from modulo_pdf_logo import gerar_relatorio_pdf
import base64

from pathlib import Path
import sys
BASE_PATH = Path(getattr(sys, '_MEIPASS', Path.cwd()))

# ====== Inicialização segura da sessão ======
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "email_login" not in st.session_state:
    st.session_state.email_login = "cp.pedromaciel@gmail.com"
if "senha_login" not in st.session_state:
    st.session_state.senha_login = "1234"

# ====== Login ======
if not st.session_state.autenticado:
    st.image(str(BASE_PATH / "logo_skopeo.png"), width=200)
    st.markdown("### 🔒 Acesso Restrito — Skopeo")
    email = st.text_input("E-mail institucional")
    senha = st.text_input("Senha de acesso", type="password")
    if st.button("Entrar"):
        if email == st.session_state.email_login and senha == st.session_state.senha_login:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Credenciais inválidas.")
    st.stop()

# ====== Após Login - Configuração inicial ======
st.set_page_config(page_title="Skopeo - Sistema Escolar Multidisciplinar", layout="wide")

CONFIG_FILE = "config.json"

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def carregar_logo_base64(caminho):
    with open(caminho, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def carregar_dados_trimestre(path_trimestre: str) -> pd.DataFrame:
    dados_disciplina = []
    arquivos = [f for f in os.listdir(path_trimestre) if f.endswith(".csv")]
    for arq in arquivos:
        try:
            df = pd.read_csv(os.path.join(path_trimestre, arq))
            df["disciplina"] = arq.replace(".csv", "").replace("_", " ").title()
            dados_disciplina.append(df)
        except Exception as e:
            print(f"Erro ao ler {arq}: {e}")
    if not dados_disciplina:
        return pd.DataFrame()
    return pd.concat(dados_disciplina, ignore_index=True)

def garantir_diretorio_dados():
    os.makedirs("dados", exist_ok=True)

# Carrega config e define estado
default_config = {
    "nome_escola": "Skopeo - Sistema Escolar Multidisciplinar",
    "logo_escola_path": "",
    "endereco": "",
    "telefone": "",
    "export_fields": ["Aluno", "Turma", "Trimestre", "Media"],
    "diag_aprovado": "Desempenho adequado. Manter acompanhamento regular.",
    "diag_reforco": "Encaminhar para apoio pedagógico e revisão de conteúdos.",
    "diag_reprovado": "Plano de recuperação individual. Avaliar causas da dificuldade."
}
config = carregar_config()
for key, val in default_config.items():
    config.setdefault(key, val)

# Atualiza sessão com recomendações
st.session_state.recomendacoes = {
    "Aprovado": config["diag_aprovado"],
    "Reforço": config["diag_reforco"],
    "Reprovado": config["diag_reprovado"]
}

# Cabeçalho
col_logo, col_title = st.columns([1, 8])
with col_logo:
    if config.get("logo_escola_path") and os.path.exists(config["logo_escola_path"]):
        st.image(config["logo_escola_path"], width=80)
    else:
        st.image(str(BASE_PATH / "logo_skopeo.png"), width=80)
with col_title:
    st.markdown(f"## {config['nome_escola']}")

# Menu lateral
opcao = st.sidebar.radio("Escolha uma opção", [
    "Importar PDF",
    "Análise por Aluno",
    "Análise por Turma",
    "Ranking da Turma",
    "Painel Geral",
    "Configurações"
])


if opcao == "Importar PDF":
    st.title("📥 Importar PDF")
    executar()

elif opcao == "Painel Geral":
    st.title("📈 Painel Geral da Escola")

    base_dir = "dados"
    garantir_diretorio_dados()
    trimestres = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])

    if not trimestres:
        st.warning("Nenhum dado disponível.")
        st.stop()

    etapas = ["Fundamental II", "Ensino Médio"]
    etapa_selecionada = st.selectbox("Selecione a etapa de ensino", etapas)

    trimestre = st.selectbox("Selecione o trimestre", trimestres)
    caminho = os.path.join(base_dir, trimestre)
    df = carregar_dados_trimestre(caminho)

    if df.empty:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    # Detectar etapa com base na turma
    def detectar_etapa(turma):
        if isinstance(turma, str):
            turma_lower = turma.lower()
            if turma_lower.startswith(("6º", "7º", "8º", "9º")):
                return "Fundamental II"
            elif "em" in turma_lower:
                return "Ensino Médio"
        return None

    df["etapa"] = df["turma"].apply(detectar_etapa)
    df_etapa = df[df["etapa"] == etapa_selecionada]

    if df_etapa.empty:
        st.info("Nenhum dado encontrado para a etapa selecionada neste trimestre.")
    else:
        st.markdown("### 📊 Média por Disciplina")
        df_media = df_etapa.groupby("disciplina").agg({
            "nota": "mean",
            "faltas": "sum"
        }).reset_index().rename(columns={"nota": "Média", "faltas": "Faltas Totais"})

        st.dataframe(df_media.style.format({"Média": "{:.2f}"}))

        fig_bar = px.bar(
            df_media,
            x="disciplina",
            y="Média",
            color="disciplina",
            title=f"Média por Disciplina – {etapa_selecionada} ({trimestre})"
        )
        st.plotly_chart(fig_bar)
    # 🔘 Botão para mostrar evolução por trimestre
    if st.button("📈 Ver evolução da média por trimestre"):
        medias_etapa = []
        for trim in trimestres:
            caminho_trim = os.path.join(base_dir, trim)
            df_trim = carregar_dados_trimestre(caminho_trim)

            if df_trim.empty:
                continue

            df_trim["etapa"] = df_trim["turma"].apply(detectar_etapa)
            df_e = df_trim[df_trim["etapa"] == etapa_selecionada]

            if not df_e.empty:
                media_geral = df_e["nota"].mean()
                medias_etapa.append({"Trimestre": trim, "Média": media_geral})

        if medias_etapa:
            df_medias = pd.DataFrame(medias_etapa)

            fig = px.line(
                df_medias,
                x="Trimestre",
                y="Média",
                markers=True,
                title=f"Evolução da Média Geral — {etapa_selecionada}"
            )
            st.plotly_chart(fig)
        else:
            st.info("Não há dados suficientes para gerar o gráfico de evolução.")
    if st.button("📤 Exportar Painel em PDF"):
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        if config.get("logo_escola_path") and os.path.exists(config["logo_escola_path"]):
            pdf.image(config["logo_escola_path"], x=10, y=8, w=30)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"{config['nome_escola']}", ln=True, align="C")
        if config.get("endereco") or config.get("telefone"):
            pdf.set_font("Arial", size=10)
            info = f"{config.get('endereco', '')} | {config.get('telefone', '')}"
            pdf.cell(0, 10, info.strip(" | "), ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Painel Geral - {trimestre}", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"Total de Alunos: {total_alunos}", ln=True)
        pdf.cell(0, 10, f"Média Geral das Notas: {media_geral:.2f}", ln=True)
        pdf.cell(0, 10, f"Total de Faltas: {total_faltas}", ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Média por Disciplina:", ln=True)
        pdf.set_font("Arial", size=12)
        for _, row in media_disc.iterrows():
            pdf.cell(0, 10, f"{row['disciplina']}: {row['nota']:.2f}", ln=True)

        if "turma" in df.columns:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Faltas por Turma:", ln=True)
            pdf.set_font("Arial", size=12)
            for _, row in faltas_turma.iterrows():
                pdf.cell(0, 10, f"{row['turma']}: {int(row['faltas'])} faltas", ln=True)

        nome_pdf = os.path.join("exportacoes/painel_geral", f"painel_geral_{trimestre.replace(' ', '_')}.pdf")
        os.makedirs(os.path.dirname(nome_pdf), exist_ok=True)
        pdf.output(nome_pdf)
        with open(nome_pdf, "rb") as f:
            st.download_button("📎 Baixar PDF do Painel", f, file_name=nome_pdf, mime="application/pdf")
elif opcao == "Configurações":
    st.title("⚙️ Configurações")
    nome_escola = st.text_input("Nome da Escola", value=config.get("nome_escola", ""))
    endereco = st.text_input("Endereço da Escola", value=config.get("endereco", ""))
    telefone = st.text_input("Telefone de Contato", value=config.get("telefone", ""))
    logo_uploader = st.file_uploader("Logo da Escola (PNG)", type=["png"])
    if logo_uploader:
        path = str(BASE_PATH / "logo_escola.png") if hasattr(sys, "_MEIPASS") else "logo_escola.png"
        with open(path, "wb") as f:
            f.write(logo_uploader.getbuffer())
        config["logo_escola_path"] = path

    st.markdown("### Campos para Exportação de PDF")
    fields_opts = ["Posição", "Aluno", "Turma", "Trimestre", "Media"]
    export_fields = st.multiselect("Selecione campos", options=fields_opts, default=config.get("export_fields", fields_opts))

    st.markdown("### Mensagens de Diagnóstico")
    diag_approv = st.text_area("Aprovado", value=config.get("diag_aprovado", ""))
    diag_ref = st.text_area("Reforço", value=config.get("diag_reforco", ""))
    diag_rep = st.text_area("Reprovado", value=config.get("diag_reprovado", ""))

    if st.button("Salvar Configurações"):
        config["nome_escola"] = nome_escola
        config["endereco"] = endereco
        config["telefone"] = telefone
        config["export_fields"] = export_fields
        config["diag_aprovado"] = diag_approv
        config["diag_reforco"] = diag_ref
        config["diag_reprovado"] = diag_rep
        salvar_config(config)
        st.success("Configurações salvas!")

    st.success(f"Sistema carregado. Módulo selecionado: **{opcao}**")


elif opcao == "Análise por Aluno":
    st.title("📘 Análise por Aluno")
    base_dir = "dados"
    garantir_diretorio_dados()
    trimestres = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not trimestres:
        st.warning("Nenhum dado disponível.")
        st.stop()

    trimestre = st.selectbox("Selecione o trimestre", trimestres, key="trimestre_aluno")
    caminho = os.path.join(base_dir, trimestre)
    df_total = carregar_dados_trimestre(caminho)
    if df_total.empty:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    # Filtro por turma antes de selecionar o aluno
    turmas = sorted(df_total["turma"].dropna().unique())
    turma_selecionada = st.selectbox("Selecione a turma", turmas, key="turma_aluno")
    df_total = df_total[df_total["turma"] == turma_selecionada]

    nomes = sorted(df_total["nome"].unique())
    aluno = st.selectbox("Selecione o aluno", nomes, key="aluno_especifico")
    df_aluno = df_total[df_total["nome"] == aluno]

    # Filtro adicional por disciplina
    disciplinas = sorted(df_aluno["disciplina"].unique())
    disciplinas_selecionadas = st.multiselect("Filtrar disciplinas", disciplinas, default=disciplinas, key="disciplinas_aluno")
    df_aluno = df_aluno[df_aluno["disciplina"].isin(disciplinas_selecionadas)]

    st.markdown("### 📋 Detalhamento das Disciplinas")

    # Cria a coluna 'situação' com base na nota
    df_aluno["situacao"] = df_aluno["nota"].apply(
        lambda n: "Aprovado" if n >= 7 else "Reforço" if n >= 5 else "Reprovado"
    )

    # Define colunas finais e ordena
    df_visivel = df_aluno[["disciplina", "nota", "faltas", "situacao"]].sort_values(by="nota", ascending=False).reset_index(drop=True)

    st.dataframe(df_visivel)


    st.markdown("### 📊 Notas por Disciplina")
    st.plotly_chart(px.bar(df_aluno, x="disciplina", y="nota", color="disciplina"))

    media = df_aluno["nota"].mean()
    faltas = df_aluno["faltas"].sum()

    # Indicadores adicionais
    disciplina_melhor = df_aluno.loc[df_aluno["nota"].idxmax()]["disciplina"]
    disciplina_pior = df_aluno.loc[df_aluno["nota"].idxmin()]["disciplina"]
    disciplina_mais_faltas = df_aluno.loc[df_aluno["faltas"].idxmax()]["disciplina"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Média Geral", f"{media:.2f}")
    col2.metric("Total de Faltas", int(faltas))
    col3.metric("Maior Nota", f"{df_aluno['nota'].max():.1f}")

    st.markdown("### 🔍 Observações Detalhadas")
    st.write(f"📌 Melhor desempenho em **{disciplina_melhor}**.")
    st.write(f"⚠️ Pior desempenho em **{disciplina_pior}**.")
    st.write(f"🚫 Mais faltas em **{disciplina_mais_faltas}**.")

    # Histórico do aluno por trimestre
    historico_aluno = []
    for tri in trimestres:
        caminho_tri = os.path.join(base_dir, tri)
        df_tri = carregar_dados_trimestre(caminho_tri)
        if df_tri.empty:
            continue
        df_tri_aluno = df_tri[df_tri["nome"] == aluno]
        media_tri = df_tri_aluno["nota"].mean()
        faltas_tri = df_tri_aluno["faltas"].sum()
        historico_aluno.append({
            "Trimestre": tri,
            "Média": media_tri,
            "Faltas": faltas_tri
        })

    if historico_aluno:
        df_hist = pd.DataFrame(historico_aluno).sort_values("Trimestre")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📈 Evolução da Média por Trimestre")
            st.plotly_chart(px.line(df_hist, x="Trimestre", y="Média", markers=True))
        with col2:
            st.markdown("### 📉 Evolução das Faltas por Trimestre")
            st.plotly_chart(px.line(df_hist, x="Trimestre", y="Faltas", markers=True))

    recomendacao = (
        st.session_state.recomendacoes["Aprovado"] if media >= 7 else
        st.session_state.recomendacoes["Reforço"] if media >= 5 else
        st.session_state.recomendacoes["Reprovado"]
    )
    st.info(f"📌 Recomendação: {recomendacao}")

    if st.button("📤 Exportar Relatório do Aluno"):
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()

        # Cabeçalho com logo
        if config.get("logo_escola_path") and os.path.exists(config["logo_escola_path"]):
            pdf.image(config["logo_escola_path"], x=10, y=8, w=30)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"{config['nome_escola']}", ln=True, align="C")
        if config.get("endereco") or config.get("telefone"):
            pdf.set_font("Arial", size=10)
            info = f"{config.get('endereco', '')} | {config.get('telefone', '')}"
            pdf.cell(0, 10, info.strip(" | "), ln=True, align="C")

        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Relatório do Aluno - {aluno}", ln=True, align="C")
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"Média Geral: {media:.2f}", ln=True)
        pdf.cell(0, 10, f"Faltas Totais: {int(faltas)}", ln=True)
        pdf.multi_cell(0, 10, f"Recomendação: {recomendacao}")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Notas por Disciplina:", ln=True)
        pdf.set_font("Arial", size=12)
        for _, row in df_aluno.iterrows():
            pdf.cell(0, 10, f"{row['disciplina']}: {row['nota']} | Faltas: {row['faltas']}", ln=True)

        nome_pdf = os.path.join("exportacoes/relatorios_alunos", f"relatorio_{aluno.replace(' ', '_')}.pdf")
        os.makedirs(os.path.dirname(nome_pdf), exist_ok=True)
        pdf.output(nome_pdf)
        with open(nome_pdf, "rb") as f:
            st.download_button("📎 Baixar PDF", f, file_name=nome_pdf, mime="application/pdf")

elif opcao == "Análise por Turma":
    st.title("📊 Análise por Turma")

    base_dir = "dados"
    garantir_diretorio_dados()
    trimestres = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not trimestres:
        st.warning("Nenhum dado disponível.")
        st.stop()

    trimestre = st.selectbox("Selecione o trimestre", trimestres)
    caminho = os.path.join(base_dir, trimestre)
    df = carregar_dados_trimestre(caminho)
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    turmas = sorted(df["turma"].dropna().unique())
    turma = st.selectbox("Selecione a turma", turmas)
    dff = df[df["turma"] == turma]

    # Filtro de disciplinas
    disciplinas = sorted(dff["disciplina"].unique())
    disciplina = st.multiselect("Filtrar disciplinas", disciplinas, default=disciplinas)

    # Aplicar filtro
    dff = dff[dff["disciplina"].isin(disciplina)]

    # Gera a coluna "Situação"
    dff["situacao"] = dff["nota"].apply(
        lambda n: "Aprovado" if n >= 7 else "Reforço" if n >= 5 else "Reprovado"
    )

    # Tabela organizada
    df_visivel = dff[["nome", "disciplina", "nota", "faltas", "situacao"]].sort_values(by="nome").reset_index(drop=True)
    df_visivel = df_visivel.rename(columns={
        "nome": "Aluno",
        "disciplina": "Disciplina",
        "nota": "Nota",
        "faltas": "Faltas",
        "situacao": "Situação"
    })

    st.markdown("### 📋 Detalhamento por Aluno e Disciplina")
    st.dataframe(df_visivel)

    # Gráfico de barras (múltiplas disciplinas)
    st.markdown("### 📊 Desempenho por Disciplina")
    if len(disciplina) > 1:
        fig = px.bar(
            dff.groupby("disciplina")["nota"].mean().reset_index(),
            x="disciplina",
            y="nota",
            color="disciplina",
            title="Média por Disciplina"
        )
        st.plotly_chart(fig)
    elif len(disciplina) == 1:
        media_disciplina = dff["nota"].mean()
        st.info(f"Média geral da disciplina **{disciplina[0]}**: {media_disciplina:.2f}")

    # Comparativo com trimestre anterior (linha)
    if len(disciplina) == 1:
        disciplina_selecionada = disciplina[0]
        st.markdown(f"### 📈 Evolução da Média da Turma - {disciplina_selecionada}")

        try:
            idx_atual = trimestres.index(trimestre)
            if idx_atual > 0:
                trimestre_anterior = trimestres[idx_atual - 1]
                caminho_anterior = os.path.join("dados", trimestre_anterior)
                df_antigo = carregar_dados_trimestre(caminho_anterior)
                df_antigo = df_antigo[
                    (df_antigo["turma"] == turma) &
                    (df_antigo["disciplina"] == disciplina_selecionada)
                ]
                df_novo = dff[dff["disciplina"] == disciplina_selecionada]

                media_antiga = df_antigo["nota"].mean()
                media_atual = df_novo["nota"].mean()

                df_comp = pd.DataFrame({
                    "Trimestre": [trimestre_anterior, trimestre],
                    "Média da Turma": [media_antiga, media_atual]
                })

                fig_comp = px.line(
                    df_comp,
                    x="Trimestre",
                    y="Média da Turma",
                    markers=True,
                    title=f"Evolução da Média - {disciplina_selecionada}"
                )
                st.plotly_chart(fig_comp)
            else:
                st.info("Nenhum trimestre anterior disponível para comparação.")
        except Exception as e:
            st.warning(f"Erro ao gerar comparativo: {e}")


    if st.button("📤 Exportar Relatório da Turma"):
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        if config.get("logo_escola_path") and os.path.exists(config["logo_escola_path"]):
            pdf.image(config["logo_escola_path"], x=10, y=8, w=30)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"{config['nome_escola']}", ln=True, align="C")
        if config.get("endereco") or config.get("telefone"):
            pdf.set_font("Arial", size=10)
            info = f"{config.get('endereco', '')} | {config.get('telefone', '')}"
            pdf.cell(0, 10, info.strip(" | "), ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Relatório da Turma {turma} - {trimestre}", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Média e Faltas por Aluno:", ln=True)
        pdf.set_font("Arial", size=12)
        df_alunos = dff.groupby("nome")[["nota", "faltas"]].agg({"nota": "mean", "faltas": "sum"}).reset_index()
        for _, row in df_alunos.iterrows():
            pdf.cell(0, 10, f"{row['nome']}: Média {row['nota']:.2f}, Faltas {int(row['faltas'])}", ln=True)
        nome_pdf = os.path.join("exportacoes/relatorios_alunos", f"relatorio_turma_{turma.replace(' ', '_')}_{trimestre}.pdf")
        os.makedirs(os.path.dirname(nome_pdf), exist_ok=True)
        pdf.output(nome_pdf)
        with open(nome_pdf, "rb") as f:
            st.download_button("📎 Baixar PDF da Turma", f, file_name=nome_pdf, mime="application/pdf")


elif opcao == "Ranking da Turma":
    st.title("🏆 Ranking da Turma")

    from fpdf import FPDF
    import tempfile

    base_dir = "dados"
    garantir_diretorio_dados()
    trimestres = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])

    if not trimestres:
        st.warning("Nenhum dado disponível.")
        st.stop()

    trimestre = st.selectbox("Selecione o trimestre", trimestres)
    caminho = os.path.join(base_dir, trimestre)
    df = carregar_dados_trimestre(caminho)

    if df.empty:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    turmas = sorted(df["turma"].dropna().unique())
    turma = st.selectbox("Selecione a turma", turmas)

    df = df[df["turma"] == turma]

    # Agrupa por aluno e calcula média
    ranking = df.groupby("nome")["nota"].mean().reset_index()
    ranking = ranking.rename(columns={"nome": "Aluno", "nota": "Média"})
    ranking = ranking.sort_values(by="Média", ascending=False).reset_index(drop=True)

    # Adiciona posição e medalhas em texto (compatível com PDF)
    ranking.insert(0, "Posição", ranking.index + 1)
    ranking["Medalha"] = ""

    if not ranking.empty:
        if len(ranking) >= 1:
            ranking.at[0, "Medalha"] = "Ouro"
        if len(ranking) >= 2:
            ranking.at[1, "Medalha"] = "Prata"
        if len(ranking) >= 3:
            ranking.at[2, "Medalha"] = "Bronze"

    st.markdown(f"### 📋 Ranking - Turma {turma} ({trimestre})")
    st.dataframe(ranking.style.format({"Média": "{:.2f}"}), use_container_width=True)

    # Botão para gerar PDF
    if st.button("📎 Baixar Ranking em PDF"):
        class PDF(FPDF):
            def header(self):
                self.set_font("Arial", "B", 14)
                self.cell(0, 10, f"Ranking da Turma {turma} - {trimestre}", ln=True, align="C")
                self.ln(10)

        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Cabeçalho da tabela
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(20, 10, "Pos.", 1, 0, "C", True)
        pdf.cell(80, 10, "Aluno", 1, 0, "C", True)
        pdf.cell(30, 10, "Média", 1, 0, "C", True)
        pdf.cell(30, 10, "Medalha", 1, 1, "C", True)

        # Linhas da tabela
        for _, row in ranking.iterrows():
            pdf.cell(20, 10, str(row["Posição"]), 1, 0, "C")
            pdf.cell(80, 10, str(row["Aluno"]), 1, 0)
            pdf.cell(30, 10, f"{row['Média']:.2f}", 1, 0, "C")
            pdf.cell(30, 10, row["Medalha"], 1, 1, "C")

        # Gera e disponibiliza o PDF para download
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            pdf.output(tmpfile.name)
            with open(tmpfile.name, "rb") as f:
                st.download_button(
                    label="📥 Clique aqui para baixar o PDF",
                    data=f,
                    file_name=f"Ranking_{turma}_{trimestre}.pdf",
                    mime="application/pdf"
                )
