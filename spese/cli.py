"""Interfaccia da riga di comando: python -m spese <comando> ..."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from spese.core import (
    ENTRATA,
    TIPI,
    USCITA,
    Registro,
    esporta_csv,
    euro,
    parse_data,
    parse_importo,
    parse_mese,
    percorso_predefinito,
    riepilogo,
)


def _tipo_importo(testo: str) -> Decimal:
    try:
        return parse_importo(testo)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def _tipo_data(testo: str) -> date:
    try:
        return parse_data(testo)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def _tipo_mese(testo: str) -> tuple[int, int]:
    try:
        return parse_mese(testo)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def crea_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spese", description="Gestore di spese personali.")
    parser.add_argument(
        "--file",
        type=Path,
        default=percorso_predefinito(),
        help="file JSON dei dati (predefinito: $SPESE_FILE o ~/.spese.json)",
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("finestra", help="apre l'interfaccia grafica")

    for tipo in TIPI:
        p = sub.add_parser(tipo, help=f"registra una {tipo}")
        p.add_argument("importo", type=_tipo_importo, help="es. 12.50 oppure 12,50")
        p.add_argument("categoria", help="es. cibo, affitto, stipendio")
        p.add_argument("-d", "--descrizione", default="")
        p.add_argument("--data", type=_tipo_data, help="GG/MM/AAAA (predefinito: oggi)")

    filtri = argparse.ArgumentParser(add_help=False)
    filtri.add_argument("--mese", type=_tipo_mese, help="AAAA-MM")
    filtri.add_argument("--categoria")
    filtri.add_argument("--tipo", choices=TIPI)

    sub.add_parser("lista", parents=[filtri], help="mostra i movimenti")
    sub.add_parser("riepilogo", parents=[filtri], help="totali e spese per categoria")

    p = sub.add_parser("elimina", help="elimina un movimento per ID")
    p.add_argument("id", type=int)

    p = sub.add_parser("esporta", parents=[filtri], help="esporta i movimenti in CSV")
    p.add_argument("destinazione", type=Path)

    return parser


def cmd_aggiungi(reg: Registro, args) -> int:
    mov = reg.aggiungi(args.comando, args.importo, args.categoria, args.data, args.descrizione)
    reg.salva()
    print(f"Aggiunta {mov.tipo} #{mov.id}: {euro(mov.importo)} [{mov.categoria}] del {mov.data}")
    return 0


def cmd_lista(reg: Registro, args) -> int:
    movimenti = reg.filtra(args.mese, args.categoria, args.tipo)
    if not movimenti:
        print("Nessun movimento trovato.")
        return 0
    print(f"{'ID':>4}  {'DATA':<10}  {'TIPO':<7}  {'IMPORTO':>12}  {'CATEGORIA':<14}  DESCRIZIONE")
    for m in movimenti:
        segno = "+" if m.tipo == ENTRATA else "-"
        print(
            f"{m.id:>4}  {m.data.isoformat():<10}  {m.tipo:<7}  "
            f"{segno + euro(m.importo):>12}  {m.categoria:<14}  {m.descrizione}"
        )
    return 0


def cmd_riepilogo(reg: Registro, args) -> int:
    r = riepilogo(reg.filtra(args.mese, args.categoria, args.tipo))
    print(f"Entrate: {euro(r.entrate):>14}")
    print(f"Uscite:  {euro(r.uscite):>14}")
    print(f"Saldo:   {euro(r.saldo):>14}")
    if r.per_categoria:
        print("\nUscite per categoria:")
        larghezza = max(len(c) for c in r.per_categoria)
        for categoria, totale in r.per_categoria.items():
            quota = totale / r.uscite * 100
            barra = "█" * round(quota / 5)
            print(f"  {categoria:<{larghezza}}  {euro(totale):>12}  {quota:5.1f}%  {barra}")
    return 0


def cmd_elimina(reg: Registro, args) -> int:
    try:
        mov = reg.elimina(args.id)
    except KeyError:
        print(f"Errore: nessun movimento con ID {args.id}.", file=sys.stderr)
        return 1
    reg.salva()
    print(f"Eliminato movimento #{mov.id} ({mov.tipo} di {euro(mov.importo)}, {mov.categoria}).")
    return 0


def cmd_esporta(reg: Registro, args) -> int:
    movimenti = reg.filtra(args.mese, args.categoria, args.tipo)
    esporta_csv(movimenti, args.destinazione)
    print(f"Esportati {len(movimenti)} movimenti in {args.destinazione}.")
    return 0


COMANDI = {
    ENTRATA: cmd_aggiungi,
    USCITA: cmd_aggiungi,
    "lista": cmd_lista,
    "riepilogo": cmd_riepilogo,
    "elimina": cmd_elimina,
    "esporta": cmd_esporta,
}


def main(argv: list[str] | None = None) -> int:
    args = crea_parser().parse_args(argv)
    if args.comando == "finestra":
        from spese.gui import main as avvia_finestra

        avvia_finestra(args.file)
        return 0
    reg = Registro(args.file)
    return COMANDI[args.comando](reg, args)
