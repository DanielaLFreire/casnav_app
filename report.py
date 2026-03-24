import streamlit as st
from datetime import datetime, date, timedelta
from functions_aux import (load_projeto, salvar_relatorio, get_todos_formularios)
from export_utils import render_botoes_download


# ═══════════════════════════════════════════════════
#  GERAR RELATÓRIO INDIVIDUAL
# ═══════════════════════════════════════════════════
def gerar_relatorio(form: dict, proj: dict) -> dict:
    nome    = form.get("bolsista_nome", "Bolsista")
    periodo = form.get("periodo_referencia", "—")
    mes     = form.get("mes_execucao", "—")
    termo   = form.get("numero_termo", "—")
    ativs   = ", ".join(form.get("atividade_principal", []))

    bloco1 = f"""## BLOCO 1 — RELATÓRIO TÉCNICO

**Projeto:** {proj['nome_projeto']} — {proj['titulo']}
**Coordenador:** {proj['coordenador']}
**Bolsista:** {nome} | **Termo:** {termo}
**Período:** {periodo} | **{mes}**
**Atividade(s) principal(is):** {ativs}

### 1. Enquadramento
{form.get('conexao_cronograma', '—')}

Status: {', '.join(form.get('status_atividade', ['—']))}
{form.get('explicacao_status', '')}

### 2. Atividades
"""
    # Gerar seção para cada atividade
    atividades = form.get("atividades", [])
    concluidas = [a for a in atividades if a.get("situacao") == "Concluída"]
    em_andamento = [a for a in atividades if a.get("situacao") == "Em andamento"]
    nao_iniciadas = [a for a in atividades if a.get("situacao") == "Não Iniciada"]
    impedidas = [a for a in atividades if a.get("situacao") == "Impedida"]

    if concluidas:
        bloco1 += "\n#### Atividades Concluídas\n"
        for a in concluidas:
            bloco1 += f"""
**{a.get('nome', a.get('codigo','—'))}** — Concluída
- Objetivo: {a.get('objetivo','—')}
- Descrição: {a.get('descricao','—')}
- Entregas: {a.get('entregas','—')}
- Execução acumulada: {a.get('pct_acum',100)}%
- Marco: {a.get('marco','—')}
{a.get('obs','')}
"""
    else:
        bloco1 += "\nNenhuma atividade concluída integralmente no período.\n"

    if em_andamento:
        bloco1 += "\n#### Atividades em Andamento\n"
        for a in em_andamento:
            bloco1 += f"""
**{a.get('nome', a.get('codigo','—'))}** — Em andamento
- Estágio: {', '.join(a.get('estagio', ['—']))}
- Realizado: {a.get('realizado','—')}
- Falta: {a.get('falta','—')}
- % período: {a.get('pct_periodo',0)}% | % acumulado: {a.get('pct_acum',0)}%
- Dificuldades: {a.get('dificuldades','—')}
- Previsão: {a.get('previsao','—')}
- Marco: {a.get('marco','—')}
"""

    if impedidas:
        bloco1 += "\n#### Atividades Impedidas\n"
        for a in impedidas:
            bloco1 += f"""
**{a.get('nome', a.get('codigo','—'))}** — Impedida
- Motivo: {a.get('motivo_impedimento','—')}
- Previsão de desbloqueio: {a.get('previsao_desbloqueio','—')}
"""

    if nao_iniciadas:
        bloco1 += "\n#### Atividades Não Iniciadas\n"
        for a in nao_iniciadas:
            bloco1 += f"- {a.get('nome', a.get('codigo','—'))}\n"

    bloco1 += f"""
### 3. Estimativa de Conclusão
Riscos: {form.get('prox_risco_explicacao', '—')}
Mitigação: {form.get('prox_mitigacao', '—')}

### 4. Próximas Atividades
{form.get('prox_atividades', '—')}
Entregáveis: {form.get('prox_entregaveis', '—')}

### 5. Considerações Finais
{form.get('consideracoes_finais', '—')}
"""

    bloco2 = f"""## BLOCO 2 — SÍNTESE GERENCIAL PARA GANTT

| Campo | Valor |
|-------|-------|
| Atividade | {form.get('gantt_atividade', '—')} |
| Código | {form.get('gantt_codigo', '—')} |
| Status | {form.get('gantt_status', '—')} |
| Início planejado | {form.get('gantt_inicio_plan', '—')} |
| Início real | {form.get('gantt_inicio_real', '—')} |
| Término planejado | {form.get('gantt_termino_plan', '—')} |
| Término atualizado | {form.get('gantt_termino_atual', '—')} |
| Tipo desvio | {form.get('gantt_desvio_tipo', '—')} |
| Impacto | {form.get('gantt_impacto', '—')} |
| Dependências | {form.get('gantt_dependencias', '—')} |
| Marco | {form.get('gantt_marco', '—')} |
| Comentário | {form.get('gantt_comentario', '—')} |
"""

    bloco3 = f"""## BLOCO 3 — SÍNTESE FÍSICA PARA CURVA S

| Indicador | Valor |
|-----------|-------|
| Entregas concluídas | {form.get('curva_concluidas', 'Nenhuma')} |
| Entregas parciais | {form.get('curva_parciais', '—')} |
| % avanço período | {form.get('curva_pct_periodo', 0)}% |
| % avanço acumulado | {form.get('curva_pct_acum', 0)}% |

**Justificativa:** {form.get('curva_justificativa', '—')}
**Contribuíram:** {form.get('curva_contribuiram', '—')}
**Riscos:** {form.get('curva_riscos', '—')}
**Aceleradores:** {form.get('curva_aceleradores', '—')}
"""

    bloco4 = f"""## BLOCO 4 — RESUMO EXECUTIVO

{form.get('resumo_executivo', 'Não preenchido.')}
"""

    return {
        "bolsista_id": form.get("bolsista_id", ""), "bolsista_nome": nome,
        "numero_termo": termo, "periodo": periodo,
        "mes_referencia_num": form.get("mes_execucao_num", 0),
        "bloco1_tecnico": bloco1, "bloco2_gantt": bloco2,
        "bloco3_curva_s": bloco3, "bloco4_resumo": bloco4,
        "tipo": "individual", "gerado_em": datetime.now().isoformat(),
    }


def page_relatorio():
    proj = load_projeto()
    st.markdown("""<div class="main-header">
        <h1>📄 Gerar Relatório Individual</h1>
        <p>Selecione um formulário preenchido para gerar o relatório nos 4 blocos.</p>
    </div>""", unsafe_allow_html=True)

    formularios = get_todos_formularios()
    if not formularios:
        st.warning("Nenhum formulário salvo. Preencha um formulário primeiro.")
        return

    opcoes = [f"{f.get('bolsista_nome','?')} — {f.get('mes_execucao','?')} ({f.get('_salvamento','')})" for f in formularios]
    idx = st.selectbox("Selecione o formulário", range(len(opcoes)), format_func=lambda i: opcoes[i])
    form = formularios[idx]

    with st.expander("📋 Dados do formulário", expanded=False):
        st.json(form)

    if st.button("🚀 Gerar Relatório", type="primary", use_container_width=True):
        rel = gerar_relatorio(form, proj)
        st.session_state["rel_ind"] = rel

        # FIX: persistir relatório automaticamente (local + GitHub)
        fn_rel = salvar_relatorio(rel)
        st.success(f"✅ Relatório gerado e salvo: **{fn_rel}**")

    if "rel_ind" in st.session_state:
        rel = st.session_state["rel_ind"]
        t1, t2, t3, t4 = st.tabs(["📝 Técnico", "📊 Gantt", "📉 Curva S", "📋 Resumo"])
        with t1: st.markdown(rel["bloco1_tecnico"])
        with t2: st.markdown(rel["bloco2_gantt"])
        with t3: st.markdown(rel["bloco3_curva_s"])
        with t4: st.markdown(rel["bloco4_resumo"])

        # Botão manual de salvar (fallback, agora redundante mas inofensivo)
        if st.button("💾 Salvar Relatório"):
            fn = salvar_relatorio(rel)
            st.success(f"✅ Salvo: {fn}")

        # Download em 3 formatos
        st.markdown("#### 📥 Baixar Relatório")
        full = "\n---\n".join([rel["bloco1_tecnico"], rel["bloco2_gantt"],
                                rel["bloco3_curva_s"], rel["bloco4_resumo"]])
        fname = f"relatorio_{rel.get('bolsista_id', 'x')}_mes{rel.get('mes_referencia_num', 0)}"
        titulo = f"Relatório — {rel.get('bolsista_nome', '')} — Mês {rel.get('mes_referencia_num', '')}"
        render_botoes_download(full, fname, titulo)
