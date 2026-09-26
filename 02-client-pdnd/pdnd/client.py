"""Client per chiamare un e-service: gestisce da solo voucher, scadenza e rinnovo."""

from __future__ import annotations

import httpx

from pdnd.config import Config
from pdnd.voucher import Voucher, richiedi_voucher


class ClientEService:
    def __init__(self, config: Config, http: httpx.Client | None = None):
        self.config = config
        # "a or b" restituisce a se è valorizzato, altrimenti b (come ?: in PHP).
        self.http = http or httpx.Client(timeout=30)
        self._chiave = config.chiave_privata.read_bytes()
        self._voucher: Voucher | None = None

    def voucher(self, rinnova: bool = False) -> Voucher:
        """Restituisce il voucher in cache, chiedendone uno nuovo solo se serve."""
        if rinnova or self._voucher is None or not self._voucher.valido():
            self._voucher = richiedi_voucher(self.config, self.http, self._chiave)
        return self._voucher

    def get(self, percorso: str, **parametri) -> httpx.Response:
        """GET su <eservice_url>/<percorso>; i parametri diventano la query string."""
        url = self.config.eservice_url.rstrip("/") + "/" + percorso.lstrip("/")
        risposta = self._chiama("GET", url, parametri)
        if risposta.status_code == 401:
            # Voucher revocato o scaduto lato server: ne chiediamo uno nuovo e riproviamo una volta.
            self.voucher(rinnova=True)
            risposta = self._chiama("GET", url, parametri)
        return risposta

    def _chiama(self, metodo: str, url: str, parametri: dict) -> httpx.Response:
        intestazioni = {"Authorization": f"Bearer {self.voucher().token}"}
        return self.http.request(metodo, url, params=parametri, headers=intestazioni)

    # __enter__/__exit__ permettono di usare il client con "with", come Using in VB.NET:
    # alla fine del blocco la connessione viene chiusa anche in caso di errore.
    def __enter__(self) -> ClientEService:
        return self

    def __exit__(self, *_errore) -> None:
        self.http.close()
