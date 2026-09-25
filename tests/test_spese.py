import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from decimal import Decimal
from pathlib import Path

from spese.cli import euro, main
from spese.core import ENTRATA, USCITA, Registro, parse_data, parse_importo, parse_mese, riepilogo


class TestParsing(unittest.TestCase):
    def test_importo_con_virgola_o_punto(self):
        self.assertEqual(parse_importo("12,5"), Decimal("12.50"))
        self.assertEqual(parse_importo("12.50"), Decimal("12.50"))

    def test_importo_non_valido(self):
        for testo in ("abc", "0", "-3", "nan", "inf"):
            with self.subTest(testo=testo), self.assertRaises(ValueError):
                parse_importo(testo)

    def test_data(self):
        self.assertEqual(parse_data("25/09/2026"), date(2026, 9, 25))
        self.assertEqual(parse_data("2026-09-25"), date(2026, 9, 25))
        for testo in ("31/02/2026", "ieri", "25-09"):
            with self.subTest(testo=testo), self.assertRaises(ValueError):
                parse_data(testo)

    def test_mese(self):
        self.assertEqual(parse_mese("2026-09"), (2026, 9))
        for testo in ("2026-13", "settembre", "2026"):
            with self.subTest(testo=testo), self.assertRaises(ValueError):
                parse_mese(testo)

    def test_euro(self):
        self.assertEqual(euro(Decimal("1234.5")), "1.234,50 €")
        self.assertEqual(euro(Decimal("-7")), "-7,00 €")


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.percorso = Path(self.tmp.name) / "spese.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_salva_e_ricarica(self):
        reg = Registro(self.percorso)
        reg.aggiungi(USCITA, Decimal("9.90"), "Cibo", date(2026, 9, 1), "pizza")
        reg.salva()

        mov = Registro(self.percorso).movimenti[0]
        self.assertEqual(mov.importo, Decimal("9.90"))
        self.assertEqual(mov.categoria, "cibo")
        self.assertEqual(mov.data, date(2026, 9, 1))
        self.assertEqual(mov.descrizione, "pizza")

    def test_id_progressivi_dopo_eliminazione(self):
        reg = Registro(self.percorso)
        a = reg.aggiungi(USCITA, Decimal("1"), "x")
        b = reg.aggiungi(USCITA, Decimal("2"), "x")
        reg.elimina(a.id)
        c = reg.aggiungi(USCITA, Decimal("3"), "x")
        self.assertEqual((a.id, b.id, c.id), (1, 2, 3))
        with self.assertRaises(KeyError):
            reg.elimina(99)

    def test_filtra_e_riepilogo(self):
        reg = Registro(self.percorso)
        reg.aggiungi(ENTRATA, Decimal("1500"), "stipendio", date(2026, 9, 1))
        reg.aggiungi(USCITA, Decimal("600"), "affitto", date(2026, 9, 2))
        reg.aggiungi(USCITA, Decimal("50.25"), "cibo", date(2026, 9, 3))
        reg.aggiungi(USCITA, Decimal("40"), "cibo", date(2026, 8, 30))

        settembre = reg.filtra(mese=(2026, 9))
        self.assertEqual(len(settembre), 3)
        self.assertEqual(len(reg.filtra(categoria="CIBO")), 2)

        r = riepilogo(settembre)
        self.assertEqual(r.entrate, Decimal("1500"))
        self.assertEqual(r.uscite, Decimal("650.25"))
        self.assertEqual(r.saldo, Decimal("849.75"))
        self.assertEqual(list(r.per_categoria), ["affitto", "cibo"])


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = str(Path(self.tmp.name) / "spese.json")

    def tearDown(self):
        self.tmp.cleanup()

    def esegui(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            codice = main(["--file", self.file, *argv])
        return codice, out.getvalue()

    def test_flusso_completo(self):
        self.esegui("entrata", "1500", "stipendio", "--data", "2026-09-01")
        self.esegui("uscita", "12,50", "cibo", "-d", "pizza", "--data", "2026-09-05")

        codice, out = self.esegui("lista")
        self.assertEqual(codice, 0)
        self.assertIn("pizza", out)
        self.assertIn("-12,50 €", out)

        _, out = self.esegui("riepilogo", "--mese", "2026-09")
        self.assertIn("1.487,50 €", out)

        csv_path = Path(self.tmp.name) / "export.csv"
        self.esegui("esporta", str(csv_path))
        with csv_path.open(encoding="utf-8") as f:
            righe = list(csv.DictReader(f))
        self.assertEqual([r["importo"] for r in righe], ["1500.00", "12.50"])

        codice, _ = self.esegui("elimina", "2")
        self.assertEqual(codice, 0)
        _, out = self.esegui("lista")
        self.assertNotIn("pizza", out)

    def test_importo_non_valido(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--file", self.file, "uscita", "abc", "cibo"])
        self.assertFalse(Path(self.file).exists())

    def test_elimina_id_inesistente(self):
        err = io.StringIO()
        with redirect_stderr(err):
            codice, _ = self.esegui("elimina", "5")
        self.assertEqual(codice, 1)
        self.assertIn("nessun movimento", err.getvalue())

if __name__ == "__main__":
    unittest.main()
