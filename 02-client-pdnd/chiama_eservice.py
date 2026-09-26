"""Chiama un e-service tramite PDND e stampa la risposta.

Esempi:
    python chiama_eservice.py residenti/RSSMRA80A01H501U
    python chiama_eservice.py residenti cognome=rossi
    python chiama_eservice.py residenti/RSSMRA80A01H501U --mostra-token
    python chiama_eservice.py qualcosa --env .env.collaudo
"""

import argparse
import json
import sys

import httpx
import jwt

from pdnd import ClientEService, Config, ErrorePDND, crea_client_assertion


def stampa_jwt(titolo: str, token: str) -> None:
    """Decodifica un JWT senza verificarne la firma: serve solo per vedere cosa contiene."""
    print(f"--- {titolo} ---")
    print("header: ", json.dumps(jwt.get_unverified_header(token), indent=2))
    print("payload:", json.dumps(jwt.decode(token, options={"verify_signature": False}), indent=2))
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("percorso", help="percorso dopo ESERVICE_URL, es. residenti/RSSMRA80A01H501U")
    parser.add_argument("parametri", nargs="*", help="parametri della query string, nella forma nome=valore")
    parser.add_argument("--env", default=".env", help="file di configurazione (predefinito: .env)")
    parser.add_argument("--mostra-token", action="store_true", help="mostra client assertion e voucher decodificati")
    args = parser.parse_args()

    try:
        config = Config.da_env(args.env)
        parametri = dict(p.split("=", 1) for p in args.parametri)
    except ValueError as errore:
        print(f"Errore di configurazione: {errore}", file=sys.stderr)
        return 2

    # try/except è il Try/Catch di VB.NET.
    try:
        with ClientEService(config) as client:
            if args.mostra_token:
                stampa_jwt("Client assertion (firmata da noi)", crea_client_assertion(config))
                stampa_jwt("Voucher (firmato da PDND)", client.voucher().token)
            risposta = client.get(args.percorso, **parametri)
    except ErrorePDND as errore:
        print(errore, file=sys.stderr)
        return 1
    except httpx.HTTPError as errore:
        print(f"Errore di rete: {errore}", file=sys.stderr)
        return 1

    print(f"HTTP {risposta.status_code}")
    try:
        print(json.dumps(risposta.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print(risposta.text)
    return 0 if risposta.is_success else 1


if __name__ == "__main__":
    sys.exit(main())
