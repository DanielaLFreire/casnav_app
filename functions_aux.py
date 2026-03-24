# -*- coding: utf-8 -*-
"""
CASNAV DMarSup - Funcoes Auxiliares
Persistencia dual: GitHub API (Streamlit Cloud) + filesystem local (dev).
"""

import json
from datetime import datetime
from config import DATA_DIR, REL_DIR, mes_label_curto

# Tenta importar github_storage (pode nao existir em envs antigos)
try:
    import github_storage as gh
except ImportError:
    gh = None


# ═══════════════════════════════════════════════════
# LEITURA/ESCRITA — com fallback automatico
# ═══════════════════════════════════════════════════

def _use_github():
    """Retorna True se deve usar GitHub como backend."""
    return gh is not None and gh.is_enabled()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_projeto():
    if _use_github():
        d, _ = gh.read_json("data/projeto.json")
        if d is not None:
            return d
    return load_json(DATA_DIR / "projeto.json")


def load_bolsistas():
    if _use_github():
        d, _ = gh.read_json("data/bolsistas.json")
        if d is not None:
            return d
    return load_json(DATA_DIR / "bolsistas.json")


def save_bolsistas(data):
    # Salva local sempre
    save_json(DATA_DIR / "bolsistas.json", data)
    # Salva no GitHub se disponivel
    if _use_github():
        gh.write_json("data/bolsistas.json", data,
                       message="atualizar cadastro de bolsistas")


# ═══════════════════════════════════════════════════
# FORMULARIOS E RELATORIOS
# ═══════════════════════════════════════════════════

def _gh_relatorios_dir():
    return "data/relatorios"


def get_todos_formularios():
    forms = []

    if _use_github():
        try:
            files = gh.list_files(_gh_relatorios_dir())
            for f in sorted(files, key=lambda x: x["name"]):
                if f["name"].startswith("formulario_") and f["name"].endswith(".json"):
                    d, _ = gh.read_json(f["path"])
                    if d is not None:
                        forms.append(d)
            if forms:
                return forms
        except Exception:
            pass  # fallback para local

    # Fallback: leitura local
    for f in sorted(REL_DIR.glob("formulario_*.json")):
        forms.append(load_json(f))
    return forms


def get_todos_relatorios():
    rels = []

    if _use_github():
        try:
            files = gh.list_files(_gh_relatorios_dir())
            for f in sorted(files, key=lambda x: x["name"]):
                if f["name"].startswith("relatorio_") and f["name"].endswith(".json"):
                    d, _ = gh.read_json(f["path"])
                    if d is not None:
                        rels.append(d)
            if rels:
                return rels
        except Exception:
            pass

    for f in sorted(REL_DIR.glob("relatorio_*.json")):
        rels.append(load_json(f))
    return rels


def get_formularios_bolsista(bolsista_id):
    return [f for f in get_todos_formularios() if f.get("bolsista_id") == bolsista_id]


def get_ultimo_formulario(bolsista_id):
    forms = get_formularios_bolsista(bolsista_id)
    return forms[-1] if forms else None


def salvar_formulario(data):
    bid = data.get("bolsista_id", "unknown")
    mes = data.get("mes_execucao_num", "0")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = "formulario_%s_mes%s.json" % (bid, mes)
    data["_salvamento"] = ts
    data["_arquivo"] = fn

    # Salva local
    save_json(REL_DIR / fn, data)

    # Salva no GitHub
    if _use_github():
        gh_path = "%s/%s" % (_gh_relatorios_dir(), fn)
        gh.write_json(gh_path, data,
                       message="formulario %s mes %s" % (bid, mes))

    return fn


def salvar_relatorio(data):
    bid = data.get("bolsista_id", "unificado")
    mes = data.get("mes_referencia_num", "0")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = "relatorio_%s_mes%s_%s.json" % (bid, mes, ts)
    data["_salvamento"] = ts
    data["_arquivo"] = fn

    # Salva local
    save_json(REL_DIR / fn, data)

    # Salva no GitHub
    if _use_github():
        gh_path = "%s/%s" % (_gh_relatorios_dir(), fn)
        gh.write_json(gh_path, data,
                       message="relatorio %s mes %s" % (bid, mes))

    return fn


# ═══════════════════════════════════════════════════
# PRE-PREENCHIMENTO
# ═══════════════════════════════════════════════════

def calcular_atividades_do_periodo(bolsista, mes_num, proj):
    """Retorna atividades designadas ao bolsista que englobam o mes atual."""
    ativs_designadas = bolsista.get("atividades_designadas", [])
    if not ativs_designadas:
        return []
    resultado = []
    for ad in ativs_designadas:
        mi = ad.get("meses_inicio", 0)
        mf = ad.get("meses_fim", 0)
        if mi <= mes_num <= mf + 6:
            cod = ad["codigo"]
            for a in proj["atividades"]:
                if a["codigo"] == cod:
                    resultado.append(a)
                    break
    return resultado


def calcular_faixa_planejada(bolsista, mes_num):
    """Calcula a faixa planejada no cronograma."""
    ativs = bolsista.get("atividades_designadas", [])
    faixas = []
    for ad in ativs:
        mi = ad.get("meses_inicio", 0)
        mf = ad.get("meses_fim", 0)
        if mi <= mes_num <= mf + 6:
            faixas.append("meses %d-%d (%s a %s)" % (mi, mf, mes_label_curto(mi), mes_label_curto(mf)))
    return " / ".join(faixas) if faixas else ""


def prefill_gantt_inicio_plan(bolsista):
    """Pre-preenche inicio planejado do Gantt."""
    ativs = bolsista.get("atividades_designadas", [])
    partes = []
    for ad in ativs:
        cod = ad.get("codigo", "")
        mi = ad.get("meses_inicio", 0)
        partes.append("%s: Mes %d (%s)" % (cod, mi, mes_label_curto(mi)))
    return " | ".join(partes) if partes else ""


def prefill_gantt_termino_plan(bolsista):
    """Pre-preenche termino planejado do Gantt."""
    ativs = bolsista.get("atividades_designadas", [])
    partes = []
    for ad in ativs:
        cod = ad.get("codigo", "")
        mf = ad.get("meses_fim", 0)
        partes.append("%s: Mes %d (%s)" % (cod, mf, mes_label_curto(mf)))
    return " | ".join(partes) if partes else ""
