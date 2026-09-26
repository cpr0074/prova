import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from genera_chiavi import genera
from pdnd import ClientEService, Config, ErrorePDND, crea_client_assertion, richiedi_voucher
from simulatore.server import ClientRegistrato, crea_app


class TestFlussoPDND(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cartella = Path(self.tmp.name)
        privata, pubblica = genera(cartella)
        self.config = Config(
            client_id="client-1",
            kid="kid-1",
            purpose_id="finalita-1",
            chiave_privata=privata,
            # TestClient chiama l'app FastAPI in memoria, senza avviare un server.
            token_url="http://testserver/token.oauth2",
            audience="simulatore/client-assertion",
            eservice_url="http://testserver/anagrafe/v1",
        )
        self.app = crea_app(ClientRegistrato(
            client_id="client-1", kid="kid-1", purpose_id="finalita-1",
            chiave_pubblica=pubblica.read_bytes(), audience="simulatore/client-assertion",
        ))
        self.http = TestClient(self.app)

    def tearDown(self):
        self.http.close()
        self.tmp.cleanup()

    def test_client_assertion(self):
        assertion = crea_client_assertion(self.config)
        header = jwt.get_unverified_header(assertion)
        payload = jwt.decode(assertion, options={"verify_signature": False})
        self.assertEqual((header["kid"], header["alg"]), ("kid-1", "RS256"))
        self.assertEqual(payload["iss"], "client-1")
        self.assertEqual(payload["sub"], "client-1")
        self.assertEqual(payload["aud"], "simulatore/client-assertion")
        self.assertEqual(payload["purposeId"], "finalita-1")
        self.assertEqual(payload["exp"] - payload["iat"], 600)
        self.assertNotEqual(payload["jti"], jwt.decode(crea_client_assertion(self.config),
                                                       options={"verify_signature": False})["jti"])

    def test_chiamata_eservice(self):
        client = ClientEService(self.config, self.http)
        risposta = client.get("residenti/rssmra80a01h501u")
        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(risposta.json()["cognome"], "Rossi")

        risposta = client.get("residenti", cognome="bian")
        self.assertEqual(risposta.json()["totale"], 1)

        self.assertEqual(client.get("residenti/XXXXXX00X00X000X").status_code, 404)

    def test_voucher_riusato_finche_valido(self):
        client = ClientEService(self.config, self.http)
        primo = client.voucher()
        client.get("residenti")
        self.assertIs(client.voucher(), primo)
        primo.scadenza = time.time()  # lo facciamo "scadere"
        self.assertIsNot(client.voucher(), primo)

    def test_errori_del_server_di_autorizzazione(self):
        casi = {
            "firma non valida": lambda: replace(self.config, chiave_privata=genera(Path(self.tmp.name) / "altra")[0]),
            "kid sconosciuto": lambda: replace(self.config, kid="kid-sbagliato"),
            "finalità non valida": lambda: replace(self.config, purpose_id="altra-finalita"),
            "Audience": lambda: replace(self.config, audience="auth.uat.interop.pagopa.it/client-assertion"),
            "client non valido": lambda: replace(self.config, client_id="client-2"),
        }
        for messaggio, crea_config in casi.items():
            with self.subTest(messaggio), self.assertRaises(ErrorePDND) as ctx:
                richiedi_voucher(crea_config(), self.http)
            self.assertIn(messaggio, str(ctx.exception))

    def test_eservice_senza_voucher(self):
        risposta = self.http.get("/anagrafe/v1/residenti")
        self.assertEqual(risposta.status_code, 401)
        risposta = self.http.get("/anagrafe/v1/residenti", headers={"Authorization": "Bearer falso"})
        self.assertEqual(risposta.status_code, 401)

    def test_config_da_env(self):
        env = Path(self.tmp.name) / ".env"
        env.write_text("PDND_CLIENT_ID=abc\n")
        with self.assertRaises(ValueError) as ctx:
            Config.da_env(env)
        self.assertIn("PDND_KID", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
