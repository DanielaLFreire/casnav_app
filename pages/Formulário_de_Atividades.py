"""
CASNAV DMarSup — Sistema de Acompanhamento de Atividades dos Bolsistas
Projeto Sistemas Marítimos Não Tripulados
Mês 1 do Projeto = Agosto/2025

Página: Formulário de Atividades
- Permite selecionar bolsista e mês (padrão = mês atual)
- Se existir formulário salvo para bolsista+mês → exibe relatório gerado
- Se não existir → exibe formulário LIMPO para preenchimento
  (pré-preenchido APENAS com dados do perfil do bolsista e do projeto)
"""

import streamlit as st
from config import (SITUACAO_OPTS, EST_OPTS, mes_atual, hoje,
                    periodo_referencia_auto, render_sidebar, mes_label, mes_label_curto)
from functions_aux import (load_bolsistas, load_projeto, salvar_formulario,
                           salvar_relatorio,
                           get_ultimo_formulario, calcular_atividades_do_periodo,
                           calcular_faixa_planejada, prefill_gantt_inicio_plan,
                           prefill_gantt_termino_plan, get_formularios_bolsista)
from report import gerar_relatorio
from export_utils import render_botoes_download


# ═══════════════════════════════════════════════════
#  AUXILIAR: buscar formulário salvo por bolsista + mês
# ═══════════════════════════════════════════════════
def get_formulario_por_mes(bolsista_id: str, mes_num: int):
    """Retorna o formulário salvo mais recente para um bolsista+mês, ou None."""
    forms = get_formularios_bolsista(bolsista_id)
    forms_mes = [f for f in forms if f.get("mes_execucao_num") == mes_num]
    return forms_mes[-1] if forms_mes else None


# ═══════════════════════════════════════════════════
#  VISUALIZAÇÃO DO RELATÓRIO SALVO
# ═══════════════════════════════════════════════════
def exibir_relatorio_salvo(form_salvo: dict, proj: dict, bolsista: dict, mes_ref: int):
    """Exibe o relatório gerado a partir de um formulário salvo."""
    rel = gerar_relatorio(form_salvo, proj)

    st.success(f"✅ Formulário já preenchido para **{bolsista['nome']}** — **{mes_label(mes_ref)}**")
    st.caption(f"Salvo em: {form_salvo.get('data_preenchimento', '—')}")

    t1, t2 = st.tabs(["📝 Relatório Técnico", "📋 Resumo Executivo"])
    with t1:
        st.markdown(rel["bloco1_tecnico"])
    with t2:
        st.markdown(rel["bloco4_resumo"])

    full = "\n---\n".join([rel["bloco1_tecnico"], rel["bloco4_resumo"]])
    fname = f"relatorio_{bolsista['id']}_mes{mes_ref}"
    titulo = f"Relatório — {bolsista['nome']} — {mes_label(mes_ref)}"
    render_botoes_download(full, fname, titulo)

    # Botão para editar
    if st.button("✏️ Editar formulário", key="btn_editar"):
        st.session_state["modo_edicao"] = True
        st.rerun()


# ═══════════════════════════════════════════════════
#  FORMULÁRIO DE PREENCHIMENTO (campos limpos)
# ═══════════════════════════════════════════════════
def exibir_formulario(bolsista: dict, proj: dict, mes_ref: int):
    """Exibe o formulário completo para preenchimento.
    Campos LIMPOS, exceto os derivados do perfil do bolsista ou do projeto."""

    # ── Dados auxiliares ──
    atividades = proj["atividades"]
    ativs_desig = bolsista.get("atividades_designadas", [])
    ativs_opcoes = [f"{a['codigo']} {a['nome']}" for a in atividades]

    # Buscar atividades padrão do período (do projeto, não do último form)
    ativs_do_periodo = calcular_atividades_do_periodo(bolsista, mes_ref, proj)
    ativs_default = [f"{a['codigo']} {a['nome']}" for a in ativs_do_periodo]

    # Buscar dados completos de cada atividade designada (do projeto)
    ativs_info = []
    for ad in ativs_desig:
        cod = ad["codigo"]
        info = {"codigo": cod, "nome": cod, "periodicidade": ad.get("periodicidade", ""),
                "meses_inicio": ad.get("meses_inicio", 0), "meses_fim": ad.get("meses_fim", 0)}
        for a in atividades:
            if a["codigo"] == cod:
                info["nome"] = f"{cod} {a['nome']}"
                info["descricao_projeto"] = a.get("descricao", "")
                info["entregas_projeto"] = a.get("entregas", "")
                break
        ativs_info.append(info)

    # Info de pré-preenchimento
    pre_info = []
    pre_info.append("**Nome, coordenador, termo, data** ← cadastro do bolsista")
    pre_info.append(f"**Mês {mes_ref}** = {mes_label_curto(mes_ref)}, período = {periodo_referencia_auto(mes_ref)}")
    if ativs_default:
        pre_info.append(f"**Atividades sugeridas:** {', '.join(ativs_default)}")
    pre_info.append("**Demais campos em branco** — preencha com os dados do período atual.")
    st.markdown('<div class="prefill-info">' + "<br>".join(pre_info) + '</div>', unsafe_allow_html=True)

    # ── Formulário ──
    with st.form("form_atividades", clear_on_submit=False):

        # ═══ SEÇÃO 1: IDENTIFICAÇÃO (pré-preenchido do perfil/projeto) ═══
        st.markdown("### 1. Identificação")
        f_nome        = st.text_input("Nome do bolsista", value=bolsista["nome"], disabled=True,
                                       help="Preenchido automaticamente a partir do cadastro.")
        f_termo       = st.text_input("Nº do Termo de Bolsa", value=bolsista.get("numero_termo", ""),
                                       help="Número do Termo de Concessão de Bolsa individual do bolsista.")
        f_periodo     = st.text_input("Período de referência",
                                       value=periodo_referencia_auto(mes_ref),
                                       help="Período coberto por este relatório (dd/mm/aaaa a dd/mm/aaaa).")
        f_data_preench = st.text_input("Data de preenchimento", value=hoje.strftime("%d/%m/%Y"),
                                        help="Data em que o formulário está sendo preenchido.")
        f_mes_exec    = st.text_input("Mês de execução no cronograma",
                                       value=f"Mês {mes_ref} do projeto ({mes_label(mes_ref)})",
                                       disabled=True,
                                       help="Mês no cronograma global do projeto. Mês 1 = Agosto/2025.")
        f_coord        = st.text_input("Coordenador", value=proj["coordenador"], disabled=True,
                                       help="Coordenador do projeto, preenchido automaticamente.")
        f_responsavel = st.text_input("Responsável pelo preenchimento", value=bolsista["nome"],
                                      help="Nome de quem está preenchendo.")

        st.markdown("---")

        # ═══ SEÇÃO 2: ENQUADRAMENTO (atividades e faixa do projeto; resto limpo) ═══
        st.markdown("### 2. Enquadramento no Cronograma")
        _ativ_default_safe = [v for v in ativs_default if v in ativs_opcoes]
        f_ativ_princ = st.multiselect("2.1 Atividade(s) principal(is) do período", ativs_opcoes,
                                       default=_ativ_default_safe,
                                       help="Selecione as atividades do cronograma em que trabalhou neste período.")
        f_ativ_sec   = st.text_area("2.2 Atividades secundárias", value="", height=80,
                                     help="Atividades de apoio realizadas no período.")
        f_faixa      = st.text_input("2.3 Faixa planejada no cronograma original",
                                      value=calcular_faixa_planejada(bolsista, mes_ref),
                                      help="Faixa de meses prevista no cronograma original.")
        f_conexao    = st.text_area("2.4 Conexão com o cronograma global (4-8 linhas)",
                                     value="", height=120,
                                     help="Explique como as atividades se conectam ao cronograma macro do projeto.")
        _status_opts = [
            "dentro da fase originalmente prevista", "adiantada em relação ao cronograma",
            "atrasada em relação ao cronograma", "executada parcialmente fora da faixa originalmente prevista"
        ]
        f_status     = st.multiselect("2.5 Status da atividade no período", _status_opts,
                                       default=[],
                                       help="Selecione um ou mais status que descrevam a situação das atividades.")
        f_expl_status = st.text_area("Explique:", value="", height=80)

        st.markdown("---")

        # ═══ SEÇÃO 3: RESUMO EXECUTIVO (limpo) ═══
        st.markdown("### 3. Resumo Executivo do Período")
        f_resumo = st.text_area("5 a 10 linhas", value="", height=150,
                                 help="Síntese das atividades, entregas e avanços do período.")

        st.markdown("---")

        # ═══ SEÇÃO 4: ATIVIDADES DESIGNADAS (dinâmicas por situação) ═══
        st.markdown("### 4. Atividades Designadas")
        ativs_form = []

        if not ativs_desig:
            st.warning("⚠️ Nenhuma atividade designada para este bolsista. Configure em 👥 Gestão de Bolsistas.")
        else:
            for idx, ai in enumerate(ativs_info):
                st.markdown(f"#### {ai['nome']}")
                st.caption(f"Periodicidade: meses {ai['meses_inicio']}–{ai['meses_fim']}")
                if ai.get("descricao_projeto"):
                    st.caption(f"Descrição no projeto: {ai['descricao_projeto']}")

                ss_key = f"sit_{bolsista['id']}_{idx}"
                situacao = st.session_state.get(ss_key, "Não Iniciada")

                ativ_data = {"codigo": ai["codigo"], "nome": ai["nome"], "situacao": situacao}

                if situacao == "Em andamento":
                    ativ_data["objetivo"] = st.text_area(
                        f"Objetivo ({ai['codigo']})", value="", height=80, key=f"obj_{idx}",
                        help="Objetivo desta etapa da atividade.")
                    ativ_data["descricao"] = st.text_area(
                        f"Descrição técnica ({ai['codigo']})", value="", height=120, key=f"desc_{idx}",
                        help="Descrição técnica detalhada do que está sendo realizado.")

                    est_opts_safe = EST_OPTS
                    ativ_data["estagio"] = st.multiselect(
                        f"Estágio atual ({ai['codigo']})", est_opts_safe, default=[], key=f"est_{idx}",
                        help="Selecione os estágios em que a atividade se encontra.")

                    ativ_data["realizado"] = st.text_area(
                        f"O que já foi realizado ({ai['codigo']})", value="", height=80, key=f"real_{idx}")
                    ativ_data["falta"] = st.text_area(
                        f"O que falta ({ai['codigo']})", value="", height=80, key=f"falta_{idx}")

                    c1, c2 = st.columns(2)
                    with c1:
                        ativ_data["pct_periodo"] = st.slider(
                            f"% no período ({ai['codigo']})", 0, 100, 0, key=f"pp_{idx}",
                            help="Percentual de avanço gerado apenas neste período de referência.")
                    with c2:
                        ativ_data["pct_acum"] = st.slider(
                            f"% acumulado ({ai['codigo']})", 0, 100, 0, key=f"pa_{idx}",
                            help="Percentual acumulado total de execução desta atividade desde seu início.")

                    ativ_data["dificuldades"] = st.text_area(
                        f"Dificuldades ({ai['codigo']})", value="", height=68, key=f"dif_{idx}",
                        help="Dificuldades técnicas, limitações ou riscos identificados nesta atividade.")
                    ativ_data["previsao"] = st.text_input(
                        f"Previsão de conclusão ({ai['codigo']})", value="", key=f"prev_{idx}",
                        help="Data ou mês previsto para conclusão desta atividade.")
                    ativ_data["marco"] = st.text_input(
                        f"Marco ({ai['codigo']})", value="", key=f"mar_{idx}",
                        help="Principal marco esperado para encerrar esta atividade.")

                elif situacao == "Concluída":
                    ativ_data["objetivo"] = st.text_area(
                        f"Objetivo ({ai['codigo']})", value="", height=80, key=f"obj_{idx}")
                    ativ_data["descricao"] = st.text_area(
                        f"Descrição técnica ({ai['codigo']})", value="", height=120, key=f"desc_{idx}")
                    ativ_data["entregas"] = st.text_area(
                        f"Entregas concretas ({ai['codigo']})", value="", height=80, key=f"entr_{idx}")
                    ativ_data["pct_acum"] = st.slider(
                        f"% acumulado ({ai['codigo']})", 0, 100, 100, key=f"pa_{idx}")
                    ativ_data["marco"] = st.text_input(
                        f"Marco ({ai['codigo']})", value="", key=f"mar_{idx}")
                    ativ_data["obs"] = st.text_area(
                        f"Observação ({ai['codigo']})", value="", height=68, key=f"obs_{idx}")

                elif situacao == "Impedida":
                    ativ_data["motivo_impedimento"] = st.text_area(
                        f"Motivo ({ai['codigo']})", value="", height=80, key=f"imp_{idx}",
                        help="Descreva o motivo do impedimento.")
                    ativ_data["previsao_desbloqueio"] = st.text_input(
                        f"Previsão de desbloqueio ({ai['codigo']})", value="", key=f"desb_{idx}",
                        help="Quando se espera que o impedimento seja resolvido.")

                # Não Iniciada: nenhum campo extra

                ativs_form.append(ativ_data)
                st.markdown("---")

        # ═══ SEÇÃO 5: PRÓXIMOS PASSOS (limpo) ═══
        st.markdown("### 5. Próximos Passos")
        f_prox_at  = st.text_area("Atividades previstas", value="", height=80,
                                   help="Quais atividades devem ser concluídas ou iniciadas no próximo período?")
        f_prox_pre = st.text_input("Previsão de início/continuidade", value="",
                                    help="Previsão de conclusão para cada atividade listada acima.")
        f_prox_ent = st.text_area("Entregáveis esperados", value="", height=68,
                                   help="Quais entregáveis concretos são esperados até o próximo relatório?")
        f_prox_ri  = st.selectbox("Há riscos identificados?", ["Não", "Sim"], key="prox_ri",
                                   help="Há risco de não cumprimento dos prazos previstos?")
        f_prox_rie = st.text_area("Explicação do risco:", value="", height=68,
                                   help="Descreva o risco e seu possível impacto.") if f_prox_ri == "Sim" else ""
        f_prox_mit = st.text_area("Mitigação:", value="", height=68,
                                   help="Ações previstas para mitigar.") if f_prox_ri == "Sim" else ""

        st.markdown("---")

        # ═══ SEÇÃO 6: DIFICULDADES E SUPORTE (limpo) ═══
        st.markdown("### 6. Dificuldades e Suporte")
        c1, c2 = st.columns(2)
        with c1:
            f_dt  = st.selectbox("Dificuldades técnicas?", ["Não", "Sim"], key="dt",
                                  help="Houve dificuldades técnicas no período?")
            f_da  = st.selectbox("Ajuste metodológico?", ["Não", "Sim"], key="da",
                                  help="Houve necessidade de mudar abordagem?")
        with c2:
            f_dap = st.selectbox("Apoio orientador?", ["Não", "Sim"], key="dap",
                                  help="Houve necessidade de apoio do orientador/coordenador?")
            f_di  = st.selectbox("Necessidade infraestrutura?", ["Não", "Sim"], key="di",
                                  help="Há necessidade de infraestrutura, dados ou equipamento?")
        f_dtq = st.text_area("Quais dificuldades?", value="", height=68,
                              help="Descreva as dificuldades técnicas.") if f_dt == "Sim" else ""
        f_did = st.text_area("Detalhe necessidade:", value="", height=68,
                              help="Detalhe a necessidade de infraestrutura.") if f_di == "Sim" else ""

        st.markdown("---")

        # ═══ SEÇÃO 7: CONSIDERAÇÕES FINAIS (limpo) ═══
        st.markdown("### 7. Considerações Finais")
        f_cf = st.text_area("Fechamento (1-2 parágrafos)", value="", height=150,
                             help="Evolução do trabalho, aderência ao cronograma, expectativa para o próximo ciclo.")

        # ═══ SUBMISSÃO ═══
        submitted = st.form_submit_button("💾 Salvar Formulário", type="primary", use_container_width=True)

        if submitted:
            form_data = {
                "bolsista_id": bolsista["id"], "bolsista_nome": bolsista["nome"],
                "numero_termo": f_termo, "mes_execucao_num": mes_ref,
                "_projeto": proj["nome_projeto"], "_coordenador": proj["coordenador"],
                "nome_bolsista": f_nome, "periodo_referencia": f_periodo,
                "data_preenchimento": f_data_preench,
                "mes_execucao": f"Mês {mes_ref} do projeto ({mes_label(mes_ref)})",
                "responsavel": f_responsavel,
                "atividade_principal": f_ativ_princ, "atividades_secundarias": f_ativ_sec,
                "faixa_cronograma": f_faixa, "conexao_cronograma": f_conexao,
                "status_atividade": f_status, "explicacao_status": f_expl_status,
                "resumo_executivo": f_resumo,
                "atividades": ativs_form if ativs_desig else [],
                "prox_atividades": f_prox_at, "prox_previsao": f_prox_pre,
                "prox_entregaveis": f_prox_ent, "prox_risco": f_prox_ri,
                "prox_risco_explicacao": f_prox_rie, "prox_mitigacao": f_prox_mit,
                "dif_tecnicas": f_dt, "dif_tecnicas_quais": f_dtq,
                "dif_ajuste": f_da, "dif_apoio": f_dap,
                "dif_infra": f_di, "dif_infra_detalhe": f_did,
                "consideracoes_finais": f_cf,
            }
            fn = salvar_formulario(form_data)
            st.success(f"✅ Formulário salvo: **{fn}**")

            # Gerar relatório imediatamente
            rel = gerar_relatorio(form_data, proj)
            st.session_state["rel_ind"] = rel

            # Persistir relatório (local + GitHub)
            fn_rel = salvar_relatorio(rel)
            st.success(f"✅ Relatório salvo: **{fn_rel}**")

            # Limpar modo edição
            st.session_state.pop("modo_edicao", None)

    # ═══════════════════════════════════════════════════
    # RELATÓRIO GERADO (fora do form, aparece após salvar)
    # ═══════════════════════════════════════════════════
    if "rel_ind" in st.session_state:
        st.markdown("---")
        st.markdown("### 📄 Relatório Gerado")
        rel = st.session_state["rel_ind"]

        t1, t2 = st.tabs(["📝 Técnico", "📋 Resumo"])
        with t1:
            st.markdown(rel["bloco1_tecnico"])
        with t2:
            st.markdown(rel["bloco4_resumo"])

        full = "\n---\n".join([rel["bloco1_tecnico"], rel["bloco4_resumo"]])
        fname = f"relatorio_{rel.get('bolsista_id', 'x')}_mes{rel.get('mes_referencia_num', 0)}"
        titulo = f"Relatório — {rel.get('bolsista_nome', '')} — Mês {rel.get('mes_referencia_num', '')}"
        render_botoes_download(full, fname, titulo)


# ═══════════════════════════════════════════════════
#  PÁGINA PRINCIPAL
# ═══════════════════════════════════════════════════
def page_formulario():
    proj  = load_projeto()
    bdata = load_bolsistas()
    bolsistas = bdata["bolsistas"]
    atividades = proj["atividades"]

    st.markdown("""<div class="main-header">
        <h2>📝 Formulário de Atividades do Bolsista</h2>
        <p>Selecione o bolsista e o mês para visualizar o relatório salvo ou preencher um novo formulário.</p>
    </div>""", unsafe_allow_html=True)

    # ── Seleção: Bolsista + Mês ──
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        nome_sel = st.selectbox(
            "Selecione o bolsista",
            [b["nome"] for b in bolsistas],
            help="Escolha o bolsista para ver o relatório ou preencher o formulário."
        )
    bolsista = next(b for b in bolsistas if b["nome"] == nome_sel)

    with col_sel2:
        mes_ref = st.number_input(
            "Mês de referência no projeto",
            min_value=1, max_value=36,
            value=min(mes_atual, 36),
            help=f"Mês 1 = Agosto/2025. Mês atual do projeto: {mes_atual}. Selecione o mês que deseja consultar ou preencher."
        )

    st.markdown("---")

    # ── Verificar se existe formulário salvo ──
    form_salvo = get_formulario_por_mes(bolsista["id"], mes_ref)

    if form_salvo and not st.session_state.get("modo_edicao"):
        exibir_relatorio_salvo(form_salvo, proj, bolsista, mes_ref)
    else:
        # Exibir seletor de situação para cada atividade designada ANTES do form
        ativs_desig = bolsista.get("atividades_designadas", [])
        if ativs_desig:
            st.markdown("#### Situação das Atividades")
            st.caption("Defina a situação de cada atividade antes de preencher os campos abaixo.")
            for idx, ad in enumerate(ativs_desig):
                cod = ad["codigo"]
                nome_at = cod
                for a in atividades:
                    if a["codigo"] == cod:
                        nome_at = f"{cod} {a['nome']}"
                        break
                ss_key = f"sit_{bolsista['id']}_{idx}"
                st.selectbox(
                    nome_at, SITUACAO_OPTS, key=ss_key,
                    help="Selecione o status atual: Não Iniciada, Em andamento, Concluída ou Impedida."
                )
            st.markdown("---")

        exibir_formulario(bolsista, proj, mes_ref)


def main():
    st.markdown("""<div class="main-header">
        <h1>🚢 CASNAV DMarSup </h1>
        <p>Projeto Sistemas Marítimos Não Tripulados | Visão Computacional</p>
    </div>""", unsafe_allow_html=True)
    render_sidebar()
    page_formulario()


# EXECUÇÃO
# =============================================================================
if __name__ == "__main__":
    main()
