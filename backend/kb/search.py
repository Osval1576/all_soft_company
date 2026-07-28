"""Retrieval simple sobre la KB publicada de una org (Fase 3B).

Scoring por solapamiento de palabras entre la consulta y el artículo (título con
más peso que el cuerpo). Sin vector store: las KB por tenant son chicas y esto
es barato, testeable y suficiente para la deflección. Si en el futuro crecen,
se puede cambiar por FULLTEXT de MySQL o embeddings sin tocar el resto.
"""
import re

from tenancy.scoping import org_kb

# Stopwords mínimas en español para reducir ruido del scoring.
_STOP = {
    "que", "los", "las", "por", "con", "para", "una", "uno", "del", "como",
    "mas", "muy", "sus", "este", "esta", "esto", "ese", "esa", "son", "sin",
    "porque", "cuando", "donde", "cual", "cuales", "hay", "puedo", "puede",
}


def _tokens(text):
    return {t for t in re.findall(r"\w+", (text or "").lower()) if len(t) > 2 and t not in _STOP}


def search_articles(org, query, limit=4):
    """Top-N artículos PUBLICADOS de la org más relevantes a la consulta.

    Devuelve una lista de Article (posiblemente vacía). Siempre scoped por org
    (aislamiento multi-tenant) y solo artículos publicados.
    """
    q_tokens = _tokens(query)
    if not q_tokens:
        return []
    scored = []
    for a in org_kb(org).filter(is_published=True):
        title_hits = len(q_tokens & _tokens(a.title))
        body_hits = len(q_tokens & _tokens(a.body))
        score = 2 * title_hits + body_hits
        if score > 0:
            scored.append((score, a))
    scored.sort(key=lambda x: (-x[0], -x[1].id))
    return [a for _, a in scored[:limit]]
