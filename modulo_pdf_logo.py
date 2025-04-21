from fpdf import FPDF
import streamlit as st

def gerar_relatorio_pdf(dados, nome_arquivo='relatorio.pdf'):
    pdf = FPDF()
    pdf.add_page()

    # Logo
    try:
        pdf.image('logo_skopeo.png', x=10, y=8, w=33)
    except:
        pass

    # Cabeçalho
    nome_escola = st.session_state.get("nome_escola", "Skopeo - Sistema Escolar Multidisciplinar")
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(80)
    pdf.cell(30, 10, nome_escola, ln=1, align='C')
    pdf.ln(10)

    # Tabela
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(60, 10, "Aluno", 1)
    pdf.cell(40, 10, "Média", 1)
    pdf.cell(40, 10, "Faltas", 1)
    pdf.cell(50, 10, "Situação", 1)
    pdf.ln()

    pdf.set_font("Arial", size=12)
    for linha in dados:
        nome, media, faltas = linha
        media_f = float(media)
        if media_f >= 7:
            situacao = "Aprovado"
        elif media_f >= 5:
            situacao = "Reforço"
        else:
            situacao = "Reprovado"
        pdf.cell(60, 10, nome, 1)
        pdf.cell(40, 10, media, 1)
        pdf.cell(40, 10, str(faltas), 1)
        pdf.cell(50, 10, situacao, 1)
        pdf.ln()

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Comentários por Situação:", ln=True)

    pdf.set_font("Arial", size=11)
    recomendacoes = st.session_state.get("recomendacoes", {})
    for status in ["Aprovado", "Reforço", "Reprovado"]:
        texto = recomendacoes.get(status, "")
        pdf.multi_cell(0, 10, f"{status}: {texto}")

    pdf.output(nome_arquivo)


