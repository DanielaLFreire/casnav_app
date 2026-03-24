"""
CASNAV DMarSup — Sistema de Acompanhamento de Atividades dos Bolsistas
Projeto Sistemas Marítimos Não Tripulados
Mês 1 do Projeto = Agosto/2025
"""


import json
from datetime import datetime
from config import DATA_DIR,  REL_DIR, mes_label_curto


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
    fn  = f"formulario_{bid}_mes{mes}.json"
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

