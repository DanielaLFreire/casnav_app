# -*- coding: utf-8 -*-
"""
CASNAV DMarSup - Persistencia via GitHub API
Salva/le JSONs diretamente no repositorio GitHub.
Compativel com Python 3.8+

Configuracao (em .streamlit/secrets.toml ou Streamlit Cloud Secrets):
    [github]
    token = "ghp_SEU_TOKEN_AQUI"
    repo = "usuario/nome-do-repo"
    branch = "master"
"""

import json
import base64
import requests

_CONFIG = None


def _get_config():
    """Carrega config do st.secrets (lazy, so importa streamlit quando precisar)."""
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    try:
        import streamlit as st
        gh = st.secrets.get("github", {})
        token = gh.get("token", "")
        repo = gh.get("repo", "")
        branch = gh.get("branch", "master")
        if token and repo:
            _CONFIG = {"token": token, "repo": repo, "branch": branch}
        else:
            _CONFIG = {}
    except Exception:
        _CONFIG = {}

    return _CONFIG


def is_enabled():
    """Retorna True se a persistencia GitHub esta configurada."""
    cfg = _get_config()
    return bool(cfg.get("token")) and bool(cfg.get("repo"))


def _headers():
    cfg = _get_config()
    return {
        "Authorization": "Bearer %s" % cfg["token"],
        "Accept": "application/vnd.github.v3+json",
    }


def _api_url(path):
    cfg = _get_config()
    return "https://api.github.com/repos/%s/contents/%s" % (cfg["repo"], path)


def list_files(directory):
    """Lista arquivos em um diretorio do repo. Retorna lista de dicts com 'name', 'path', 'sha'."""
    cfg = _get_config()
    if not cfg:
        return []

    url = _api_url(directory)
    params = {"ref": cfg["branch"]}
    resp = requests.get(url, headers=_headers(), params=params, timeout=15)

    if resp.status_code == 404:
        return []
    resp.raise_for_status()

    items = resp.json()
    if not isinstance(items, list):
        return []

    return [
        {"name": f["name"], "path": f["path"], "sha": f["sha"]}
        for f in items
        if f["type"] == "file"
    ]


def read_file(filepath):
    """Le o conteudo de um arquivo do repo. Retorna (conteudo_str, sha) ou (None, None)."""
    cfg = _get_config()
    if not cfg:
        return None, None

    url = _api_url(filepath)
    params = {"ref": cfg["branch"]}
    resp = requests.get(url, headers=_headers(), params=params, timeout=15)

    if resp.status_code == 404:
        return None, None
    resp.raise_for_status()

    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def read_json(filepath):
    """Le um arquivo JSON do repo. Retorna (dict, sha) ou (None, None)."""
    content, sha = read_file(filepath)
    if content is None:
        return None, None
    return json.loads(content), sha


def write_file(filepath, content_str, message="auto-save"):
    """Cria ou atualiza um arquivo no repo. Retorna True se sucesso."""
    cfg = _get_config()
    if not cfg:
        return False

    url = _api_url(filepath)
    encoded = base64.b64encode(content_str.encode("utf-8")).decode("ascii")

    # Verificar se arquivo ja existe (precisa do SHA para update)
    params = {"ref": cfg["branch"]}
    existing = requests.get(url, headers=_headers(), params=params, timeout=15)
    sha = None
    if existing.status_code == 200:
        sha = existing.json().get("sha")

    body = {
        "message": message,
        "content": encoded,
        "branch": cfg["branch"],
    }
    if sha:
        body["sha"] = sha

    resp = requests.put(url, headers=_headers(), json=body, timeout=30)
    return resp.status_code in (200, 201)


def write_json(filepath, data_dict, message="auto-save"):
    """Salva um dict como JSON no repo."""
    content = json.dumps(data_dict, ensure_ascii=False, indent=2)
    return write_file(filepath, content, message)


def delete_file(filepath, message="auto-delete"):
    """Deleta um arquivo do repo. Retorna True se sucesso."""
    cfg = _get_config()
    if not cfg:
        return False

    url = _api_url(filepath)
    params = {"ref": cfg["branch"]}
    existing = requests.get(url, headers=_headers(), params=params, timeout=15)
    if existing.status_code != 200:
        return False

    sha = existing.json()["sha"]
    body = {
        "message": message,
        "sha": sha,
        "branch": cfg["branch"],
    }
    resp = requests.delete(url, headers=_headers(), json=body, timeout=30)
    return resp.status_code == 200
