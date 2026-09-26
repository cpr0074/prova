"""Configurazione letta da un file .env (come in Laravel o nel web.config di .NET)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Nome della variabile d'ambiente -> nome del campo in Config.
VARIABILI = {
    "PDND_CLIENT_ID": "client_id",
    "PDND_KID": "kid",
    "PDND_PURPOSE_ID": "purpose_id",
    "PDND_CHIAVE_PRIVATA": "chiave_privata",
    "PDND_TOKEN_URL": "token_url",
    "PDND_AUDIENCE": "audience",
    "ESERVICE_URL": "eservice_url",
}


# @dataclass genera da solo costruttore, confronto e stampa leggibile:
# è l'equivalente di una Class VB.NET con sole Property ReadOnly.
@dataclass(frozen=True)
class Config:
    client_id: str      # ID del client, dal back office PDND
    kid: str            # ID della chiave pubblica caricata sul client
    purpose_id: str     # ID della finalità approvata per l'e-service
    chiave_privata: Path
    token_url: str      # endpoint del server di autorizzazione
    audience: str       # "aud" della client assertion
    eservice_url: str   # URL base dell'e-service dell'erogatore
    durata_assertion: int = 600  # secondi

    @classmethod
    def da_env(cls, file_env: str | Path = ".env") -> Config:
        load_dotenv(file_env, override=True)
        mancanti = [nome for nome in VARIABILI if not os.environ.get(nome)]
        if mancanti:
            raise ValueError(f"Mancano queste variabili in {file_env}: {', '.join(mancanti)}")
        # Dict comprehension: costruisce un dizionario in una riga,
        # come un foreach che riempie un array associativo in PHP.
        valori = {campo: os.environ[nome] for nome, campo in VARIABILI.items()}
        valori["chiave_privata"] = Path(valori["chiave_privata"])
        return cls(**valori)  # **valori = passa il dizionario come argomenti con nome
