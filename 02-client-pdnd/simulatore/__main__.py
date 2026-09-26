"""Avvia il simulatore: python -m simulatore [--env .env] [--porta 8000]"""

import argparse
from pathlib import Path

import uvicorn

from pdnd import Config
from simulatore.server import ClientRegistrato, crea_app

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--env", default=".env")
parser.add_argument("--porta", type=int, default=8000)
args = parser.parse_args()

config = Config.da_env(args.env)
# Il simulatore "registra" il client usando gli stessi dati del .env
# e la chiave pubblica che sta accanto a quella privata.
client = ClientRegistrato(
    client_id=config.client_id,
    kid=config.kid,
    purpose_id=config.purpose_id,
    chiave_pubblica=Path(config.chiave_privata).with_name("pubblica.pem").read_bytes(),
    audience=config.audience,
)
uvicorn.run(crea_app(client), host="127.0.0.1", port=args.porta)
