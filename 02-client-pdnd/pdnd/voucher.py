"""Client assertion e richiesta del voucher (flusso Bearer di PDND Interoperabilità).

1. Creiamo un JWT (la "client assertion") e lo firmiamo con la chiave privata.
2. Lo mandiamo al server di autorizzazione PDND (endpoint /token.oauth2).
3. PDND verifica la firma con la chiave pubblica caricata sul client e ci
   restituisce un voucher, da usare come "Authorization: Bearer <voucher>".
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import httpx
import jwt

from pdnd.config import Config

TIPO_ASSERTION = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


class ErrorePDND(Exception):
    """Il server di autorizzazione ha rifiutato la richiesta."""


def crea_client_assertion(config: Config, chiave_privata: bytes | None = None) -> str:
    adesso = int(time.time())
    header = {"kid": config.kid, "alg": "RS256", "typ": "JWT"}
    # Un dict Python è come un array associativo PHP: ["iss" => ..., "sub" => ...]
    payload = {
        "iss": config.client_id,
        "sub": config.client_id,
        "aud": config.audience,
        "purposeId": config.purpose_id,
        "jti": str(uuid.uuid4()),  # identificativo univoco, impedisce il riuso
        "iat": adesso,
        "exp": adesso + config.durata_assertion,
    }
    if chiave_privata is None:
        chiave_privata = config.chiave_privata.read_bytes()
    return jwt.encode(payload, chiave_privata, algorithm="RS256", headers=header)


@dataclass
class Voucher:
    token: str
    scadenza: float  # timestamp Unix

    def valido(self, margine: int = 30) -> bool:
        """True se il voucher non scade nei prossimi `margine` secondi."""
        return time.time() < self.scadenza - margine


def richiedi_voucher(config: Config, http: httpx.Client, chiave_privata: bytes | None = None) -> Voucher:
    # data=... invia i campi come form (application/x-www-form-urlencoded),
    # come curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($campi)) in PHP.
    risposta = http.post(config.token_url, data={
        "client_id": config.client_id,
        "client_assertion": crea_client_assertion(config, chiave_privata),
        "client_assertion_type": TIPO_ASSERTION,
        "grant_type": "client_credentials",
    })
    if risposta.status_code != 200:
        raise ErrorePDND(f"Voucher rifiutato ({risposta.status_code}): {risposta.text}")
    dati = risposta.json()  # come json_decode($body, true) in PHP
    return Voucher(token=dati["access_token"], scadenza=time.time() + dati["expires_in"])
