"""
CASNAV DMarSup — Sistema de Acompanhamento de Atividades dos Bolsistas
Projeto Sistemas Marítimos Não Tripulados
Mês 1 do Projeto = Agosto/2025
"""

import streamlit as st
import json, os, re
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ═══════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════
APP_DIR   = Path(__file__).parent
DATA_DIR  = APP_DIR / "data"
REL_DIR   = DATA_DIR / "relatorios"
REL_DIR.mkdir(parents=True, exist_ok=True)

DATA_INICIO_PROJETO = "2025-08-01"   # Mês 1 = Agosto/2025
MESES_PT = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

st.set_page_config(page_title="CASNAV DMarSup", page_icon="🚢", layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════════
# FUNÇÕES UTILITÁRIAS
# ═══════════════════════════════════════════════════

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_projeto():
    return load_json(DATA_DIR / "projeto.json")

def load_bolsistas():
    return load_json(DATA_DIR / "bolsistas.json")

def save_bolsistas(data):
    save_json(DATA_DIR / "bolsistas.json", data)

def mes_para_data(mes_num: int) -> date:
    d0 = datetime.strptime(DATA_INICIO_PROJETO, "%Y-%m-%d").date()
    return d0 + relativedelta(months=mes_num - 1)

def data_para_mes(dt: date) -> int:
    d0 = datetime.strptime(DATA_INICIO_PROJETO, "%Y-%m-%d").date()
    return (dt.year - d0.year) * 12 + (dt.month - d0.month) + 1

def mes_label(m: int) -> str:
    dt = mes_para_data(m)
    return f"Mês {m} — {MESES_PT[dt.month-1]}/{dt.year}"

def mes_label_curto(m: int) -> str:
    dt = mes_para_data(m)
    return f"{MESES_PT[dt.month-1]}/{dt.year}"

def periodo_referencia_auto(mes_num: int) -> str:
    dt = mes_para_data(mes_num)
    primeiro = dt.replace(day=1)
    ultimo = (primeiro + relativedelta(months=1)) - timedelta(days=1)
    return f"{primeiro.strftime('%d/%m/%Y')} a {ultimo.strftime('%d/%m/%Y')}"

# ── Persistência ──

def get_todos_formularios() -> list:
    forms = []
    for f in sorted(REL_DIR.glob("formulario_*.json")):
        forms.append(load_json(f))
    return forms

def get_todos_relatorios() -> list:
    rels = []
    for f in sorted(REL_DIR.glob("relatorio_*.json")):
        rels.append(load_json(f))
    return rels

def get_formularios_bolsista(bolsista_id: str) -> list:
    return [f for f in get_todos_formularios() if f.get("bolsista_id") == bolsista_id]

def get_ultimo_formulario(bolsista_id: str):
    forms = get_formularios_bolsista(bolsista_id)
    return forms[-1] if forms else None

def salvar_formulario(data: dict) -> str:
    bid = data.get("bolsista_id", "unknown")
    mes = data.get("mes_execucao_num", "0")
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn  = f"formulario_{bid}_mes{mes}_{ts}.json"
    data["_salvamento"] = ts
    data["_arquivo"] = fn
    save_json(REL_DIR / fn, data)
    return fn

def salvar_relatorio(data: dict) -> str:
    bid = data.get("bolsista_id", "unificado")
    mes = data.get("mes_referencia_num", "0")
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn  = f"relatorio_{bid}_mes{mes}_{ts}.json"
    data["_salvamento"] = ts
    data["_arquivo"] = fn
    save_json(REL_DIR / fn, data)
    return fn

# ── Pré-preenchimento ──

def calcular_atividades_do_periodo(bolsista: dict, mes_num: int, proj: dict) -> list:
    """Retorna atividades designadas ao bolsista que englobam o mês atual."""
    ativs_designadas = bolsista.get("atividades_designadas", [])
    if not ativs_designadas:
        return []
    resultado = []
    for ad in ativs_designadas:
        mi = ad.get("meses_inicio", 0)
        mf = ad.get("meses_fim", 0)
        # Atividade abrange o mês ou já foi deslocada
        if mi <= mes_num <= mf + 6:  # Margem de 6 meses para desvios
            cod = ad["codigo"]
            # Busca dados completos da atividade no projeto
            for a in proj["atividades"]:
                if a["codigo"] == cod:
                    resultado.append(a)
                    break
    return resultado

def calcular_faixa_planejada(bolsista: dict, mes_num: int) -> str:
    """Calcula a faixa planejada no cronograma com base nas atividades designadas."""
    ativs = bolsista.get("atividades_designadas", [])
    faixas = []
    for ad in ativs:
        mi = ad.get("meses_inicio", 0)
        mf = ad.get("meses_fim", 0)
        if mi <= mes_num <= mf + 6:
            faixas.append(f"meses {mi}–{mf} ({mes_label_curto(mi)} a {mes_label_curto(mf)})")
    return " / ".join(faixas) if faixas else ""

def prefill_gantt_inicio_plan(bolsista: dict) -> str:
    """Pré-preenche início planejado do Gantt."""
    partes = []
    for ad in bolsista.get("atividades_designadas", []):
        mi = ad.get("meses_inicio", 0)
        if mi:
            partes.append(f"{ad['codigo']}: Mês {mi} — {mes_label_curto(mi)}")
    return " | ".join(partes)

def prefill_gantt_termino_plan(bolsista: dict) -> str:
    partes = []
    for ad in bolsista.get("atividades_designadas", []):
        mf = ad.get("meses_fim", 0)
        if mf:
            partes.append(f"{ad['codigo']}: Mês {mf} — {mes_label_curto(mf)}")
    return " | ".join(partes)


# ═══════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════
st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #3949ab 100%);
        padding: 1.5rem 2rem; border-radius: 12px; color: white; margin-bottom: 1.5rem; }
    .main-header h1 { margin: 0; font-size: 1.5rem; }
    .main-header p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.85rem; }
    .prefill-info { background: #e8f5e9; border-left: 4px solid #2e7d32;
        padding: 0.6rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.85rem; }
    .hist-card { background: #f5f5f5; border-left: 4px solid #1565c0;
        padding: 0.8rem 1rem; border-radius: 8px; margin-bottom: 0.5rem; }
    .status-ok   { color: #2e7d32; font-weight: 600; }
    .status-pend { color: #e65100; font-weight: 600; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1b3e 0%, #1a237e 100%); }
    div[data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🚢 CASNAV DMarSup")
    st.markdown("**Visão Computacional**")
    st.markdown("---")
    pagina = st.radio("Navegação", [
        "📊 Dashboard",
        "📝 Formulário do Bolsista",
        "📄 Gerar Relatório",
        "📑 Relatório Unificado",
        "📈 Gantt & Cronograma",
        "📉 Curva S",
        "👥 Gestão de Bolsistas",
        "📁 Histórico do Gerente",
    ], label_visibility="collapsed")
    st.markdown("---")
    hoje = date.today()
    mes_atual = data_para_mes(hoje)
    st.markdown(f"📅 **{mes_label(mes_atual)}**")
    st.markdown(f"**Hoje:** {hoje.strftime('%d/%m/%Y')}")


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
        <h1>🚢 CASNAV DMarSup — Painel de Acompanhamento</h1>
        <p>Projeto Sistemas Marítimos Não Tripulados | Visão Computacional</p>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mês do Projeto", f"{mes_atual}/36")
    c2.metric("Bolsistas", len(bolsistas))
    c3.metric("Formulários", len(formularios))
    c4.metric("Relatórios", len(relatorios))

    st.markdown("---")

    # Gantt
    st.subheader("📅 Cronograma Macro")
    gantt_rows = []
    for a in proj["atividades"]:
        d_i = mes_para_data(a["meses_inicio"])
        d_f = mes_para_data(a["meses_fim"]) + relativedelta(months=1) - timedelta(days=1)
        status = "Em andamento" if a["meses_inicio"] <= mes_atual <= a["meses_fim"] \
                 else ("Não iniciada" if mes_atual < a["meses_inicio"] else "Janela encerrada")
        gantt_rows.append({"Atividade": f"{a['codigo']} {a['nome']}", "Início": d_i, "Fim": d_f, "Status": status})
    df = pd.DataFrame(gantt_rows)
    fig = px.timeline(df, x_start="Início", x_end="Fim", y="Atividade", color="Status",
        color_discrete_map={"Não iniciada":"#bdbdbd","Em andamento":"#1565c0","Janela encerrada":"#66bb6a"})
    fig.update_yaxes(autorange="reversed")
    fig.add_vline(x=str(hoje), line_dash="dash", line_color="red")
    fig.add_annotation(x=str(hoje), y=1, yref="paper", text="Hoje", showarrow=False,
        font=dict(color="red", size=11), yshift=10)
    fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Bolsistas
    st.subheader("👥 Bolsistas")
    rows = []
    for b in bolsistas:
        ativs = ", ".join(a["codigo"] for a in b.get("atividades_designadas", [])) or "A definir"
        termo = b.get("numero_termo", "") or "—"
        rows.append({"Nome": b["nome"], "Termo": termo, "Formação": b.get("formacao","") or "—",
                      "Início Bolsa": b.get("data_inicio_bolsa",""), "Atividades": ativs})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
#  FORMULÁRIO DO BOLSISTA  (com pré-preenchimento)
# ═══════════════════════════════════════════════════
def page_formulario():
    proj  = load_projeto()
    bdata = load_bolsistas()
    bolsistas = bdata["bolsistas"]
    atividades = proj["atividades"]

    st.markdown("""<div class="main-header">
        <h1>📝 Formulário de Atividades do Bolsista</h1>
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

    # Info de pré-preenchimento
    pre_info = []
    pre_info.append(f"**Nome, coordenador, termo, data** ← cadastro do bolsista")
    pre_info.append(f"**Mês {mes_ref}** = {mes_label_curto(mes_ref)}, período = {periodo_referencia_auto(mes_ref)}")
    if ativs_default:
        pre_info.append(f"**Atividades sugeridas:** {', '.join(ativs_default)}")
    if ultimo:
        pre_info.append(f"**Último formulário encontrado** ({ultimo.get('_salvamento','')}) — dados herdados como ponto de partida")
    st.markdown('<div class="prefill-info">' + "<br>".join(pre_info) + '</div>', unsafe_allow_html=True)

    # Helper para herdar valor
    def h(key, fallback=""):
        """Herda valor do último formulário ou retorna fallback."""
        if ultimo:
            return ultimo.get(key, fallback)
        return fallback

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

        # ═══ SEÇÃO 4: ATIVIDADES DESIGNADAS (abas dinâmicas) ═══
        st.markdown("### 4. Atividades Designadas")
        ativs_desig = bolsista.get("atividades_designadas", [])

        if not ativs_desig:
            st.warning("⚠️ Nenhuma atividade designada para este bolsista. Configure em 👥 Gestão de Bolsistas.")
        else:
            # Buscar dados completos de cada atividade
            ativs_info = []
            for ad in ativs_desig:
                cod = ad["codigo"]
                info = {"codigo": cod, "nome": cod, "periodicidade": ad.get("periodicidade",""),
                        "meses_inicio": ad.get("meses_inicio",0), "meses_fim": ad.get("meses_fim",0)}
                for a in proj["atividades"]:
                    if a["codigo"] == cod:
                        info["nome"] = f"{cod} {a['nome']}"
                        info["descricao_projeto"] = a.get("descricao","")
                        info["entregas_projeto"] = a.get("entregas","")
                        break
                ativs_info.append(info)

            # Herdar dados de atividades do último formulário
            def ha(idx, campo, fallback=""):
                """Herda campo da atividade idx do último formulário."""
                if ultimo and "atividades" in ultimo:
                    ativs_ant = ultimo["atividades"]
                    if idx < len(ativs_ant):
                        return ativs_ant[idx].get(campo, fallback)
                return fallback

            tab_labels = [ai["nome"] for ai in ativs_info]
            tabs = st.tabs(tab_labels)

            SITUACAO_OPTS = ["Não Iniciada", "Impedida", "Em andamento", "Concluída"]
            EST_OPTS = ["planejamento","preparação de dados","implementação","treinamento",
                        "ajuste fino","testes","validação","integração","documentação","outro"]

            ativs_form = []  # lista que será salva no JSON

            for idx, (tab, ai) in enumerate(zip(tabs, ativs_info)):
                with tab:
                    k = f"a{idx}_"  # prefixo de key único por aba

                    # Situação (campo principal)
                    sit_ant = ha(idx, "situacao", "Não Iniciada")
                    sit_idx = SITUACAO_OPTS.index(sit_ant) if sit_ant in SITUACAO_OPTS else 0
                    situacao = st.selectbox(
                        "🔹 Situação da atividade", SITUACAO_OPTS, index=sit_idx, key=k+"sit"
                    )

                    # Cabeçalho informativo
                    st.caption(f"📅 Cronograma: {ai.get('periodicidade','')} | "
                               f"Entrega prevista: {ai.get('entregas_projeto','—')}")

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
                        a_data["obs_gantt"] = st.text_area(
                            "Observação para Gantt", value=ha(idx,"obs_gantt"), height=68, key=k+"ogantt")
                        a_data["obs_curvas"] = st.text_area(
                            "Observação para Curva S", value=ha(idx,"obs_curvas"), height=68, key=k+"ocurva")

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

        # ═══ SEÇÃO 9: GANTT (pré-preenchido com datas do cronograma) ═══
        st.markdown("### 9. Campos para Gantt")
        st.caption("ℹ️ Início e término planejados pré-preenchidos com base nas atividades designadas ao bolsista.")
        c1, c2 = st.columns(2)
        with c1:
            f_g_at  = st.text_input("Atividade", value=h("gantt_atividade", " / ".join(a["nome"] for a in ativs_periodo)))
            f_g_st  = st.selectbox("Status", ["não iniciada","em andamento","concluída","concluída parcialmente","atrasada","suspensa"], key="gs")
            f_g_ip  = st.text_input("Início planejado", value=h("gantt_inicio_plan", prefill_gantt_inicio_plan(bolsista)))
            f_g_tp  = st.text_input("Término planejado", value=h("gantt_termino_plan", prefill_gantt_termino_plan(bolsista)))
        with c2:
            f_g_cod = st.text_input("Código", value=h("gantt_codigo", " / ".join(a["codigo"] for a in ativs_periodo)))
            f_g_dt  = st.selectbox("Tipo desvio", ["sem desvio","atraso","adiantamento","replanejamento"], key="gdt")
            f_g_ir  = st.text_input("Início real", value=h("gantt_inicio_real"))
            f_g_ta  = st.text_input("Término atualizado", value=h("gantt_termino_atual"))
        f_g_imp = st.selectbox("Impacto no cronograma", ["baixo","médio","alto"], key="gi")
        f_g_dep = st.text_input("Dependências", value=h("gantt_dependencias"))
        f_g_mar = st.text_input("Marco principal", value=h("gantt_marco"), key="g_marco")
        f_g_com = st.text_area("Comentário Gantt", value=h("gantt_comentario"), height=68)

        st.markdown("---")

        # ═══ SEÇÃO 10: CURVA S ═══
        st.markdown("### 10. Campos para Curva S")
        f_cs_conc = st.text_area("Entregas concluídas no período", value=h("curva_concluidas"), height=68)
        f_cs_parc = st.text_area("Entregas parcialmente executadas", value=h("curva_parciais"), height=68)
        c1, c2 = st.columns(2)
        with c1:
            f_cs_pp = st.slider("% avanço físico no período", 0, 100, int(h("curva_pct_periodo", 0)))
        with c2:
            # Se há último formulário, o acumulado anterior é o ponto de partida
            pct_acum_anterior = int(h("curva_pct_acum", 0))
            f_cs_pa = st.slider("% avanço físico acumulado", 0, 100, pct_acum_anterior)
        f_cs_just = st.text_area("Justificativa do percentual (4-8 linhas)", value=h("curva_justificativa"), height=120)
        f_cs_cont = st.text_area("Atividades que mais contribuíram", value=h("curva_contribuiram"), height=68)
        f_cs_risk = st.text_area("Riscos para evolução futura", value=h("curva_riscos"), height=68)
        f_cs_acel = st.text_area("Fatores aceleradores", value=h("curva_aceleradores"), height=68)

        st.markdown("---")

        # ═══ SEÇÃO 11: DIFICULDADES ═══
        st.markdown("### 11. Dificuldades e Suporte")
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

        # ═══ SEÇÃO 12: CONSIDERAÇÕES FINAIS ═══
        st.markdown("### 12. Considerações Finais")
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
                "gantt_atividade": f_g_at, "gantt_codigo": f_g_cod,
                "gantt_status": f_g_st, "gantt_inicio_plan": f_g_ip,
                "gantt_inicio_real": f_g_ir, "gantt_termino_plan": f_g_tp,
                "gantt_termino_atual": f_g_ta, "gantt_desvio_tipo": f_g_dt,
                "gantt_impacto": f_g_imp, "gantt_dependencias": f_g_dep,
                "gantt_marco": f_g_mar, "gantt_comentario": f_g_com,
                "curva_concluidas": f_cs_conc, "curva_parciais": f_cs_parc,
                "curva_pct_periodo": f_cs_pp, "curva_pct_acum": f_cs_pa,
                "curva_justificativa": f_cs_just, "curva_contribuiram": f_cs_cont,
                "curva_riscos": f_cs_risk, "curva_aceleradores": f_cs_acel,
                "dif_tecnicas": f_dt, "dif_tecnicas_quais": f_dtq,
                "dif_ajuste": f_da, "dif_apoio": f_dap,
                "dif_infra": f_di, "dif_infra_detalhe": f_did,
                "consideracoes_finais": f_cf,
            }
            fn = salvar_formulario(form_data)
            st.success(f"✅ Formulário salvo: **{fn}**")


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
**{a.get('nome', a.get('codigo','—'))}** — ✅ Concluída
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
**{a.get('nome', a.get('codigo','—'))}** — 🔵 Em andamento
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
**{a.get('nome', a.get('codigo','—'))}** — 🔴 Impedida
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
        "bolsista_id": form.get("bolsista_id",""), "bolsista_nome": nome,
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

    if "rel_ind" in st.session_state:
        rel = st.session_state["rel_ind"]
        t1, t2, t3, t4 = st.tabs(["📝 Técnico", "📊 Gantt", "📉 Curva S", "📋 Resumo"])
        with t1: st.markdown(rel["bloco1_tecnico"])
        with t2: st.markdown(rel["bloco2_gantt"])
        with t3: st.markdown(rel["bloco3_curva_s"])
        with t4: st.markdown(rel["bloco4_resumo"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Salvar"):
                fn = salvar_relatorio(rel)
                st.success(f"✅ Salvo: {fn}")
        with col2:
            full = "\n---\n".join([rel["bloco1_tecnico"], rel["bloco2_gantt"], rel["bloco3_curva_s"], rel["bloco4_resumo"]])
            st.download_button("📥 Baixar (.md)", full, file_name=f"relatorio_{rel.get('bolsista_id','x')}.md")


# ═══════════════════════════════════════════════════
#  RELATÓRIO UNIFICADO
# ═══════════════════════════════════════════════════
def page_unificado():
    proj  = load_projeto()
    bdata = load_bolsistas()
    st.markdown("""<div class="main-header">
        <h1>📑 Relatório Unificado</h1>
        <p>Consolida relatórios de todos os bolsistas por período.</p>
    </div>""", unsafe_allow_html=True)

    formularios = get_todos_formularios()
    if not formularios:
        st.warning("Nenhum formulário salvo.")
        return

    meses = sorted(set(str(f.get("mes_execucao_num","?")) for f in formularios))
    mes_sel = st.selectbox("Mês de referência", meses)
    forms_mes = [f for f in formularios if str(f.get("mes_execucao_num","?")) == mes_sel]

    # Status de preenchimento
    nomes_ok  = set(f.get("bolsista_nome","?") for f in forms_mes)
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

    if "unificado" in st.session_state:
        st.markdown(st.session_state["unificado"])
        st.download_button("📥 Baixar Unificado (.md)", st.session_state["unificado"],
                          file_name=f"unificado_mes{mes_sel}.md")


# ═══════════════════════════════════════════════════
#  GANTT
# ═══════════════════════════════════════════════════
def page_gantt():
    proj = load_projeto()
    st.markdown("""<div class="main-header">
        <h1>📈 Gantt — Cronograma do Projeto</h1>
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
        <h1>📉 Curva S — Avanço Físico</h1>
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


# ═══════════════════════════════════════════════════
#  GESTÃO DE BOLSISTAS (com numero_termo por bolsista)
# ═══════════════════════════════════════════════════
def page_bolsistas():
    bdata = load_bolsistas()
    proj  = load_projeto()
    st.markdown("""<div class="main-header">
        <h1>👥 Gestão de Bolsistas</h1>
        <p>Cadastro, termo de bolsa e atividades designadas. Nº do Termo é atributo do bolsista.</p>
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
                    b["formacao"]          = st.text_input("Formação", value=b.get("formacao",""), key=f"bf{i}")
                with c2:
                    b["data_inicio_bolsa"] = st.text_input("Início da bolsa", value=b.get("data_inicio_bolsa",""), key=f"bd{i}")
                    b["valor_mensal"]      = st.number_input("Valor (R$)", value=float(b.get("valor_mensal",0)), key=f"bv{i}")
                    b["prazo_meses"]       = st.number_input("Prazo (meses)", value=int(b.get("prazo_meses",0)), key=f"bp{i}")
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


# ═══════════════════════════════════════════════════
#  HISTÓRICO DO GERENTE (nova página completa)
# ═══════════════════════════════════════════════════
def page_historico():
    bdata = load_bolsistas()
    proj  = load_projeto()

    st.markdown("""<div class="main-header">
        <h1>📁 Histórico — Visão do Gerente</h1>
        <p>Timeline de todos os formulários e relatórios. Compare períodos, acompanhe evolução e identifique pendências.</p>
    </div>""", unsafe_allow_html=True)

    formularios = get_todos_formularios()
    relatorios  = get_todos_relatorios()

    # ── ABA 1: Painel de Status por Período ──
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Status por Período", "🕐 Timeline", "📈 Evolução", "📄 Detalhes"])

    with tab1:
        st.subheader("Quem preencheu em cada mês?")
        if not formularios:
            st.info("Nenhum formulário salvo ainda.")
        else:
            # Montar matriz mês × bolsista
            todos_nomes = sorted(b["nome"] for b in bdata["bolsistas"])
            meses_com_dados = sorted(set(f.get("mes_execucao_num", 0) for f in formularios if f.get("mes_execucao_num")))

            matrix = {}
            for m in meses_com_dados:
                matrix[m] = {}
                forms_m = [f for f in formularios if f.get("mes_execucao_num") == m]
                nomes_m = set(f.get("bolsista_nome","?") for f in forms_m)
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
                mes  = f.get("mes_execucao", f.get("mes_execucao_num", "?"))
                ts   = f.get("_salvamento", "")
                pct  = f.get("curva_pct_acum", "—")
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
                with st.expander(f"{r.get('bolsista_nome', r.get('tipo','?'))} — {r.get('periodo','?')}"):
                    if "bloco1_tecnico" in r:
                        st.markdown(r["bloco1_tecnico"][:800] + "...")
                    st.json(r)


# ═══════════════════════════════════════════════════
# ROTEAMENTO
# ═══════════════════════════════════════════════════
if   pagina == "📊 Dashboard":           page_dashboard()
elif pagina == "📝 Formulário do Bolsista": page_formulario()
elif pagina == "📄 Gerar Relatório":      page_relatorio()
elif pagina == "📑 Relatório Unificado":  page_unificado()
elif pagina == "📈 Gantt & Cronograma":   page_gantt()
elif pagina == "📉 Curva S":             page_curva_s()
elif pagina == "👥 Gestão de Bolsistas":  page_bolsistas()
elif pagina == "📁 Histórico do Gerente": page_historico()
