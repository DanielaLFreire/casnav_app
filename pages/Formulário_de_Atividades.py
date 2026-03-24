"""
CASNAV DMarSup — Sistema de Acompanhamento de Atividades dos Bolsistas
Projeto Sistemas Marítimos Não Tripulados
Mês 1 do Projeto = Agosto/2025
"""

import streamlit as st
from config import SITUACAO_OPTS, EST_OPTS, mes_atual, hoje, periodo_referencia_auto, render_sidebar
from functions_aux import (load_bolsistas,load_projeto, salvar_formulario,
                           get_ultimo_formulario, calcular_atividades_do_periodo,
                           calcular_faixa_planejada, prefill_gantt_inicio_plan, prefill_gantt_termino_plan)
from report import gerar_relatorio

# ═══════════════════════════════════════════════════
#  FORMULÁRIO DO BOLSISTA  (com pré-preenchimento)
# ═══════════════════════════════════════════════════
def page_formulario():
    proj  = load_projeto()
    bdata = load_bolsistas()
    bolsistas = bdata["bolsistas"]
    atividades = proj["atividades"]

    st.markdown("""<div class="main-header">
        <h2>📝 Formulário de Atividades do Bolsista</h2>
        <p>Campos pré-preenchidos automaticamente quando a informação é conhecida. Complete apenas o que falta.</p>
    </div>""", unsafe_allow_html=True)

    # ── Seleção ──
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        nome_sel = st.selectbox("Selecione o bolsista", [b["nome"] for b in bolsistas])
    bolsista = next(b for b in bolsistas if b["nome"] == nome_sel)
    with col_sel2:
        mes_ref = st.number_input("Mês de referência no projeto", min_value=1, max_value=36, value=min(mes_atual, 36))

    # Dados do último formulário para herança
    ultimo = get_ultimo_formulario(bolsista["id"])
    ativs_periodo = calcular_atividades_do_periodo(bolsista, mes_ref, proj)
    ativs_opcoes  = [f"{a['codigo']} {a['nome']}" for a in atividades]
    ativs_default = [f"{a['codigo']} {a['nome']}" for a in ativs_periodo]


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
    # Selectboxes sem tabs — cada atividade é uma linha com selectbox.
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
        st.caption(
            "⚡ Selecione a situação de cada atividade. Os campos de detalhamento aparecerão no formulário abaixo.")

        # Renderizar um selectbox por atividade — sem tabs
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
            f_nome       = st.text_input("Nome do bolsista", value=bolsista["nome"], disabled=True)
            f_periodo    = st.text_input("Período de referência", value=periodo_referencia_auto(mes_ref))
            f_termo      = st.text_input("Nº do Termo (do bolsista)", value=bolsista.get("numero_termo","") or "")
        with c2:
            f_data_preench = st.date_input("Data de preenchimento", value=hoje).isoformat()
            f_mes_exec     = st.text_input("Mês de execução", value=f"Mês {mes_ref}", disabled=True)
            f_coord        = st.text_input("Coordenador", value=proj["coordenador"], disabled=True)
        f_responsavel = st.text_input("Responsável pelo preenchimento", value=bolsista["nome"])

        st.markdown("---")

        # ═══ SEÇÃO 2: ENQUADRAMENTO ═══
        st.markdown("### 2. Enquadramento no Cronograma")
        _ativ_default_safe = [v for v in ativs_default if v in ativs_opcoes]
        f_ativ_princ = st.multiselect("2.1 Atividade(s) principal(is) do período", ativs_opcoes, default=_ativ_default_safe)
        f_ativ_sec   = st.text_area("2.2 Atividades secundárias", value=h("atividades_secundarias"), height=80)
        f_faixa      = st.text_input("2.3 Faixa planejada no cronograma original", value=calcular_faixa_planejada(bolsista, mes_ref))
        f_conexao    = st.text_area("2.4 Conexão com o cronograma global (4-8 linhas)", value=h("conexao_cronograma"), height=120)
        _status_opts = [
            "dentro da fase originalmente prevista", "adiantada em relação ao cronograma",
            "atrasada em relação ao cronograma", "executada parcialmente fora da faixa originalmente prevista"
        ]
        _status_default = [v for v in h("status_atividade", []) if v in _status_opts]
        f_status     = st.multiselect("2.5 Status da atividade no período", _status_opts, default=_status_default)
        f_expl_status = st.text_area("Explique:", value=h("explicacao_status"), height=80)

        st.markdown("---")

        # ═══ SEÇÃO 3: RESUMO EXECUTIVO ═══
        st.markdown("### 3. Resumo Executivo do Período")
        f_resumo = st.text_area("5 a 10 linhas", value=h("resumo_executivo"), height=150)

        st.markdown("---")

        # ═══ SEÇÃO 4: DETALHAMENTO DAS ATIVIDADES (dentro do form) ═══
        # Lê a situação do session_state (definida fora do form)
        ativs_form = []

        if ativs_desig:
            st.markdown("### 4. Detalhamento das Atividades")

            tabs_det = st.tabs(["Atividade " + ai["codigo"] for ai in ativs_info])

            for idx, (tab, ai) in enumerate(zip(tabs_det, ativs_info)):
                with tab:
                    k = f"a{idx}_"
                    ss_key = f"sit_{bolsista['id']}_{idx}"
                    situacao = st.session_state.get(ss_key, "Não Iniciada")

                    # Mostrar situação atual (informativo, não editável aqui)
                    cor = {"Não Iniciada": "🔘", "Impedida": "🔴", "Em andamento": "🔵", "Concluída": "✅"}
                    st.markdown(f"**Situação:** {cor.get(situacao,'')} {situacao}")

                    a_data = {"codigo": ai["codigo"], "nome": ai["nome"], "situacao": situacao}

                    if situacao == "Não Iniciada":
                        st.info("Atividade ainda não iniciada. Nenhum campo adicional necessário.")
                        a_data["obs"] = st.text_area("Observação (opcional)", value=ha(idx,"obs"), height=68, key=k+"obs")

                    elif situacao == "Impedida":
                        a_data["motivo_impedimento"] = st.text_area(
                            "Motivo do impedimento", value=ha(idx,"motivo_impedimento"), height=100, key=k+"imp")
                        a_data["previsao_desbloqueio"] = st.text_input(
                            "Previsão de desbloqueio", value=ha(idx,"previsao_desbloqueio"), key=k+"desb")
                        a_data["obs"] = st.text_area("Observação", value=ha(idx,"obs"), height=68, key=k+"obs")

                    elif situacao == "Em andamento":
                        a_data["objetivo"] = st.text_area(
                            "Objetivo desta etapa", value=ha(idx,"objetivo", ai.get("descricao_projeto","")), height=80, key=k+"obj")
                        a_data["descricao"] = st.text_area(
                            "Descrição técnica do que está sendo realizado", value=ha(idx,"descricao"), height=120, key=k+"desc")

                        est_ant = ha(idx, "estagio", [])
                        est_safe = [v for v in est_ant if v in EST_OPTS] if isinstance(est_ant, list) else []
                        a_data["estagio"] = st.multiselect("Estágio atual", EST_OPTS, default=est_safe, key=k+"est")

                        a_data["realizado"] = st.text_area(
                            "O que já foi realizado?", value=ha(idx,"realizado"), height=100, key=k+"real")
                        a_data["falta"] = st.text_area(
                            "O que ainda falta?", value=ha(idx,"falta"), height=100, key=k+"falta")
                        a_data["metodos"] = st.text_area(
                            "Métodos, ferramentas, tecnologias", value=ha(idx,"metodos"), height=80, key=k+"met")

                        c1, c2 = st.columns(2)
                        with c1:
                            a_data["entregas_parciais"] = st.selectbox("Entregas parciais?", ["Sim","Não"], key=k+"ep")
                            a_data["inicio_real"] = st.text_input(
                                "Data real de início", value=ha(idx,"inicio_real"), key=k+"ini")
                            a_data["pct_periodo"] = st.slider(
                                "% execução no período", 0, 100, int(ha(idx,"pct_periodo",0)), key=k+"pp")
                        with c2:
                            a_data["quais_entregas"] = st.text_input(
                                "Quais entregas parciais?", value=ha(idx,"quais_entregas"), key=k+"qe")
                            a_data["prazo_original"] = st.text_input(
                                "Prazo original", value=ha(idx,"prazo_original",
                                    f"Mês {ai['meses_inicio']}–{ai['meses_fim']}"), key=k+"po")
                            a_data["pct_acum"] = st.slider(
                                "% acumulado", 0, 100, int(ha(idx,"pct_acum",0)), key=k+"pa")

                        a_data["previsao"] = st.text_input(
                            "Previsão atualizada de conclusão", value=ha(idx,"previsao"), key=k+"prev")
                        a_data["dificuldades"] = st.text_area(
                            "Dificuldades e riscos", value=ha(idx,"dificuldades"), height=80, key=k+"dif")
                        a_data["marco"] = st.text_input(
                            "Marco esperado para encerrar", value=ha(idx,"marco"), key=k+"marco")
                        a_data["relevancia"] = st.selectbox(
                            "Relevância para avanço físico", ["baixa","média","alta"], index=2, key=k+"rel")


                    elif situacao == "Concluída":
                        a_data["objetivo"] = st.text_area(
                            "Objetivo da atividade", value=ha(idx,"objetivo", ai.get("descricao_projeto","")), height=80, key=k+"obj")
                        a_data["descricao"] = st.text_area(
                            "Descrição técnica do que foi realizado", value=ha(idx,"descricao"), height=120, key=k+"desc")
                        a_data["metodos"] = st.text_area(
                            "Métodos, ferramentas, tecnologias", value=ha(idx,"metodos"), height=80, key=k+"met")
                        a_data["entregas"] = st.text_area(
                            "Produtos/entregas concretas", value=ha(idx,"entregas"), height=80, key=k+"entr")
                        c1, c2 = st.columns(2)
                        with c1:
                            a_data["verificavel"] = st.selectbox("Verificáveis?", ["Sim","Não"], key=k+"verif")
                            a_data["inicio_real"] = st.text_input("Data real início", value=ha(idx,"inicio_real"), key=k+"ini")
                        with c2:
                            a_data["armazenamento"] = st.text_input("Onde armazenadas?", value=ha(idx,"armazenamento"), key=k+"arm")
                            a_data["conclusao_real"] = st.text_input("Data real conclusão", value=ha(idx,"conclusao_real"), key=k+"conc")
                        a_data["resultados"] = st.text_area(
                            "Resultados obtidos", value=ha(idx,"resultados"), height=80, key=k+"res")
                        a_data["contribuicao"] = st.text_area(
                            "Contribuição ao projeto", value=ha(idx,"contribuicao"), height=68, key=k+"contrib")
                        a_data["pct_acum"] = st.slider(
                            "% execução acumulada", 0, 100, int(ha(idx,"pct_acum",100)), key=k+"pa")
                        a_data["marco"] = st.text_input(
                            "Marco principal", value=ha(idx,"marco"), key=k+"marco")
                        a_data["impacto_proxima"] = st.text_input(
                            "Impacto em qual próxima etapa?", value=ha(idx,"impacto_proxima"), key=k+"impac")
                        a_data["obs"] = st.text_area(
                            "Observação gerencial", value=ha(idx,"obs"), height=68, key=k+"obs")

                    ativs_form.append(a_data)
        else:
            st.warning("⚠️ Nenhuma atividade designada para este bolsista. Configure em 👥 Gestão de Bolsistas.")

        st.markdown("---")

        # ═══ SEÇÃO 7: PRÓXIMOS PASSOS ═══
        st.markdown("### 7. Próximos Passos")
        f_prox_at  = st.text_area("Próximas atividades", value=h("prox_atividades"), height=80)
        f_prox_pre = st.text_input("Previsão de conclusão", value=h("prox_previsao"))
        f_prox_ent = st.text_area("Entregáveis esperados", value=h("prox_entregaveis"), height=68)
        f_prox_ri  = st.selectbox("Risco de não cumprimento?", ["Sim","Não"], key="pr")
        f_prox_rie = st.text_area("Se sim, explique:", value=h("prox_risco_explicacao"), height=68, key="pre")
        f_prox_mit = st.text_area("Ações de mitigação:", value=h("prox_mitigacao"), height=68)

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
        f_cs_just = st.text_area("Justificativa do percentual (4-8 linhas)", value=h("curva_justificativa"), height=120)

        f_cf = st.text_area("Fechamento (1-2 parágrafos)", value=h("consideracoes_finais"), height=150)

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
                "curva_justificativa": f_cs_just,
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

    # ═══════════════════════════════════════════════════
    # RELATÓRIO GERADO (fora do form, aparece após salvar)
    # ═══════════════════════════════════════════════════
    if "rel_ind" in st.session_state:
        st.markdown("---")
        st.markdown("### 📄 Relatório Gerado")
        rel = st.session_state["rel_ind"]

        t1, t2 = st.tabs(["📝 Técnico",  "📋 Resumo"])
        with t1: st.markdown(rel["bloco1_tecnico"])
        with t2: st.markdown(rel["bloco2_resumo"])

        full = "\n---\n".join([rel["bloco1_tecnico"],  rel["bloco2_resumo"]])
        st.download_button("📥 Baixar Relatório (.md)", full,
            file_name=f"relatorio_{rel.get('bolsista_id','x')}.md")

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
