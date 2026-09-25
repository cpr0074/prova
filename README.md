# Gestore di spese 💶

Piccolo programma da riga di comando per registrare entrate e uscite e vedere dove vanno i soldi.
Usa solo la libreria standard di Python (3.9+): nessuna dipendenza da installare.

## Uso

```bash
python -m spese entrata 1800 stipendio --data 2026-09-01
python -m spese uscita 85,40 spesa -d "supermercato"
python -m spese lista --mese 2026-09
python -m spese riepilogo --mese 2026-09
python -m spese elimina 3
python -m spese esporta spese.csv
```

Esempio di riepilogo:

```
Entrate:     1.800,00 €
Uscite:        767,40 €
Saldo:       1.032,60 €

Uscite per categoria:
  affitto      650,00 €   84.7%  █████████████████
  spesa         85,40 €   11.1%  ██
  svago         32,00 €    4.2%  █
```

| Comando | Cosa fa |
|---|---|
| `entrata IMPORTO CATEGORIA` | registra un'entrata (`-d` descrizione, `--data AAAA-MM-GG`) |
| `uscita IMPORTO CATEGORIA` | registra un'uscita (stesse opzioni) |
| `lista` | elenca i movimenti |
| `riepilogo` | totale entrate/uscite, saldo e uscite per categoria |
| `elimina ID` | elimina un movimento |
| `esporta FILE.csv` | esporta in CSV (apribile con Excel) |

`lista`, `riepilogo` ed `esporta` accettano i filtri `--mese AAAA-MM`, `--categoria NOME` e `--tipo entrata|uscita`.

I dati vengono salvati in `~/.spese.json`. Per usare un altro file: `--file percorso.json` oppure la variabile d'ambiente `SPESE_FILE`.

Per avere il comando `spese` al posto di `python -m spese`: `pip install -e .`

## Test

```bash
python -m unittest -v
```

## Struttura

- `spese/core.py`: modello dei movimenti, salvataggio JSON, filtri e calcolo del riepilogo
- `spese/cli.py`: comandi da terminale (argparse) e formattazione degli importi
- `tests/test_spese.py`: test automatici
