"""Simulatore locale di PDND: server di autorizzazione + un e-service di anagrafe fittizio.

Serve per provare tutto il flusso sul proprio computer, senza toccare il collaudo.
Fa gli stessi controlli principali del server vero sulla client assertion:
firma, kid, iss/sub, aud, purposeId, scadenza e riuso del jti.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from urllib.parse import parse_qs

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

TIPO_ASSERTION = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
AUDIENCE_ESERVICE = "simulatore/anagrafe/v1"
DURATA_VOUCHER = 600
DURATA_MASSIMA_ASSERTION = 24 * 3600

# Dati inventati, a solo scopo di esempio.
RESIDENTI = {
    "RSSMRA80A01H501U": {"nome": "Mario", "cognome": "Rossi", "data_nascita": "1980-01-01",
                         "comune_residenza": "Roma", "indirizzo": "Via dei Test 1"},
    "BNCLRA85M41F205X": {"nome": "Laura", "cognome": "Bianchi", "data_nascita": "1985-08-01",
                         "comune_residenza": "Milano", "indirizzo": "Corso Esempio 22"},
    "VRDGPP70C15L219K": {"nome": "Giuseppe", "cognome": "Verdi", "data_nascita": "1970-03-15",
                         "comune_residenza": "Torino", "indirizzo": "Piazza Prova 3"},
}


@dataclass
class ClientRegistrato:
    """Quello che su PDND è registrato nel back office: client, chiave pubblica e finalità."""
    client_id: str
    kid: str
    purpose_id: str
    chiave_pubblica: bytes
    audience: str


class ErroreRichiesta(Exception):
    def __init__(self, titolo: str, dettaglio: str, status: int = 400):
        super().__init__(dettaglio)
        self.titolo, self.dettaglio, self.status = titolo, dettaglio, status


@dataclass
class ServerAutorizzazione:
    client: ClientRegistrato
    chiave_firma: rsa.RSAPrivateKey = field(default_factory=lambda: rsa.generate_private_key(65537, 2048))
    jti_usati: set[str] = field(default_factory=set)

    def emetti_voucher(self, campi: dict[str, str]) -> dict:
        if campi.get("grant_type") != "client_credentials":
            raise ErroreRichiesta("grant_type non valido", "deve essere client_credentials")
        if campi.get("client_assertion_type") != TIPO_ASSERTION:
            raise ErroreRichiesta("client_assertion_type non valido", f"deve essere {TIPO_ASSERTION}")
        assertion = campi.get("client_assertion", "")

        try:
            header = jwt.get_unverified_header(assertion)
        except jwt.PyJWTError as e:
            raise ErroreRichiesta("client_assertion non leggibile", str(e)) from None
        if header.get("kid") != self.client.kid:
            raise ErroreRichiesta("kid sconosciuto", f"nessuna chiave con kid {header.get('kid')!r} sul client")

        try:
            payload = jwt.decode(
                assertion, self.client.chiave_pubblica, algorithms=["RS256"],
                audience=self.client.audience, options={"require": ["iss", "sub", "aud", "jti", "iat", "exp"]},
            )
        except jwt.InvalidSignatureError:
            raise ErroreRichiesta("firma non valida", "la chiave privata non corrisponde alla pubblica caricata") from None
        except jwt.PyJWTError as e:
            raise ErroreRichiesta("client_assertion non valida", str(e)) from None

        if not (payload["iss"] == payload["sub"] == campi.get("client_id") == self.client.client_id):
            raise ErroreRichiesta("client non valido", "iss, sub e client_id devono essere l'ID del client")
        if payload.get("purposeId") != self.client.purpose_id:
            raise ErroreRichiesta("finalità non valida", f"purposeId {payload.get('purposeId')!r} non attivo per il client")
        if payload["exp"] - payload["iat"] > DURATA_MASSIMA_ASSERTION:
            raise ErroreRichiesta("durata eccessiva", "exp - iat supera la durata massima consentita")
        if payload["jti"] in self.jti_usati:
            raise ErroreRichiesta("jti già usato", "ogni client assertion deve avere un jti diverso")
        self.jti_usati.add(payload["jti"])

        adesso = int(time.time())
        voucher = jwt.encode({
            "iss": "simulatore-pdnd",
            "aud": AUDIENCE_ESERVICE,
            "client_id": self.client.client_id,
            "sub": self.client.client_id,
            "purposeId": self.client.purpose_id,
            "jti": str(uuid.uuid4()),
            "iat": adesso,
            "nbf": adesso,
            "exp": adesso + DURATA_VOUCHER,
        }, self.chiave_firma, algorithm="RS256", headers={"kid": "simulatore"})
        return {"access_token": voucher, "token_type": "Bearer", "expires_in": DURATA_VOUCHER}

    def verifica_voucher(self, authorization: str | None) -> dict:
        """Quello che fa l'erogatore a ogni chiamata: controlla il voucher firmato da PDND."""
        if not authorization or not authorization.startswith("Bearer "):
            raise ErroreRichiesta("voucher mancante", "serve l'header Authorization: Bearer <voucher>", 401)
        try:
            return jwt.decode(authorization.removeprefix("Bearer "), self.chiave_firma.public_key(),
                              algorithms=["RS256"], audience=AUDIENCE_ESERVICE)
        except jwt.PyJWTError as e:
            raise ErroreRichiesta("voucher non valido", str(e), 401) from None


def crea_app(client: ClientRegistrato) -> FastAPI:
    app = FastAPI(title="Simulatore PDND")
    server = ServerAutorizzazione(client)
    app.state.server = server

    @app.exception_handler(ErroreRichiesta)
    def gestisci_errore(_request: Request, e: ErroreRichiesta) -> JSONResponse:
        return JSONResponse({"status": e.status, "title": e.titolo, "detail": e.dettaglio}, status_code=e.status)

    @app.post("/token.oauth2")
    async def token(request: Request) -> dict:
        corpo = parse_qs((await request.body()).decode())
        campi = {nome: valori[0] for nome, valori in corpo.items()}
        return server.emetti_voucher(campi)

    @app.get("/anagrafe/v1/residenti/{codice_fiscale}")
    def residente(codice_fiscale: str, authorization: str | None = Header(None)) -> dict:
        server.verifica_voucher(authorization)
        dati = RESIDENTI.get(codice_fiscale.upper())
        if dati is None:
            raise HTTPException(404, detail=f"nessun residente con codice fiscale {codice_fiscale}")
        return {"codice_fiscale": codice_fiscale.upper(), **dati}

    @app.get("/anagrafe/v1/residenti")
    def cerca_residenti(cognome: str = "", authorization: str | None = Header(None)) -> dict:
        server.verifica_voucher(authorization)
        trovati = [{"codice_fiscale": cf, **dati} for cf, dati in RESIDENTI.items()
                   if cognome.lower() in dati["cognome"].lower()]
        return {"totale": len(trovati), "risultati": trovati}

    return app
