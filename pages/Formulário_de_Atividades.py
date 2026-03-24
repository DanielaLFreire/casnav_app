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
        nome_sel = st.selectbox("Selecione o bolsista", [b["nome"] for b in bolsistas], help="Escolha o bolsista que irá preencher o formulário.")
    bolsista = next(b for b in bolsistas if b["nome"] == nome_sel)
    with col_sel2:
        mes_ref = st.number_input("Mês de referência no projeto", min_value=1, max_value=36, value=min(mes_atual, 36), help="Mês 1 = Agosto/2025. Informe o mês do projeto a que este relatório se refere.")

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
            f_nome       = st.text_input("Nome do bolsista", value=bolsista["nome"], disabled=True, help="Preenchido automaticamente a partir do cadastro.")
            f_periodo    = st.text_input("Período de referência", value=periodo_referencia_auto(mes_ref), help="Intervalo de datas coberto por este relatório. Ex.: 01/08/2025 a 31/08/2025.")
            f_termo      = st.text_input("Nº do Termo (do bolsista)", value=bolsista.get("numero_termo","") or "", help="Número do Termo de Concessão de Bolsa (atributo do bolsista, não do projeto).")
        with c2:
            f_data_preench = st.date_input("Data de preenchimento", value=hoje, help="Data em que o bolsista está preenchendo este formulário.").isoformat()
            f_mes_exec     = st.text_input("Mês de execução", value=f"Mês {mes_ref}", disabled=True, help="Mês do projeto calculado automaticamente.")
            f_coord        = st.text_input("Coordenador", value=proj["coordenador"], disabled=True, help="Coordenador do projeto, preenchido automaticamente.")
        f_responsavel = st.text_input("Responsável pelo preenchimento", value=bolsista["nome"], help="Nome de quem está preenchendo. Pode ser diferente do bolsista.")

        st.markdown("---")

        # ═══ SEÇÃO 2: ENQUADRAMENTO ═══
        st.markdown("### 2. Enquadramento no Cronograma")
        _ativ_default_safe = [v for v in ativs_default if v in ativs_opcoes]
        f_ativ_princ = st.multiselect("2.1 Atividade(s) principal(is) do período", ativs_opcoes, default=_ativ_default_safe, help="Selecione as atividades do cronograma em que trabalhou neste período.")
        f_ativ_sec   = st.text_area("2.2 Atividades secundárias", value=h("atividades_secundarias"), height=80, help="Atividades de apoio realizadas no período (revisão de literatura, reuniões, etc.).")
        f_faixa      = st.text_input("2.3 Faixa planejada no cronograma original", value=calcular_faixa_planejada(bolsista, mes_ref), help="Faixa de meses prevista no cronograma original para as atividades do período.")
        f_conexao    = st.text_area("2.4 Conexão com o cronograma global (4-8 linhas)", value=h("conexao_cronograma"), height=120, help="Explique como as atividades realizadas se conectam ao cronograma macro do projeto.")
        _status_opts = [
            "dentro da fase originalmente prevista", "adiantada em relação ao cronograma",
            "atrasada em relação ao cronograma", "executada parcialmente fora da faixa originalmente prevista"
        ]
        _status_default = [v for v in h("status_atividade", []) if v in _status_opts]
        f_status     = st.multiselect("2.5 Status da atividade no período", _status_opts, default=_status_default, help="Selecione um ou mais status que descrevam a situação das atividades no período.")
        f_expl_status = st.text_area("Explique:", value=h("explicacao_status"), height=80, help="Justifique atrasos, adiantamentos ou desvios em relação ao cronograma original.")

        st.markdown("---")

        # ═══ SEÇÃO 3: RESUMO EXECUTIVO ═══
        st.markdown("### 3. Resumo Executivo do Período")
        f_resumo = st.text_area("5 a 10 linhas", value=h("resumo_executivo"), height=150, help="Resuma: etapa focal, principais ações, entregas relevantes, estágio atual e impacto na próxima etapa.")

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
                        a_data["obs"] = st.text_area("Observação (opcional)", value=ha(idx,"obs"), height=68, key=k+"obs", help="Qualquer comentário relevante sobre esta atividade ainda não iniciada.")

                    elif situacao == "Impedida":
                        a_data["motivo_impedimento"] = st.text_area(
                            "Motivo do impedimento", value=ha(idx,"motivo_impedimento"), height=100, key=k+"imp", help="Descreva o que está impedindo o início ou continuidade desta atividade.")
                        a_data["previsao_desbloqueio"] = st.text_input(
                            "Previsão de desbloqueio", value=ha(idx,"previsao_desbloqueio"), key=k+"desb", help="Quando se espera que o impedimento seja resolvido.")
                        a_data["obs"] = st.text_area("Observação", value=ha(idx,"obs"), height=68, key=k+"obs")

                    elif situacao == "Em andamento":
                        a_data["objetivo"] = st.text_area(
                            "Objetivo desta etapa", value=ha(idx,"objetivo", ai.get("descricao_projeto","")), height=80, key=k+"obj", help="O que se pretende alcançar com esta atividade no período.")
                        a_data["descricao"] = st.text_area(
                            "Descrição técnica do que está sendo realizado", value=ha(idx,"descricao"), height=120, key=k+"desc", help="Descreva com detalhes técnicos o que está sendo feito: métodos, pipelines, datasets, experimentos.")

                        est_ant = ha(idx, "estagio", [])
                        est_safe = [v for v in est_ant if v in EST_OPTS] if isinstance(est_ant, list) else []
                        a_data["estagio"] = st.multiselect("Estágio atual", EST_OPTS, default=est_safe, key=k+"est", help="Selecione um ou mais estágios que descrevam a fase atual da atividade.")

                        a_data["realizado"] = st.text_area(
                            "O que já foi realizado?", value=ha(idx,"realizado"), height=100, key=k+"real", help="Liste concretamente o que foi produzido até agora: scripts, datasets, experimentos, documentos.")
                        a_data["falta"] = st.text_area(
                            "O que ainda falta?", value=ha(idx,"falta"), height=100, key=k+"falta", help="Descreva o que ainda precisa ser feito para concluir esta atividade.")
                        a_data["metodos"] = st.text_area(
                            "Métodos, ferramentas, tecnologias", value=ha(idx,"metodos"), height=80, key=k+"met", help="Linguagens, frameworks, bases de dados, infraestrutura utilizada.")

                        c1, c2 = st.columns(2)
                        with c1:
                            a_data["entregas_parciais"] = st.selectbox("Entregas parciais?", ["Sim","Não"], key=k+"ep", help="Já existem produtos intermediários verificáveis?")
                            a_data["inicio_real"] = st.text_input(
                                "Data real de início", value=ha(idx,"inicio_real"), key=k+"ini", help="Quando esta atividade efetivamente começou. Ex.: Novembro/2025.")
                            a_data["pct_periodo"] = st.slider(
                                "% execução no período", 0, 100, int(ha(idx,"pct_periodo",0)), key=k+"pp", help="Quanto desta atividade avançou especificamente neste período.")
                        with c2:
                            a_data["quais_entregas"] = st.text_input(
                                "Quais entregas parciais?", value=ha(idx,"quais_entregas"), key=k+"qe", help="Liste os produtos intermediários já entregues.")
                            a_data["prazo_original"] = st.text_input(
                                "Prazo original", value=ha(idx,"prazo_original",
                                    f"Mês {ai['meses_inicio']}–{ai['meses_fim']}"), key=k+"po", help="Prazo originalmente previsto no cronograma do projeto.")
                            a_data["pct_acum"] = st.slider(
                                "% acumulado", 0, 100, int(ha(idx,"pct_acum",0)), key=k+"pa", help="Percentual total de execução desta atividade até o momento.")

                        a_data["previsao"] = st.text_input(
                            "Previsão atualizada de conclusão", value=ha(idx,"previsao"), key=k+"prev", help="Nova data estimada de conclusão. Ex.: Julho/2026.")
                        a_data["dificuldades"] = st.text_area(
                            "Dificuldades e riscos", value=ha(idx,"dificuldades"), height=80, key=k+"dif", help="Bloqueios, limitações técnicas, riscos identificados e como foram tratados.")
                        a_data["marco"] = st.text_input(
                            "Marco esperado para encerrar", value=ha(idx,"marco"), key=k+"marco", help="Entrega ou evento que marca a conclusão desta atividade.")
                        a_data["relevancia"] = st.selectbox(
                            "Relevância para avanço físico", ["baixa","média","alta"], index=2, key=k+"rel", help="Quanto esta atividade contribui para o avanço físico mensurável do projeto.")


                    elif situacao == "Concluída":
                        a_data["objetivo"] = st.text_area(
                            "Objetivo da atividade", value=ha(idx,"objetivo", ai.get("descricao_projeto","")), height=80, key=k+"obj", help="O que esta atividade se propôs a alcançar.")
                        a_data["descricao"] = st.text_area(
                            "Descrição técnica do que foi realizado", value=ha(idx,"descricao"), height=120, key=k+"desc", help="Descreva tecnicamente o que foi feito do início ao fim.")
                        a_data["metodos"] = st.text_area(
                            "Métodos, ferramentas, tecnologias", value=ha(idx,"metodos"), height=80, key=k+"met", help="Ferramentas, linguagens e infraestrutura utilizadas.")
                        a_data["entregas"] = st.text_area(
                            "Produtos/entregas concretas", value=ha(idx,"entregas"), height=80, key=k+"entr", help="Liste todos os produtos finais gerados: datasets, modelos, scripts, documentos.")
                        c1, c2 = st.columns(2)
                        with c1:
                            a_data["verificavel"] = st.selectbox("Verificáveis?", ["Sim","Não"], key=k+"verif", help="As entregas podem ser verificadas por terceiros (código, dados, relatórios)?")
                            a_data["inicio_real"] = st.text_input("Data real início", value=ha(idx,"inicio_real"), key=k+"ini", help="Quando esta atividade efetivamente começou.")
                        with c2:
                            a_data["armazenamento"] = st.text_input("Onde armazenadas?", value=ha(idx,"armazenamento"), key=k+"arm", help="Repositório, Drive, servidor, Colab — onde as entregas podem ser verificadas.")
                            a_data["conclusao_real"] = st.text_input("Data real conclusão", value=ha(idx,"conclusao_real"), key=k+"conc", help="Quando esta atividade foi efetivamente concluída.")
                        a_data["resultados"] = st.text_area(
                            "Resultados obtidos", value=ha(idx,"resultados"), height=80, key=k+"res", help="Resultados técnicos e científicos alcançados com a conclusão.")
                        a_data["contribuicao"] = st.text_area(
                            "Contribuição ao projeto", value=ha(idx,"contribuicao"), height=68, key=k+"contrib", help="Como esta entrega contribui para o objetivo geral do projeto.")
                        a_data["pct_acum"] = st.slider(
                            "% execução acumulada", 0, 100, int(ha(idx,"pct_acum",100)), key=k+"pa", help="Deve ser 100% se a atividade foi concluída integralmente.")
                        a_data["marco"] = st.text_input(
                            "Marco principal", value=ha(idx,"marco"), key=k+"marco", help="Entrega ou evento que oficializa a conclusão desta atividade.")
                        a_data["impacto_proxima"] = st.text_input(
                            "Impacto em qual próxima etapa?", value=ha(idx,"impacto_proxima"), key=k+"impac", help="Qual atividade depende desta conclusão para avançar.")
                        a_data["obs"] = st.text_area(
                            "Observação gerencial", value=ha(idx,"obs"), height=68, key=k+"obs", help="Comentário curto sobre prazo, qualidade ou dependências para o gestor.")

                    ativs_form.append(a_data)
        else:
            st.warning("⚠️ Nenhuma atividade designada para este bolsista. Configure em 👥 Gestão de Bolsistas.")

        st.markdown("---")

        # ═══ SEÇÃO 7: PRÓXIMOS PASSOS ═══
        st.markdown("### 7. Próximos Passos")
        f_prox_at  = st.text_area("Próximas atividades", value=h("prox_atividades"), height=80, help="Quais atividades serão executadas no próximo período.")
        f_prox_pre = st.text_input("Previsão de conclusão", value=h("prox_previsao"), help="Data estimada de conclusão de cada atividade listada acima.")
        f_prox_ent = st.text_area("Entregáveis esperados", value=h("prox_entregaveis"), height=68, help="Produtos concretos esperados até o próximo relatório.")
        f_prox_ri  = st.selectbox("Risco de não cumprimento?", ["Sim","Não"], key="pr", help="Existe risco de não cumprir os prazos previstos?")
        f_prox_rie = st.text_area("Se sim, explique:", value=h("prox_risco_explicacao"), height=68, key="pre", help="Descreva os riscos que podem afetar o cumprimento dos prazos.")
        f_prox_mit = st.text_area("Ações de mitigação:", value=h("prox_mitigacao"), height=68, help="O que será feito para reduzir ou eliminar os riscos identificados.")

        st.markdown("---")

        # ═══ SEÇÃO 8: DIFICULDADES ═══
        st.markdown("### 8. Dificuldades e Suporte")
        c1, c2 = st.columns(2)
        with c1:
            f_dt  = st.selectbox("Dificuldades técnicas?", ["Sim","Não"], key="dt", help="Houve problemas técnicos que afetaram o andamento?")
            f_da  = st.selectbox("Ajuste metodológico?", ["Sim","Não"], key="da", help="Foi necessário mudar a abordagem ou método de trabalho?")
        with c2:
            f_dap = st.selectbox("Apoio orientador?", ["Sim","Não"], key="dap", help="Houve necessidade de apoio do orientador ou equipe?")
            f_di  = st.selectbox("Necessidade infraestrutura?", ["Sim","Não"], key="di", help="Há necessidade de infra, dados, equipamento ou decisão gerencial?")
        f_dtq = st.text_area("Quais dificuldades?", value=h("dif_tecnicas_quais"), height=68) if f_dt == "Sim" else ""
        f_did = st.text_area("Detalhe necessidade:", value=h("dif_infra_detalhe"), height=68) if f_di == "Sim" else ""

        st.markdown("---")

        # ═══ SEÇÃO 9: CONSIDERAÇÕES FINAIS ═══
        st.markdown("### 9. Considerações Finais")
        f_cs_just = st.text_area("Justificativa do percentual (4-8 linhas)", value=h("curva_justificativa"), height=120, help="Explique como chegou ao percentual de avanço físico, com base em entregas concretas.")

        f_cf = st.text_area("Fechamento (1-2 parágrafos)", value=h("consideracoes_finais"), height=150, help="Evolução do trabalho, aderência ao cronograma, maturidade, expectativa para o próximo ciclo e contribuição à entrega final.")

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
