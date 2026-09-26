# Lezione 2 · Fruire di un e-service tramite PDND

In questa lezione scrivi un client Python che:

1. crea e firma la **client assertion** con la tua chiave privata;
2. la scambia con un **voucher** sul server di autorizzazione PDND;
3. chiama l'**e-service** dell'erogatore con `Authorization: Bearer <voucher>`,
   riusando il voucher finché è valido e rinnovandolo quando scade.

Prima lo provi con un **simulatore locale** (nessun rischio, nessuna credenziale),
poi cambi il file di configurazione e lo usi sul **collaudo PDND** vero.

```
 tu (fruitore)                    PDND                         erogatore
 ─────────────                    ────                         ─────────
 client assertion  ──POST /token.oauth2──▶  verifica firma
 (JWT firmato con                           con la chiave
  la chiave privata)  ◀──── voucher ──────  pubblica caricata
                                            sul client
 GET /residenti/...  ─────── Authorization: Bearer <voucher> ──────▶  verifica il voucher
                     ◀──────────────────── dati ──────────────────────  e risponde
```

## Installazione

Serve Python 3.10 o superiore. Apri il terminale nella cartella `02-client-pdnd`.

```bash
# Crea un "ambiente virtuale": una cartella con le librerie di questo progetto,
# separate da quelle di sistema (simile a vendor/ di Composer in PHP).
python -m venv .venv

# Attivalo
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac / Linux

# Installa le librerie (come "composer install" o il ripristino dei pacchetti NuGet)
pip install -r requirements.txt
```

Ogni volta che riapri il terminale, riattiva l'ambiente con il comando `activate`.

## Passo 1 · Prova con il simulatore

```bash
python genera_chiavi.py          # crea chiavi/privata.pem e chiavi/pubblica.pem
copy .env.esempio .env           # Windows   (Mac/Linux: cp .env.esempio .env)
python -m simulatore             # avvia il finto PDND su http://127.0.0.1:8000
```

Lascia aperta quella finestra, aprine un'**altra** nella stessa cartella (riattiva l'ambiente) e prova:

```bash
python chiama_eservice.py residenti/RSSMRA80A01H501U
python chiama_eservice.py residenti cognome=bianchi
python chiama_eservice.py residenti/RSSMRA80A01H501U --mostra-token
```

Con `--mostra-token` vedi il contenuto della client assertion e del voucher: è il modo migliore
per capire cosa viaggia davvero.

Apri anche <http://127.0.0.1:8000/docs>: FastAPI genera da solo la documentazione OpenAPI
del finto e-service. È lo stesso formato con cui gli erogatori descrivono i loro e-service su PDND.

**Prova a sbagliare apposta**, così riconoscerai gli errori in collaudo: cambia `PDND_KID` o
`PDND_PURPOSE_ID` nel `.env`, oppure rigenera le chiavi con `python genera_chiavi.py --forza`
senza riavviare il simulatore. Ogni volta il simulatore spiega cosa non va.

## Passo 2 · Passa al collaudo PDND

1. **Chiavi**: carica il contenuto di `chiavi/pubblica.pem` sul tuo client e-service nel back office
   di collaudo. PDND ti mostrerà il **KID** della chiave. Usa chiavi diverse per collaudo e produzione.
2. **Finalità**: devi avere una finalità **attiva** sull'e-service che vuoi usare, associata al client.
   Ti serve il suo **Purpose ID**.
3. **Configurazione**: copia `.env.collaudo.esempio` in `.env.collaudo` e compila i valori
   (nel file trovi dove prenderli). L'URL dell'e-service è quello dell'erogatore, dalla scheda
   dell'e-service o dalla sua interfaccia OpenAPI.
4. **Chiamata**:
   ```bash
   python chiama_eservice.py <percorso-dell-api> --env .env.collaudo --mostra-token
   ```

Se PDND rifiuta la client assertion, nel back office c'è uno strumento di **debug della client
assertion**: incolla quella stampata da `--mostra-token` e ti dice quale campo è sbagliato.

> **Attenzione:** alcuni e-service richiedono più del semplice Bearer. Alcuni usano il voucher
> **DPoP**, altri (per esempio quelli con dati personali, come ANPR) chiedono header aggiuntivi
> del Modello di Interoperabilità (`Agid-JWT-Signature`, `Agid-JWT-TrackingEvidence`) e un
> campo `digest` nella client assertion. Controlla la documentazione dell'e-service: li vediamo
> nelle prossime lezioni, estendendo questo stesso client.

## Il codice, file per file

| File | Cosa fa | Cosa impari di Python |
|---|---|---|
| `pdnd/config.py` | legge il `.env` | `@dataclass`, dizionari, `**kwargs`, `classmethod` |
| `pdnd/voucher.py` | client assertion e richiesta del voucher | JWT con `PyJWT`, POST con `httpx`, eccezioni personalizzate |
| `pdnd/client.py` | chiama l'e-service, riusa e rinnova il voucher | classi, cache in un attributo, `with` (context manager) |
| `chiama_eservice.py` | programma da terminale | `argparse`, `try/except`, codici di uscita |
| `genera_chiavi.py` | crea la coppia di chiavi RSA | libreria `cryptography`, file binari |
| `simulatore/server.py` | finto PDND + finto e-service | API web con `FastAPI` (ti servirà anche per erogare) |
| `tests/test_flusso.py` | 6 test automatici, compresi i casi di errore | `unittest`, test di un'API senza avviare il server |

Per lanciare i test: `python -m unittest -v`

## Dizionario PHP / VB.NET → Python

| Concetto | PHP | VB.NET | Python |
|---|---|---|---|
| array associativo | `["a" => 1]` | `Dictionary(Of String, Integer)` | `{"a": 1}` |
| stringa con variabili | `"Ciao $nome"` | `$"Ciao {nome}"` | `f"Ciao {nome}"` |
| null | `null` | `Nothing` | `None` |
| ciclo | `foreach ($lista as $x)` | `For Each x In lista` | `for x in lista:` |
| classe con proprietà | `class A { public $x; }` | `Public Property X` | `@dataclass class A: x: int` |
| costruttore | `__construct` | `Sub New` | `__init__` |
| riferimento all'oggetto | `$this` | `Me` | `self` |
| errori | `try / catch` | `Try / Catch` | `try / except` |
| rilascio risorse | `finally` | `Using` | `with` |
| JSON → oggetto | `json_decode($s, true)` | `JsonSerializer.Deserialize` | `json.loads(s)` / `risposta.json()` |
| chiamata HTTP | `curl_exec` / Guzzle | `HttpClient` | `httpx` |
| dipendenze | `composer.json` | NuGet | `requirements.txt` + `pip` |

## Esercizi

1. **Metodo `post`**: aggiungi a `ClientEService` un metodo `post(percorso, dati)` che invia JSON
   (suggerimento: `self.http.request(..., json=dati)`). Aggiungi al simulatore un endpoint POST
   per provarlo.
2. **Log delle chiamate**: usa il modulo `logging` per scrivere su file ogni chiamata con URL,
   codice di risposta e durata in millisecondi (`time.perf_counter()`).
3. **Nuovo endpoint**: aggiungi al simulatore `GET /anagrafe/v1/residenti/{cf}/stato-famiglia`
   e chiamalo con `chiama_eservice.py`.
4. **Elaborazione in blocco**: scrivi uno script che legge un CSV di codici fiscali, chiama
   l'e-service per ciascuno e salva i risultati in un nuovo CSV. È il caso d'uso più comune in un ente.

## Sicurezza

- La chiave privata **non va mai** caricata su Git: `chiavi/`, `.env` e `.env.collaudo`
  sono già esclusi da `.gitignore`.
- In produzione conserva la chiave in un posto protetto, con permessi ristretti, e ruotala periodicamente.
- Non usare dati personali reali per le prove: nel collaudo usa i dati di test forniti dall'erogatore.
