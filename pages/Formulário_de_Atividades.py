"""
CASNAV DMarSup — Sistema de Acompanhamento de Atividades dos Bolsistas
Projeto Sistemas Marítimos Não Tripulados
Mês 1 do Projeto = Agosto/2025

Página: Formulário de Atividades
- Permite selecionar bolsista e mês (padrão = mês atual)
- Se existir formulário salvo para bolsista+mês → exibe relatório gerado
- Se não existir → exibe formulário para preenchimento
"""

import streamlit as st
from config import (SITUACAO_OPTS, EST_OPTS, mes_atual, hoje,
                    periodo_referencia_auto, render_sidebar, mes_label, mes_label_curto)
from functions_aux import (load_bolsistas, load_projeto, salvar_formulario,
                           get_ultimo_formulario, calcular_atividades_do_periodo,
                           calcular_faixa_planejada, prefill_gantt_inicio_plan,
                           prefill_gantt_termino_plan, get_formularios_bolsista)
from report import gerar_relatorio


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

    # Info do formulário
    ts = form_salvo.get("_salvamento", "—")
    st.success(f"✅ Formulário encontrado para **{bolsista['nome']}** — **{mes_label(mes_ref)}** (salvo em {ts})")

    # Gerar relatório
    rel = gerar_relatorio(form_salvo, proj)

    # Tabs com os 4 blocos
    t1, t2 = st.tabs(["📝 Técnico", "📋 Resumo"])
    with t1:
        st.markdown(rel["bloco1_tecnico"])
    with t2:
        st.markdown(rel["bloco2_resumo"])

    # Ações
    st.markdown("---")
    col_dl, col_json, col_edit = st.columns(3)

    with col_dl:
        full = "\n---\n".join([
            rel["bloco1_tecnico"], rel["bloco2_resumo"]
        ])
        st.download_button(
            "📥 Baixar Relatório (.md)", full,
            file_name=f"relatorio_{bolsista['id']}_mes{mes_ref}.md",
            use_container_width=True
        )

    with col_json:
        with st.expander("📋 Ver dados do formulário"):
            st.json(form_salvo)

    with col_edit:
        if st.button("✏️ Editar / Reenviar", use_container_width=True, key="btn_editar"):
            st.session_state["modo_edicao"] = True
            st.rerun()


# ═══════════════════════════════════════════════════
#  FORMULÁRIO DO BOLSISTA  (com pré-preenchimento)
# ═══════════════════════════════════════════════════
def exibir_formulario(proj, bolsista, mes_ref, atividades, form_existente=None):
    """Exibe o formulário para preenchimento (novo ou edição)."""

    # Dados do último formulário para herança
    # Se estamos editando, usa o form existente; senão, o último salvo
    ultimo = form_existente or get_ultimo_formulario(bolsista["id"])

    ativs_periodo = calcular_atividades_do_periodo(bolsista, mes_ref, proj)
    ativs_opcoes  = [f"{a['codigo']} {a['nome']}" for a in atividades]
    ativs_default = [f"{a['codigo']} {a['nome']}" for a in ativs_periodo]

    # Info de pré-preenchimento
    pre_info = []
    pre_info.append(f"**Nome, coordenador, termo, data** ← cadastro do bolsista")
    pre_info.append(f"**Mês {mes_ref}** = {mes_label_curto(mes_ref)}, período = {periodo_referencia_auto(mes_ref)}")
    if ativs_default:
        pre_info.append(f"**Atividades sugeridas:** {', '.join(ativs_default)}")
    if form_existente:
        pre_info.append(f"**Modo edição** — carregando dados do formulário salvo ({form_existente.get('_salvamento','')})")
    elif ultimo:
        pre_info.append(f"**Último formulário encontrado** ({ultimo.get('_salvamento','')}) — dados herdados como ponto de partida")
    st.markdown('<div class="prefill-info">' + "<br>".join(pre_info) + '</div>', unsafe_allow_html=True)

    # Helper para herdar valor
    def h(key, fallback=""):
        """Herda valor do último formulário ou retorna fallback."""
        if ultimo:
            return ultimo.get(key, fallback)
        return fallback

    # Herdar dados de atividades do último formulário
    def ha(idx, campo, fallback=""):
        """Herda campo da atividade idx do último formulário."""
        if ultimo and "atividades" in ultimo:
            ativs_ant = ultimo["atividades"]
            if idx < len(ativs_ant):
                return ativs_ant[idx].get(campo, fallback)
        return fallback

    # ═══════════════════════════════════════════════════
    # SEÇÃO 4 — SITUAÇÃO DAS ATIVIDADES (FORA DO FORM)
    # ═══════════════════════════════════════════════════
    ativs_desig = bolsista.get("atividades_designadas", [])
    ativs_info = []

    if ativs_desig:
        for ad in ativs_desig:
            cod = ad["codigo"]
            info = {"codigo": cod, "nome": cod, "periodicidade": ad.get("periodicidade", ""),
                    "meses_inicio": ad.get("meses_inicio", 0), "meses_fim": ad.get("meses_fim", 0)}
            for a in proj["atividades"]:
                if a["codigo"] == cod:
                    info["nome"] = f"{cod} {a['nome']}"
                    info["descricao_projeto"] = a.get("descricao", "")
                    info["entregas_projeto"] = a.get("entregas", "")
                    break
            ativs_info.append(info)

        st.markdown("### Situação das Atividades Designadas")
        st.caption("⚡ Selecione a situação de cada atividade. Os campos de detalhamento aparecerão no formulário abaixo.")

        for idx, ai in enumerate(ativs_info):
            ss_key = f"sit_{bolsista['id']}_{idx}"
            if ss_key not in st.session_state:
                st.session_state[ss_key] = ha(idx, "situacao", "Não Iniciada")

            col_nome, col_sit = st.columns([3, 2])
            with col_nome:
                st.markdown(f"**{ai['nome']}**")
                st.caption(f"📅 {ai.get('periodicidade', '')} | Entrega: {ai.get('entregas_projeto', '—')}")
            with col_sit:
                st.selectbox(
                    "Situação", SITUACAO_OPTS,
                    key=ss_key,
                    label_visibility="collapsed"
                )

    st.markdown("---")

    # ═══════════════════════════════════════════════════
    # FORM PRINCIPAL — todos os campos de preenchimento
    # ═══════════════════════════════════════════════════
    with st.form("formulario_bolsista", clear_on_submit=False):

        # ═══ SEÇÃO 1: IDENTIFICAÇÃO (100% pré-preenchido) ═══
        st.markdown("### 1. Identificação")
        st.caption("ℹ️ Campos preenchidos automaticamente com base no cadastro do bolsista e no mês selecionado.")
        c1, c2 = st.columns(2)
        with c1:
            f_nome       = st.text_input("Nome do bolsista", value=bolsista["nome"], disabled=True,
                                         help="Preenchido automaticamente a partir do cadastro.")
            f_periodo    = st.text_input("Período de referência", value=periodo_referencia_auto(mes_ref),
                                         help="Intervalo de datas coberto por este relatório.")
            f_termo      = st.text_input("Nº do Termo (do bolsista)",
                                         value=bolsista.get("numero_termo","") or "",
                                         help="Número do Termo de Concessão de Bolsa (atributo do bolsista).")
        with c2:
            f_data_preench = st.date_input("Data de preenchimento", value=hoje,
                                           help="Data em que o bolsista está preenchendo este formulário.").isoformat()
            f_mes_exec     = st.text_input("Mês de execução", value=f"Mês {mes_ref}", disabled=True,
                                           help="Mês do projeto calculado automaticamente.")
            f_coord        = st.text_input("Coordenador", value=proj["coordenador"], disabled=True,
                                           help="Coordenador do projeto, preenchido automaticamente.")
        f_responsavel = st.text_input("Responsável pelo preenchimento", value=bolsista["nome"],
                                      help="Nome de quem está preenchendo.")

        st.markdown("---")

        # ═══ SEÇÃO 2: ENQUADRAMENTO ═══
        st.markdown("### 2. Enquadramento no Cronograma")
        _ativ_default_safe = [v for v in ativs_default if v in ativs_opcoes]
        f_ativ_princ = st.multiselect("2.1 Atividade(s) principal(is) do período", ativs_opcoes,
                                       default=_ativ_default_safe,
                                       help="Selecione as atividades do cronograma em que trabalhou neste período.")
        f_ativ_sec   = st.text_area("2.2 Atividades secundárias", value=h("atividades_secundarias"), height=80,
                                     help="Atividades de apoio realizadas no período.")
        f_faixa      = st.text_input("2.3 Faixa planejada no cronograma original",
                                      value=calcular_faixa_planejada(bolsista, mes_ref),
                                      help="Faixa de meses prevista no cronograma original.")
        f_conexao    = st.text_area("2.4 Conexão com o cronograma global (4-8 linhas)",
                                     value=h("conexao_cronograma"), height=120,
                                     help="Explique como as atividades se conectam ao cronograma macro do projeto.")
        _status_opts = [
            "dentro da fase originalmente prevista", "adiantada em relação ao cronograma",
            "atrasada em relação ao cronograma", "executada parcialmente fora da faixa originalmente prevista"
        ]
        _status_default = [v for v in h("status_atividade", []) if v in _status_opts]
        f_status     = st.multiselect("2.5 Status da atividade no período", _status_opts,
                                       default=_status_default,
                                       help="Selecione um ou mais status que descrevam a situação das atividades.")
        f_expl_status = st.text_area("Explique:", value=h("explicacao_status"), height=80)

        st.markdown("---")

        # ═══ SEÇÃO 3: RESUMO EXECUTIVO ═══
        st.markdown("### 3. Resumo Executivo do Período")
        f_resumo = st.text_area("5 a 10 linhas", value=h("resumo_executivo"), height=150)

        st.markdown("---")

        # ═══ SEÇÃO 4: ATIVIDADES DESIGNADAS ═══
        st.markdown("### 4. Atividades Designadas")
        ativs_form = []

        if not ativs_desig:
            st.warning("⚠️ Nenhuma atividade designada para este bolsista. Configure em 👥 Gestão de Bolsistas.")
        else:
            for idx, ai in enumerate(ativs_info):
                ss_key = f"sit_{bolsista['id']}_{idx}"
                situacao = st.session_state.get(ss_key, "Não Iniciada")

                st.markdown(f"#### {ai['nome']}")
                st.caption(f"Situação: **{situacao}** | {ai.get('periodicidade','')}")

                ativ_data = {"codigo": ai["codigo"], "nome": ai["nome"], "situacao": situacao}

                if situacao == "Concluída":
                    ativ_data["objetivo"]  = st.text_area(f"Objetivo ({ai['codigo']})", value=ha(idx, "objetivo"), height=68, key=f"obj_{idx}")
                    ativ_data["descricao"] = st.text_area(f"Descrição ({ai['codigo']})", value=ha(idx, "descricao"), height=80, key=f"desc_{idx}")
                    ativ_data["entregas"]  = st.text_area(f"Entregas ({ai['codigo']})", value=ha(idx, "entregas"), height=68, key=f"ent_{idx}")
                    ativ_data["pct_acum"]  = st.slider(f"% acumulado ({ai['codigo']})", 0, 100, int(ha(idx, "pct_acum", 100)), key=f"pct_{idx}")
                    ativ_data["marco"]     = st.text_input(f"Marco ({ai['codigo']})", value=ha(idx, "marco"), key=f"mar_{idx}")
                    ativ_data["obs"]       = st.text_area(f"Observações ({ai['codigo']})", value=ha(idx, "obs"), height=68, key=f"obs_{idx}")

                elif situacao == "Em andamento":
                    _est_default = [v for v in ha(idx, "estagio", []) if v in EST_OPTS]
                    ativ_data["estagio"]     = st.multiselect(f"Estágio ({ai['codigo']})", EST_OPTS, default=_est_default, key=f"est_{idx}")
                    ativ_data["objetivo"]    = st.text_area(f"Objetivo ({ai['codigo']})", value=ha(idx, "objetivo"), height=68, key=f"obj_{idx}")
                    ativ_data["descricao"]   = st.text_area(f"Descrição ({ai['codigo']})", value=ha(idx, "descricao"), height=80, key=f"desc_{idx}")
                    ativ_data["realizado"]   = st.text_area(f"O que foi realizado ({ai['codigo']})", value=ha(idx, "realizado"), height=80, key=f"real_{idx}")
                    ativ_data["falta"]       = st.text_area(f"O que falta ({ai['codigo']})", value=ha(idx, "falta"), height=68, key=f"falta_{idx}")
                    c1, c2 = st.columns(2)
                    with c1:
                        ativ_data["pct_periodo"] = st.slider(f"% no período ({ai['codigo']})", 0, 100, int(ha(idx, "pct_periodo", 0)), key=f"pp_{idx}")
                    with c2:
                        ativ_data["pct_acum"]    = st.slider(f"% acumulado ({ai['codigo']})", 0, 100, int(ha(idx, "pct_acum", 0)), key=f"pa_{idx}")
                    ativ_data["dificuldades"]    = st.text_area(f"Dificuldades ({ai['codigo']})", value=ha(idx, "dificuldades"), height=68, key=f"dif_{idx}")
                    ativ_data["previsao"]        = st.text_input(f"Previsão de conclusão ({ai['codigo']})", value=ha(idx, "previsao"), key=f"prev_{idx}")
                    ativ_data["marco"]           = st.text_input(f"Marco ({ai['codigo']})", value=ha(idx, "marco"), key=f"mar_{idx}")

                elif situacao == "Impedida":
                    ativ_data["motivo_impedimento"]    = st.text_area(f"Motivo ({ai['codigo']})", value=ha(idx, "motivo_impedimento"), height=80, key=f"imp_{idx}")
                    ativ_data["previsao_desbloqueio"]  = st.text_input(f"Previsão de desbloqueio ({ai['codigo']})", value=ha(idx, "previsao_desbloqueio"), key=f"desb_{idx}")

                # Não Iniciada: nenhum campo extra

                ativs_form.append(ativ_data)
                st.markdown("---")

        # ═══ SEÇÃO 7: PRÓXIMOS PASSOS ═══
        st.markdown("### 7. Próximos Passos")
        f_prox_at  = st.text_area("Atividades previstas", value=h("prox_atividades"), height=80)
        f_prox_pre = st.text_input("Previsão de início/continuidade", value=h("prox_previsao"))
        f_prox_ent = st.text_area("Entregáveis esperados", value=h("prox_entregaveis"), height=68)
        f_prox_ri  = st.selectbox("Há riscos identificados?", ["Sim", "Não"],
                                   index=0 if h("prox_risco") == "Sim" else 1, key="prox_ri")
        f_prox_rie = st.text_area("Explicação do risco:", value=h("prox_risco_explicacao"), height=68) if f_prox_ri == "Sim" else ""
        f_prox_mit = st.text_area("Mitigação:", value=h("prox_mitigacao"), height=68) if f_prox_ri == "Sim" else ""

        st.markdown("---")



        # ═══ SEÇÃO 8: DIFICULDADES ═══
        st.markdown("### 8. Dificuldades e Suporte")
        c1, c2 = st.columns(2)
        with c1:
            f_dt  = st.selectbox("Dificuldades técnicas?", ["Sim","Não"], key="dt")
            f_da  = st.selectbox("Ajuste metodológico?", ["Sim","Não"], key="da")
        with c2:
            f_dap = st.selectbox("Apoio orientador?", ["Sim","Não"], key="dap")
            f_di  = st.selectbox("Necessidade infraestrutura?", ["Sim","Não"], key="di")
        f_dtq = st.text_area("Quais dificuldades?", value=h("dif_tecnicas_quais"), height=68) if f_dt == "Sim" else ""
        f_did = st.text_area("Detalhe necessidade:", value=h("dif_infra_detalhe"), height=68) if f_di == "Sim" else ""

        st.markdown("---")

        # ═══ SEÇÃO 9: CONSIDERAÇÕES FINAIS ═══
        st.markdown("### 9. Considerações Finais")
        f_cf = st.text_area("Fechamento (1-2 parágrafos)", value=h("consideracoes_finais"), height=150,
                             help="Evolução do trabalho, aderência ao cronograma, expectativa para o próximo ciclo.")

        # ═══ SUBMISSÃO ═══
        submitted = st.form_submit_button("💾 Salvar Formulário", type="primary", use_container_width=True)

        if submitted:
            form_data = {
                "bolsista_id": bolsista["id"], "bolsista_nome": bolsista["nome"],
                "numero_termo": f_termo, "mes_execucao_num": mes_ref,
                "_projeto": proj["nome_projeto"], "_coordenador": proj["coordenador"],
                "nome_bolsista": f_nome, "periodo_referencia": f_periodo,
                "data_preenchimento": f_data_preench, "mes_execucao": f_mes_exec,
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
            st.markdown(rel["bloco2_resumo"])

        full = "\n---\n".join([rel["bloco1_tecnico"], rel["bloco2_resumo"]])
        st.download_button("📥 Baixar Relatório (.md)", full,
                           file_name=f"relatorio_{rel.get('bolsista_id','x')}.md")


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

    st.caption(f"📅 **{mes_label(mes_ref)}** — Período: {periodo_referencia_auto(mes_ref)}")

    # ── Verificar se existe formulário salvo ──
    form_salvo = get_formulario_por_mes(bolsista["id"], mes_ref)
    modo_edicao = st.session_state.get("modo_edicao", False)

    if form_salvo and not modo_edicao:
        # ════════════════════════════════════════════
        # MODO VISUALIZAÇÃO: mostrar relatório salvo
        # ════════════════════════════════════════════
        exibir_relatorio_salvo(form_salvo, proj, bolsista, mes_ref)

    else:
        # ════════════════════════════════════════════
        # MODO PREENCHIMENTO: formulário novo ou edição
        # ════════════════════════════════════════════
        if form_salvo and modo_edicao:
            st.info("✏️ **Modo edição** — os campos foram carregados com os dados do formulário salvo. Altere o que precisar e salve novamente.")
            if st.button("↩️ Voltar para visualização", key="btn_voltar"):
                st.session_state.pop("modo_edicao", None)
                st.rerun()
        else:
            st.info(f"📝 Nenhum formulário encontrado para **{bolsista['nome']}** no **{mes_label(mes_ref)}**. Preencha abaixo.")

        exibir_formulario(proj, bolsista, mes_ref, atividades,
                          form_existente=form_salvo if modo_edicao else None)


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
