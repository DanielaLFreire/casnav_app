


from pathlib import Path
import streamlit as st
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

# ═══════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════
APP_DIR   = Path(__file__).parent
DATA_DIR  = APP_DIR / "data"
REL_DIR   = DATA_DIR / "relatorios"
REL_DIR.mkdir(parents=True, exist_ok=True)

DATA_INICIO_PROJETO = "2025-08-01"   # Mês 1 = Agosto/2025
MESES_PT = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

SITUACAO_OPTS = ["Não Iniciada", "Impedida", "Em andamento", "Concluída"]
EST_OPTS = ["planejamento", "preparação de dados", "implementação", "treinamento",
            "ajuste fino", "testes", "validação", "integração", "documentação", "outro"]



# ═══════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════
st.markdown("""
<style>
    
    .main-header h1 { margin: 0; font-size: 1.5rem; }
    .main-header p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.85rem; }
    .prefill-info { background: #e8f5e9; border-left: 4px solid #2e7d32;
        padding: 0.6rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.85rem; }
    .status-ok   { color: #2e7d32; font-weight: 600; }
    .status-pend { color: #e65100; font-weight: 600; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1b3e 0%, #1a237e 100%); }
    div[data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# FUNÇÕES UTILITÁRIAS
# ═══════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🚢 CASNAV DMarSup")
    st.markdown("**Visão Computacional**")
    st.markdown("---")
    hoje = date.today()
    mes_atual = data_para_mes(hoje)
    st.markdown(f"📅 **{mes_label(mes_atual)}**")
    st.markdown(f"**Hoje:** {hoje.strftime('%d/%m/%Y')}")
