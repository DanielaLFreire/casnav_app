import streamlit as st
from functions_aux import (load_bolsistas, load_projeto, get_todos_formularios)
from report import gerar_relatorio
from config import hoje, render_sidebar
from export_utils import render_botoes_download


# ═══════════════════════════════════════════════════
#  RELATÓRIO UNIFICADO
# ═══════════════════════════════════════════════════
def page_unificado():
    proj  = load_projeto()
    bdata = load_bolsistas()
    st.markdown("""<div class="main-header">
        <h2>📑 Relatório Unificado</h2>
        <p>Consolida relatórios de todos os bolsistas por período.</p>
    </div>""", unsafe_allow_html=True)

    formularios = get_todos_formularios()
    if not formularios:
        st.warning("Nenhum formulário salvo.")
        return

    meses = sorted(set(str(f.get("mes_execucao_num", "?")) for f in formularios))
    mes_sel = st.selectbox("Mês de referência", meses)
    forms_mes = [f for f in formularios if str(f.get("mes_execucao_num", "?")) == mes_sel]

    # Status de preenchimento
    nomes_ok  = set(f.get("bolsista_nome", "?") for f in forms_mes)
    nomes_all = set(b["nome"] for b in bdata["bolsistas"])
    faltam    = nomes_all - nomes_ok

    c1, c2 = st.columns(2)
    with c1:
        st.success(f'✅ Preenchidos ({len(nomes_ok)}): {", ".join(sorted(nomes_ok))}')
    with c2:
        if faltam:
            st.warning(f'⏳ Pendentes ({len(faltam)}): {", ".join(sorted(faltam))}')
        else:
            st.success("Todos preencheram!")

    if st.button("📊 Gerar Unificado", type="primary", use_container_width=True):
        partes = [f"# RELATÓRIO UNIFICADO — {proj['nome_projeto']}\n**Mês:** {mes_sel} | **Data:** {hoje.strftime('%d/%m/%Y')}\n---\n"]
        for i, f in enumerate(forms_mes, 1):
            rel = gerar_relatorio(f, proj)
            partes.append(f"\n## {i}. {rel['bolsista_nome']} (Termo {rel['numero_termo']})\n")
            partes.append(rel["bloco1_tecnico"])
            partes.append(rel["bloco2_gantt"])
            partes.append(rel["bloco3_curva_s"])
            partes.append("\n---\n")
        texto = "\n".join(partes)
        st.session_state["unificado"] = texto
        st.session_state["unificado_mes"] = mes_sel

    if "unificado" in st.session_state:
        st.markdown(st.session_state["unificado"])

        # Download em 3 formatos
        st.markdown("---")
        st.markdown("#### 📥 Baixar Relatório Unificado")
        mes = st.session_state.get("unificado_mes", "0")
        render_botoes_download(
            st.session_state["unificado"],
            f"unificado_mes{mes}",
            f"Relatório Unificado — {proj['nome_projeto']} — Mês {mes}"
        )


def main():
    st.markdown("""<div class="main-header">
        <h1>🚢 CASNAV DMarSup </h1>
        <p>Projeto Sistemas Marítimos Não Tripulados | Visão Computacional</p>
    </div>""", unsafe_allow_html=True)
    render_sidebar()
    page_unificado()


# EXECUÇÃO
# =============================================================================
if __name__ == "__main__":
    main()
