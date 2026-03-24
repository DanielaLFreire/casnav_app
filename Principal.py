"""
CASNAV DMarSup — Sistema de Acompanhamento de Atividades dos Bolsistas
Projeto Sistemas Marítimos Não Tripulados
Mês 1 do Projeto = Agosto/2025
"""

import streamlit as st
from datetime import  timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from functions_aux import (load_bolsistas,load_projeto,
                           get_todos_formularios, get_todos_relatorios)

from config import mes_atual, hoje, mes_para_data, mes_label_curto, render_sidebar

# ═══════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════
def page_dashboard():
    proj = load_projeto()
    bdata = load_bolsistas()
    bolsistas = bdata["bolsistas"]
    formularios = get_todos_formularios()
    relatorios  = get_todos_relatorios()

    st.markdown("""<div class="main-header">
        <h2> Painel de Acompanhamento</h2>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mês do Projeto", f"{mes_atual}/36")
    c2.metric("Bolsistas", len(bolsistas))
    c3.metric("Formulários", len(formularios))
    c4.metric("Relatórios", len(relatorios))

    st.markdown("---")


def page_historico():
    bdata = load_bolsistas()
    proj = load_projeto()

    st.markdown("""<div class="main-header">
        <h2>📁 Histórico — Visão do Gerente</h2>
        <p>Timeline de todos os formulários e relatórios. Compare períodos, acompanhe evolução e identifique pendências.</p>
    </div>""", unsafe_allow_html=True)

    formularios = get_todos_formularios()
    relatorios = get_todos_relatorios()

    # ── ABA 1: Painel de Status por Período ──
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Status por Período", "🕐 Timeline", "📈 Evolução", "📄 Detalhes"])

    with tab1:
        st.subheader("Quem preencheu em cada mês?")
        if not formularios:
            st.info("Nenhum formulário salvo ainda.")
        else:
            # Montar matriz mês × bolsista
            todos_nomes = sorted(b["nome"] for b in bdata["bolsistas"])
            meses_com_dados = sorted(
                set(f.get("mes_execucao_num", 0) for f in formularios if f.get("mes_execucao_num")))

            matrix = {}
            for m in meses_com_dados:
                matrix[m] = {}
                forms_m = [f for f in formularios if f.get("mes_execucao_num") == m]
                nomes_m = set(f.get("bolsista_nome", "?") for f in forms_m)
                for n in todos_nomes:
                    matrix[m][n] = "✅" if n in nomes_m else "❌"

            if matrix:
                rows = []
                for m in meses_com_dados:
                    row = {"Mês": f"Mês {m} ({mes_label_curto(m)})"}
                    row.update(matrix[m])
                    rows.append(row)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Todos os formulários (ordem cronológica)")
        if not formularios:
            st.info("Vazio.")
        else:
            for f in reversed(formularios):
                nome = f.get("bolsista_nome", "?")
                mes = f.get("mes_execucao", f.get("mes_execucao_num", "?"))
                ts = f.get("_salvamento", "")
                pct = f.get("curva_pct_acum", "—")
                st.markdown(f'<div class="hist-card"><strong>{nome}</strong> — {mes} | '
                            f'Curva S acum.: <strong>{pct}%</strong> | Salvo: {ts}</div>',
                            unsafe_allow_html=True)
                with st.expander(f"Ver formulário completo ({ts})", expanded=False):
                    st.json(f)

    with tab3:
        st.subheader("Evolução do Avanço Físico por Bolsista")
        if not formularios:
            st.info("Sem dados.")
        else:
            rows = []
            for f in formularios:
                mn = f.get("mes_execucao_num", 0)
                pa = f.get("curva_pct_acum", 0)
                bn = f.get("bolsista_nome", "?")
                if mn and pa:
                    rows.append({"Mês": mn, "Bolsista": bn, "% Acumulado": pa})
            if rows:
                df = pd.DataFrame(rows)
                fig = px.line(df, x="Mês", y="% Acumulado", color="Bolsista", markers=True,
                              title="Evolução do avanço físico acumulado por bolsista")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado de curva S encontrado.")

    with tab4:
        st.subheader("Relatórios Gerados")
        if not relatorios:
            st.info("Nenhum relatório gerado.")
        else:
            for r in reversed(relatorios):
                with st.expander(f"{r.get('bolsista_nome', r.get('tipo', '?'))} — {r.get('periodo', '?')}"):
                    if "bloco1_tecnico" in r:
                        st.markdown(r["bloco1_tecnico"][:800] + "...")
                    st.json(r)


# ═══════════════════════════════════════════════════
#  GANTT
# ═══════════════════════════════════════════════════
def page_gantt():
    proj = load_projeto()
    st.markdown("""<div class="main-header">
        <h2>📈 Gantt — Cronograma do Projeto</h2>
        <p>Planejado vs. realizado conforme dados reportados.</p>
    </div>""", unsafe_allow_html=True)

    rows = []
    for a in proj["atividades"]:
        d_i = mes_para_data(a["meses_inicio"])
        d_f = mes_para_data(a["meses_fim"]) + relativedelta(months=1) - timedelta(days=1)
        st_txt = "Em andamento" if a["meses_inicio"] <= mes_atual <= a["meses_fim"] \
                 else ("Não iniciada" if mes_atual < a["meses_inicio"] else "Janela encerrada")
        rows.append({"Atividade": f"{a['codigo']} {a['nome']}", "Início": d_i, "Fim": d_f, "Tipo": "Planejado", "Status": st_txt})

    df = pd.DataFrame(rows)
    fig = px.timeline(df, x_start="Início", x_end="Fim", y="Atividade", color="Status",
        color_discrete_map={"Não iniciada":"#bdbdbd","Em andamento":"#1565c0","Janela encerrada":"#66bb6a"})
    fig.update_yaxes(autorange="reversed")
    fig.add_vline(x=str(hoje), line_dash="dash", line_color="red")
    fig.add_annotation(x=str(hoje), y=1, yref="paper", text="Hoje", showarrow=False,
        font=dict(color="red", size=11), yshift=10)
    fig.update_layout(height=450, margin=dict(l=20,r=20,t=30,b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Tabela
    tbl = []
    for a in proj["atividades"]:
        tbl.append({"Código": a["codigo"], "Nome": a["nome"],
            "Meses": f"{a['meses_inicio']}–{a['meses_fim']}",
            "Início": mes_label_curto(a["meses_inicio"]),
            "Fim": mes_label_curto(a["meses_fim"]),
            "Entrega": a["entregas"]})
    st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
#  CURVA S
# ═══════════════════════════════════════════════════
def page_curva_s():
    proj = load_projeto()
    st.markdown("""<div class="main-header">
        <h2>📉 Curva S — Avanço Físico</h2>
        <p>Avanço real baseado em entregas verificáveis, não apenas tempo.</p>
    </div>""", unsafe_allow_html=True)

    dur = proj["duracao_meses"]
    meses_plan = list(range(1, dur+1))
    pct_plan = [round((3*(m/dur)**2 - 2*(m/dur)**3)*100, 1) for m in meses_plan]

    formularios = get_todos_formularios()
    dados_reais = {}
    for f in formularios:
        mn = f.get("mes_execucao_num", 0)
        pa = f.get("curva_pct_acum", 0)
        bn = f.get("bolsista_nome", "?")
        if mn and pa:
            dados_reais.setdefault(mn, []).append({"bolsista": bn, "pct": pa})

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=meses_plan, y=pct_plan, mode="lines", name="Planejado (teórico)",
        line=dict(color="#90caf9", width=2, dash="dash"), fill="tozeroy", fillcolor="rgba(144,202,249,0.1)"))
    fig.add_vline(x=mes_atual, line_dash="dot", line_color="red")
    fig.add_annotation(x=mes_atual, y=1, yref="paper", text=f"Mês {mes_atual}", showarrow=False,
        font=dict(color="red", size=11), yshift=10)

    if dados_reais:
        ms = sorted(dados_reais.keys())
        ps = [sum(d["pct"] for d in dados_reais[m]) / len(dados_reais[m]) for m in ms]
        fig.add_trace(go.Scatter(x=ms, y=ps, mode="lines+markers", name="Real (média)",
            line=dict(color="#1565c0", width=3), marker=dict(size=10)))

    fig.update_layout(xaxis_title="Mês do Projeto", yaxis_title="% Acumulado", yaxis=dict(range=[0,105]),
        height=420, margin=dict(l=20,r=20,t=30,b=20))
    st.plotly_chart(fig, use_container_width=True)

    if dados_reais:
        st.subheader("Dados por Bolsista")
        tbl = []
        for mn in sorted(dados_reais):
            for d in dados_reais[mn]:
                tbl.append({"Mês": mn, "Ref": mes_label_curto(mn), "Bolsista": d["bolsista"], "% Acum.": d["pct"]})
        st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True)



def main():
    st.markdown("""<div class="main-header">
        <h1>🚢 CASNAV DMarSup </h1>
        <p>Projeto Sistemas Marítimos Não Tripulados | Visão Computacional</p>
    </div>""", unsafe_allow_html=True)

    render_sidebar()
    # =============================================================================
    # TABS PRINCIPAIS
    # =============================================================================

    subtab1, subtab2, subtab3 = st.tabs([
        "📊 Visão Geral",
        "📈 Gantt & Cronograma",
        "📉 Curva S",
    ])

    # =============================================================================
    # TAB 1: VISÃO GERAL
    # =============================================================================

    with subtab1:
        page_dashboard()
        page_historico()
    with subtab2:
        page_gantt()
    with subtab3:
        page_curva_s()


# EXECUÇÃO
# =============================================================================
if __name__ == "__main__":
    main()