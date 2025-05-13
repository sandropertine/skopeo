
import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re
import os

def extrair_dados_pdf(pdf_file):
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        texto_pag_2 = doc[1].get_text()
        linhas = texto_pag_2.split("\n")

    alunos = []
    for i in range(8, len(linhas)):
        nome_candidato = linhas[i].strip()
        if re.match(r"^[A-Z][A-Z\sÇÁÉÍÓÚÃÕÑ]+$", nome_candidato) and len(nome_candidato.split()) >= 2:
            bloco = linhas[i-8:i]
            try:
                faltas = int(bloco[4])
                pr1 = float(bloco[5].replace(",", "."))
                rp1 = float(bloco[6].replace(",", "."))
                po1_mt = bloco[7].split()
                if len(po1_mt) == 2:
                    po1 = float(po1_mt[0].replace(",", "."))
                    mt = float(po1_mt[1].replace(",", "."))
                else:
                    po1 = 0.0
                    mt = float(po1_mt[0].replace(",", ".")) if po1_mt else 0.0

                alunos.append({
                    "nome": nome_candidato.title(),
                    "faltas": faltas,
                    "pr1": pr1,
                    "rp1": rp1,
                    "po1": po1,
                    "nota": mt
                })
            except:
                continue

    df = pd.DataFrame(alunos)
    df["situação"] = df["nota"].apply(lambda n: "Reprovado" if n < 6 else "Reforço" if n < 7 else "Aprovado")
    return df

def executar():
    st.subheader("📄 Importar Diário em PDF")
    arquivo = st.file_uploader("Envie o PDF do professor", type="pdf")
    if arquivo:
        df = extrair_dados_pdf(arquivo)
        if not df.empty:
            st.success("PDF interpretado com sucesso!")

            trimestre = st.selectbox("Trimestre:", ["1º Trimestre", "2º Trimestre", "3º Trimestre"])
            disciplina = st.text_input("Disciplina:")
            professor = st.text_input("Professor:")
            turma = st.text_input("Turma:")

            # Proteção contra erro de digitação: "Matemática Lucas" no campo errado
            partes = disciplina.strip().split()
            if len(partes) > 1 and not professor:
                st.warning("Detectado nome duplo na disciplina. Vamos separar automaticamente.")
                disciplina = " ".join(partes[:-1])
                professor = partes[-1]

            if professor and disciplina and turma:
                df["disciplina"] = disciplina.strip()
                df["professor"] = professor.strip()
                df["turma"] = turma.strip()

                df_visual = df.rename(columns={
                    "nome": "Nome do Aluno",
                    "disciplina": "Disciplina",
                    "professor": "Professor",
                    "turma": "Turma",
                    "nota": "Nota",
                    "faltas": "Faltas",
                    "pr1": "PR1",
                    "rp1": "RP1",
                    "po1": "PO1",
                    "situação": "Situação"
                })

                df_visual = df_visual.sort_values(by=["Nome do Aluno", "Disciplina"])
                st.dataframe(df_visual.style.format({"Nota": "{:.2f}"}), use_container_width=True)

                pasta_destino = f"dados/{trimestre}"
                os.makedirs(pasta_destino, exist_ok=True)
                nome_arquivo = f"{disciplina.lower().replace(' ', '_')}_{professor.lower().replace(' ', '_')}.csv"
                caminho = os.path.join(pasta_destino, nome_arquivo)
                df.to_csv(caminho, index=False)
                st.success(f"Dados salvos em: {caminho}")
            else:
                st.warning("Informe o nome do professor, da disciplina e da turma.")
