
import streamlit as st

from functions_aux import (load_bolsistas,load_projeto, save_bolsistas)


# ═══════════════════════════════════════════════════
#  GESTÃO DE BOLSISTAS (com numero_termo por bolsista)
# ═══════════════════════════════════════════════════
def page_bolsistas():
    bdata = load_bolsistas()
    proj  = load_projeto()
    st.markdown("""<div class="main-header">
        <h2>👥 Gestão de Bolsistas</h2>
        <p>Cadastro, termo de bolsa e atividades designadas. </p>
    </div>""", unsafe_allow_html=True)

    for i, b in enumerate(bdata["bolsistas"]):
        icon = "🟢" if b.get("numero_termo") else "🟡"
        with st.expander(f"{icon} {b['nome']} — Termo: {b.get('numero_termo','não informado')}"):
            with st.form(f"edit_{i}"):
                c1, c2 = st.columns(2)
                with c1:
                    b["nome_completo"]     = st.text_input("Nome completo", value=b.get("nome_completo",""), key=f"bn{i}")
                    b["numero_termo"]      = st.text_input("Nº do Termo de Bolsa", value=b.get("numero_termo",""), key=f"bt{i}")
                    b["email"]             = st.text_input("E-mail", value=b.get("email",""), key=f"be{i}")

                with c2:
                    b["data_inicio_bolsa"] = st.text_input("Início da bolsa", value=b.get("data_inicio_bolsa",""), key=f"bd{i}")
                    b["prazo_meses"]       = st.number_input("Prazo (meses)", value=int(b.get("prazo_meses",0)), key=f"bp{i}")
                    b["formacao"] = st.text_input("Formação", value=b.get("formacao", ""), key=f"bf{i}")
                b["observacoes"] = st.text_area("Observações", value=b.get("observacoes",""), key=f"bo{i}")

                ativs_opcoes = [f"{a['codigo']} {a['nome']}" for a in proj["atividades"]]
                ativs_atuais = [a["codigo"] for a in b.get("atividades_designadas", [])]
                ativs_sel = st.multiselect("Atividades designadas", ativs_opcoes,
                    default=[o for o in ativs_opcoes if any(o.startswith(c) for c in ativs_atuais)], key=f"ba{i}")

                if st.form_submit_button("💾 Salvar"):
                    new_ativs = []
                    for sel in ativs_sel:
                        cod = sel.split(" ")[0]
                        # Buscar meses do projeto
                        for a in proj["atividades"]:
                            if a["codigo"] == cod:
                                new_ativs.append({"codigo": cod, "periodicidade": f"Mês {a['meses_inicio']} ao Mês {a['meses_fim']}",
                                                   "meses_inicio": a["meses_inicio"], "meses_fim": a["meses_fim"]})
                                break
                    b["atividades_designadas"] = new_ativs
                    bdata["bolsistas"][i] = b
                    save_bolsistas(bdata)
                    st.success(f"✅ {b['nome']} salvo!")

def main():
    st.markdown("""<div class="main-header">
        <h1>🚢 CASNAV DMarSup </h1>
        <p>Projeto Sistemas Marítimos Não Tripulados | Visão Computacional</p>
    </div>""", unsafe_allow_html=True)

    page_bolsistas()

# EXECUÇÃO
# =============================================================================
if __name__ == "__main__":
    main()