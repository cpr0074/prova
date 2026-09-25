"""Modello dei movimenti e salvataggio su file JSON."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

ENTRATA = "entrata"
USCITA = "uscita"
TIPI = (ENTRATA, USCITA)


@dataclass
class Movimento:
    id: int
    tipo: str
    importo: Decimal
    categoria: str
    data: date
    descrizione: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["importo"] = str(self.importo)
        d["data"] = self.data.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Movimento:
        return cls(
            id=int(d["id"]),
            tipo=d["tipo"],
            importo=Decimal(d["importo"]),
            categoria=d["categoria"],
            data=date.fromisoformat(d["data"]),
            descrizione=d.get("descrizione", ""),
        )


def parse_importo(testo: str) -> Decimal:
    """Converte "12,50" o "12.50" in Decimal("12.50"); rifiuta valori non positivi."""
    try:
        valore = Decimal(testo.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"importo non valido: {testo!r}") from None
    if not valore.is_finite() or valore <= 0:
        raise ValueError(f"l'importo deve essere un numero positivo: {testo!r}")
    return valore.quantize(Decimal("0.01"))


def parse_mese(testo: str) -> tuple[int, int]:
    """Converte "2026-09" in (2026, 9)."""
    try:
        anno, mese = (int(x) for x in testo.split("-"))
        date(anno, mese, 1)
    except ValueError:
        raise ValueError(f"mese non valido (formato AAAA-MM): {testo!r}") from None
    return anno, mese


class Registro:
    """Elenco dei movimenti salvato in un file JSON."""

    def __init__(self, percorso: Path):
        self.percorso = Path(percorso)
        self.movimenti: list[Movimento] = []
        if self.percorso.exists():
            with self.percorso.open(encoding="utf-8") as f:
                self.movimenti = [Movimento.from_dict(d) for d in json.load(f)]

    def salva(self) -> None:
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.percorso.with_name(self.percorso.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self.movimenti], f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.percorso)

    def aggiungi(
        self,
        tipo: str,
        importo: Decimal,
        categoria: str,
        data: date | None = None,
        descrizione: str = "",
    ) -> Movimento:
        if tipo not in TIPI:
            raise ValueError(f"tipo non valido: {tipo!r}")
        nuovo_id = max((m.id for m in self.movimenti), default=0) + 1
        mov = Movimento(
            id=nuovo_id,
            tipo=tipo,
            importo=importo,
            categoria=categoria.strip().lower(),
            data=data or date.today(),
            descrizione=descrizione,
        )
        self.movimenti.append(mov)
        return mov

    def elimina(self, id_: int) -> Movimento:
        for i, m in enumerate(self.movimenti):
            if m.id == id_:
                return self.movimenti.pop(i)
        raise KeyError(id_)

    def filtra(
        self,
        mese: tuple[int, int] | None = None,
        categoria: str | None = None,
        tipo: str | None = None,
    ) -> list[Movimento]:
        risultato = []
        for m in self.movimenti:
            if mese and (m.data.year, m.data.month) != mese:
                continue
            if categoria and m.categoria != categoria.strip().lower():
                continue
            if tipo and m.tipo != tipo:
                continue
            risultato.append(m)
        return sorted(risultato, key=lambda m: (m.data, m.id))


@dataclass
class Riepilogo:
    entrate: Decimal
    uscite: Decimal
    per_categoria: dict[str, Decimal]

    @property
    def saldo(self) -> Decimal:
        return self.entrate - self.uscite


def riepilogo(movimenti: list[Movimento]) -> Riepilogo:
    entrate = Decimal("0")
    uscite = Decimal("0")
    per_categoria: dict[str, Decimal] = defaultdict(Decimal)
    for m in movimenti:
        if m.tipo == ENTRATA:
            entrate += m.importo
        else:
            uscite += m.importo
            per_categoria[m.categoria] += m.importo
    ordinate = dict(sorted(per_categoria.items(), key=lambda kv: kv[1], reverse=True))
    return Riepilogo(entrate, uscite, ordinate)
