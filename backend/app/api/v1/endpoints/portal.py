"""
Portal endpoints — KPIs configurables, vínculos, menú dinámico y proxy de noticias RSS.
"""
from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import CurrentUser, DBSession
from app.api.v1.endpoints.admin import _get_engine_for_slug

router = APIRouter()

# ── RSS cache ─────────────────────────────────────────────────────────────────
_rss_cache: dict[str, object] = {}   # {url: {"ts": float, "items": list}}
_RSS_TTL = 900  # 15 minutos


# ── Schemas ───────────────────────────────────────────────────────────────────

class KpiIn(BaseModel):
    id_sistema: Optional[int] = None
    titulo: str
    icono: str = "ti-chart-bar"
    color: str = "teal"
    query_sql: str
    formato: str = "number"
    decimales: int = 0
    prefijo: str = ""
    sufijo: str = ""
    orden: int = 0
    es_activo: bool = True


class KpiOut(KpiIn):
    id: int

    class Config:
        from_attributes = True


class KpiPatch(BaseModel):
    titulo: Optional[str] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    query_sql: Optional[str] = None
    formato: Optional[str] = None
    decimales: Optional[int] = None
    prefijo: Optional[str] = None
    sufijo: Optional[str] = None
    orden: Optional[int] = None
    es_activo: Optional[bool] = None


class VinculoIn(BaseModel):
    id_sistema: Optional[int] = None
    titulo: str
    url: str
    icono: str = "ti-external-link"
    descripcion: Optional[str] = None
    orden: int = 0
    es_activo: bool = True


class VinculoOut(VinculoIn):
    id: int

    class Config:
        from_attributes = True


class VinculoPatch(BaseModel):
    titulo: Optional[str] = None
    url: Optional[str] = None
    icono: Optional[str] = None
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    es_activo: Optional[bool] = None


# ── KPIs ──────────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=list[KpiOut])
async def list_kpis(
    db: DBSession,
    _: CurrentUser,
    sistema_id: Optional[int] = Query(None),
):
    q = "SELECT id, id_sistema, titulo, icono, color, query_sql, formato, decimales, prefijo, sufijo, orden, es_activo FROM portal_kpis"
    params: dict = {}
    if sistema_id is not None:
        q += " WHERE id_sistema = :sid"
        params["sid"] = sistema_id
    q += " ORDER BY orden, id"
    result = await db.execute(text(q), params)
    rows = result.fetchall()
    return [dict(r._mapping) for r in rows]


@router.post("/kpis", response_model=KpiOut, status_code=201)
async def create_kpi(body: KpiIn, db: DBSession, _: CurrentUser):
    result = await db.execute(
        text("""
            INSERT INTO portal_kpis
                (id_sistema, titulo, icono, color, query_sql, formato, decimales, prefijo, sufijo, orden, es_activo)
            VALUES
                (:id_sistema, :titulo, :icono, :color, :query_sql, :formato, :decimales, :prefijo, :sufijo, :orden, :es_activo)
            RETURNING id, id_sistema, titulo, icono, color, query_sql, formato, decimales, prefijo, sufijo, orden, es_activo
        """),
        body.model_dump(),
    )
    await db.commit()
    return dict(result.fetchone()._mapping)


@router.patch("/kpis/{kpi_id}", response_model=KpiOut)
async def update_kpi(kpi_id: int, body: KpiPatch, db: DBSession, _: CurrentUser):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "Sin campos para actualizar")
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["kpi_id"] = kpi_id
    result = await db.execute(
        text(f"""
            UPDATE portal_kpis SET {sets}, updated_at = NOW()
            WHERE id = :kpi_id
            RETURNING id, id_sistema, titulo, icono, color, query_sql, formato, decimales, prefijo, sufijo, orden, es_activo
        """),
        fields,
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "KPI no encontrado")
    await db.commit()
    return dict(row._mapping)


@router.delete("/kpis/{kpi_id}", status_code=204)
async def delete_kpi(kpi_id: int, db: DBSession, _: CurrentUser):
    result = await db.execute(text("DELETE FROM portal_kpis WHERE id = :id"), {"id": kpi_id})
    if result.rowcount == 0:
        raise HTTPException(404, "KPI no encontrado")
    await db.commit()


@router.post("/kpis/{kpi_id}/run")
async def run_kpi(
    kpi_id: int,
    db: DBSession,
    _: CurrentUser,
    db_slug: Optional[str] = Query(None),
):
    """Ejecuta el query_sql del KPI. Solo permite SELECT."""
    result = await db.execute(
        text("SELECT query_sql FROM portal_kpis WHERE id = :id"),
        {"id": kpi_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "KPI no encontrado")

    sql = row[0].strip()
    if not sql.upper().startswith("SELECT"):
        raise HTTPException(400, "Solo se permiten consultas SELECT")

    eng = await _get_engine_for_slug(db_slug)
    async with eng.connect() as conn:
        res = await conn.execute(text(sql))
        first = res.fetchone()
        value = first[0] if first else None

    return {"value": value}


# ── Vínculos ──────────────────────────────────────────────────────────────────

@router.get("/vinculos", response_model=list[VinculoOut])
async def list_vinculos(
    db: DBSession,
    _: CurrentUser,
    sistema_id: Optional[int] = Query(None),
):
    q = "SELECT id, id_sistema, titulo, url, icono, descripcion, orden, es_activo FROM portal_vinculos"
    params: dict = {}
    if sistema_id is not None:
        q += " WHERE id_sistema = :sid"
        params["sid"] = sistema_id
    q += " ORDER BY orden, id"
    result = await db.execute(text(q), params)
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/vinculos", response_model=VinculoOut, status_code=201)
async def create_vinculo(body: VinculoIn, db: DBSession, _: CurrentUser):
    result = await db.execute(
        text("""
            INSERT INTO portal_vinculos
                (id_sistema, titulo, url, icono, descripcion, orden, es_activo)
            VALUES
                (:id_sistema, :titulo, :url, :icono, :descripcion, :orden, :es_activo)
            RETURNING id, id_sistema, titulo, url, icono, descripcion, orden, es_activo
        """),
        body.model_dump(),
    )
    await db.commit()
    return dict(result.fetchone()._mapping)


@router.patch("/vinculos/{vinculo_id}", response_model=VinculoOut)
async def update_vinculo(vinculo_id: int, body: VinculoPatch, db: DBSession, _: CurrentUser):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "Sin campos para actualizar")
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["vid"] = vinculo_id
    result = await db.execute(
        text(f"""
            UPDATE portal_vinculos SET {sets}, updated_at = NOW()
            WHERE id = :vid
            RETURNING id, id_sistema, titulo, url, icono, descripcion, orden, es_activo
        """),
        fields,
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Vínculo no encontrado")
    await db.commit()
    return dict(row._mapping)


@router.delete("/vinculos/{vinculo_id}", status_code=204)
async def delete_vinculo(vinculo_id: int, db: DBSession, _: CurrentUser):
    result = await db.execute(
        text("DELETE FROM portal_vinculos WHERE id = :id"), {"id": vinculo_id}
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Vínculo no encontrado")
    await db.commit()


# ── Menú dinámico ────────────────────────────────────────────────────────────

class MenuItemIn(BaseModel):
    id_sistema: int
    titulo: str
    orden: int = 0
    descripcion: Optional[str] = None
    tabla: Optional[str] = None
    url: Optional[str] = None
    icono: str = "ti-table"
    es_activo: bool = True


class MenuItemOut(MenuItemIn):
    id: int

    class Config:
        from_attributes = True


class MenuItemPatch(BaseModel):
    titulo: Optional[str] = None
    orden: Optional[int] = None
    descripcion: Optional[str] = None
    tabla: Optional[str] = None
    url: Optional[str] = None
    icono: Optional[str] = None
    es_activo: Optional[bool] = None


@router.get("/menu", response_model=list[MenuItemOut])
async def list_menu(
    db: DBSession,
    _: CurrentUser,
    sistema_id: int = Query(...),
):
    result = await db.execute(
        text("""
            SELECT id, id_sistema, titulo, orden, descripcion, tabla, url, icono, es_activo
            FROM portal_menu
            WHERE id_sistema = :sid
            ORDER BY orden, id
        """),
        {"sid": sistema_id},
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/menu", response_model=MenuItemOut, status_code=201)
async def create_menu_item(body: MenuItemIn, db: DBSession, _: CurrentUser):
    result = await db.execute(
        text("""
            INSERT INTO portal_menu
                (id_sistema, titulo, orden, descripcion, tabla, url, icono, es_activo)
            VALUES
                (:id_sistema, :titulo, :orden, :descripcion, :tabla, :url, :icono, :es_activo)
            RETURNING id, id_sistema, titulo, orden, descripcion, tabla, url, icono, es_activo
        """),
        body.model_dump(),
    )
    await db.commit()
    return dict(result.fetchone()._mapping)


@router.patch("/menu/{item_id}", response_model=MenuItemOut)
async def update_menu_item(item_id: int, body: MenuItemPatch, db: DBSession, _: CurrentUser):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "Sin campos para actualizar")
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["item_id"] = item_id
    result = await db.execute(
        text(f"""
            UPDATE portal_menu SET {sets}, updated_at = NOW()
            WHERE id = :item_id
            RETURNING id, id_sistema, titulo, orden, descripcion, tabla, url, icono, es_activo
        """),
        fields,
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Ítem de menú no encontrado")
    await db.commit()
    return dict(row._mapping)


@router.delete("/menu/{item_id}", status_code=204)
async def delete_menu_item(item_id: int, db: DBSession, _: CurrentUser):
    result = await db.execute(
        text("DELETE FROM portal_menu WHERE id = :id"), {"id": item_id}
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Ítem de menú no encontrado")
    await db.commit()


# ── Noticias RSS ──────────────────────────────────────────────────────────────

_RSS_FEEDS = [
    ("Paraguay",       "https://news.google.com/rss/search?q=paraguay&hl=es-419&gl=PY&ceid=PY:es-419"),
    ("Economía",       "https://news.google.com/rss/search?q=economia+finanzas+paraguay&hl=es-419&gl=PY&ceid=PY:es-419"),
    ("Deportes",       "https://news.google.com/rss/search?q=deportes+futbol+paraguay&hl=es-419&gl=PY&ceid=PY:es-419"),
    ("Finanzas",       "https://news.google.com/rss/search?q=mercados+bolsa+finanzas+internacionales&hl=es-419&gl=US&ceid=US:es-419"),
    ("Mundo",          "https://news.google.com/rss/search?q=noticias+internacionales+urgente&hl=es-419&gl=US&ceid=US:es-419"),
    ("Tecnología",     "https://news.google.com/rss/search?q=tecnologia+inteligencia+artificial&hl=es-419&gl=US&ceid=US:es-419"),
]

_RSS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


async def _fetch_rss(url: str) -> list[dict]:
    """Fetch and cache a single RSS feed. Returns all items (no limit)."""
    now = time.time()
    cached = _rss_cache.get(url)
    if cached and (now - cached["ts"]) < _RSS_TTL:  # type: ignore[index]
        return cached["items"]  # type: ignore[index]

    async with httpx.AsyncClient(timeout=10, headers=_RSS_HEADERS) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"media": "http://search.yahoo.com/mrss/"}
    items = []
    for item in root.iter("item"):
        title   = (item.findtext("title") or "").strip()
        link    = (item.findtext("link")  or "").strip()
        pub     = (item.findtext("pubDate") or "").strip()
        desc    = (item.findtext("description") or "").strip()
        # Google News provides original publisher in <source>
        src_el  = item.find("source")
        publisher = src_el.text.strip() if src_el is not None and src_el.text else None
        thumb_el = item.find("media:thumbnail", ns)
        enc_el   = item.find("enclosure")
        if thumb_el is not None:
            thumb = thumb_el.get("url")
        elif enc_el is not None and (enc_el.get("type","").startswith("image")):
            thumb = enc_el.get("url")
        else:
            thumb = None
        if title and link:
            items.append({"title": title, "link": link, "pubDate": pub, "description": desc, "thumbnail": thumb, "publisher": publisher})

    _rss_cache[url] = {"ts": now, "items": items}
    return items


@router.get("/noticias")
async def get_noticias(_: CurrentUser, limit: int = Query(10, ge=1, le=50)):
    """Retorna noticias mezcladas de diarios paraguayos."""
    import asyncio
    from email.utils import parsedate_to_datetime

    def _parse_date(s: str):
        try:
            return parsedate_to_datetime(s)
        except Exception:
            return None

    results: list[dict] = []
    tasks = [_fetch_rss(url) for _, url in _RSS_FEEDS]
    feeds = await asyncio.gather(*tasks, return_exceptions=True)

    for (source, _), feed_items in zip(_RSS_FEEDS, feeds):
        if isinstance(feed_items, Exception):
            continue
        for item in feed_items:
            results.append({**item, "source": source, "publisher": item.get("publisher") or source})

    # Ordenar por fecha descendente, items sin fecha al final
    results.sort(key=lambda x: _parse_date(x.get("pubDate","")) or __import__("datetime").datetime.min.replace(tzinfo=__import__("datetime").timezone.utc), reverse=True)

    return {"items": results[:limit]}
