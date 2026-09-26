"""Interfaccia grafica (tkinter) del gestore di spese."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from spese.core import (
    ENTRATA,
    USCITA,
    Registro,
    esporta_csv,
    euro,
    parse_data,
    parse_importo,
    percorso_predefinito,
    riepilogo,
)

TUTTI = "Tutti"
TUTTE = "Tutte"
MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
VERDE = "#1a7f37"
ROSSO = "#c62828"
COLORE_BARRE = "#4a6fa5"


def nome_mese(anno: int, mese: int) -> str:
    return f"{MESI[mese - 1]} {anno}"


class App(ttk.Frame):
    def __init__(self, master: tk.Tk, registro: Registro):
        super().__init__(master, padding=12)
        self.registro = registro
        self.mesi_disponibili: dict[str, tuple[int, int]] = {}

        master.title("Gestore spese")
        master.minsize(900, 560)
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._crea_form()
        self._crea_filtri_e_tabella()
        self._crea_riepilogo()
        self.aggiorna()
        self.importo.focus_set()

    # --- Costruzione dell'interfaccia -------------------------------------------------

    def _crea_form(self) -> None:
        box = ttk.LabelFrame(self, text="Nuovo movimento", padding=10)
        box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.tipo = tk.StringVar(value=USCITA)
        ttk.Radiobutton(box, text="Uscita", value=USCITA, variable=self.tipo).grid(row=1, column=0, padx=(0, 6))
        ttk.Radiobutton(box, text="Entrata", value=ENTRATA, variable=self.tipo).grid(row=1, column=1, padx=(0, 12))

        campi = [("Importo (€)", 10), ("Categoria", 16), ("Data (GG/MM/AAAA)", 12), ("Descrizione", 28)]
        widget = []
        for i, (etichetta, larghezza) in enumerate(campi, start=2):
            ttk.Label(box, text=etichetta).grid(row=0, column=i, sticky="w", padx=(0, 8))
            w = ttk.Combobox(box, width=larghezza) if etichetta == "Categoria" else ttk.Entry(box, width=larghezza)
            w.grid(row=1, column=i, sticky="ew", padx=(0, 8))
            widget.append(w)
        self.importo, self.categoria, self.data, self.descrizione = widget
        self.data.insert(0, date.today().strftime("%d/%m/%Y"))
        box.columnconfigure(5, weight=1)

        ttk.Button(box, text="Aggiungi", command=self.aggiungi).grid(row=1, column=6)
        for w in widget:
            w.bind("<Return>", lambda _e: self.aggiungi())

    def _crea_filtri_e_tabella(self) -> None:
        sinistra = ttk.Frame(self)
        sinistra.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        sinistra.columnconfigure(0, weight=1)
        sinistra.rowconfigure(1, weight=1)

        barra = ttk.Frame(sinistra)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(barra, text="Mese").pack(side="left")
        self.filtro_mese = ttk.Combobox(barra, state="readonly", width=12)
        self.filtro_mese.pack(side="left", padx=(4, 12))
        ttk.Label(barra, text="Categoria").pack(side="left")
        self.filtro_categoria = ttk.Combobox(barra, state="readonly", width=14)
        self.filtro_categoria.pack(side="left", padx=(4, 12))
        for combo in (self.filtro_mese, self.filtro_categoria):
            combo.bind("<<ComboboxSelected>>", lambda _e: self.aggiorna())
        ttk.Button(barra, text="Esporta CSV…", command=self.esporta).pack(side="right")
        ttk.Button(barra, text="Elimina", command=self.elimina).pack(side="right", padx=6)

        colonne = {"data": ("Data", 90), "tipo": ("Tipo", 70), "importo": ("Importo", 100),
                   "categoria": ("Categoria", 110), "descrizione": ("Descrizione", 200)}
        self.tabella = ttk.Treeview(sinistra, columns=list(colonne), show="headings", selectmode="browse")
        for chiave, (titolo, larghezza) in colonne.items():
            self.tabella.heading(chiave, text=titolo)
            self.tabella.column(chiave, width=larghezza, anchor="e" if chiave == "importo" else "w",
                                stretch=chiave == "descrizione")
        self.tabella.tag_configure(ENTRATA, foreground=VERDE)
        self.tabella.tag_configure(USCITA, foreground=ROSSO)
        self.tabella.bind("<Delete>", lambda _e: self.elimina())
        scroll = ttk.Scrollbar(sinistra, orient="vertical", command=self.tabella.yview)
        self.tabella.configure(yscrollcommand=scroll.set)
        self.tabella.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")

    def _crea_riepilogo(self) -> None:
        box = ttk.LabelFrame(self, text="Riepilogo", padding=10)
        box.grid(row=1, column=1, sticky="nsew")
        box.rowconfigure(4, weight=1)

        self.totali = {}
        for riga, (chiave, testo) in enumerate([("entrate", "Entrate"), ("uscite", "Uscite"), ("saldo", "Saldo")]):
            ttk.Label(box, text=testo).grid(row=riga, column=0, sticky="w")
            etichetta = ttk.Label(box, font=("TkDefaultFont", 11, "bold"))
            etichetta.grid(row=riga, column=1, sticky="e", padx=(20, 0))
            self.totali[chiave] = etichetta

        ttk.Label(box, text="Uscite per categoria").grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 4))
        self.grafico = tk.Canvas(box, width=280, highlightthickness=0, background=self._sfondo())
        self.grafico.grid(row=4, column=0, columnspan=2, sticky="nsew")
        self.grafico.bind("<Configure>", lambda _e: self._disegna_grafico())

    def _sfondo(self) -> str:
        return ttk.Style().lookup("TFrame", "background") or "white"

    # --- Azioni ---------------------------------------------------------------------

    def aggiungi(self) -> None:
        try:
            importo = parse_importo(self.importo.get().strip())
        except ValueError:
            messagebox.showerror("Importo non valido", "Scrivi un numero maggiore di zero, ad esempio 12,50.")
            self.importo.focus_set()
            return
        categoria = self.categoria.get().strip()
        if not categoria:
            messagebox.showerror("Categoria mancante", "Scrivi una categoria, ad esempio cibo o affitto.")
            self.categoria.focus_set()
            return
        try:
            giorno = parse_data(self.data.get())
        except ValueError:
            messagebox.showerror("Data non valida", "Scrivi la data nel formato GG/MM/AAAA, ad esempio 25/09/2026.")
            self.data.focus_set()
            return

        self.registro.aggiungi(self.tipo.get(), importo, categoria, giorno, self.descrizione.get().strip())
        self.registro.salva()
        for campo in (self.importo, self.categoria, self.descrizione):
            campo.delete(0, "end")
        self.importo.focus_set()
        self.aggiorna()

    def elimina(self) -> None:
        selezione = self.tabella.selection()
        if not selezione:
            messagebox.showinfo("Elimina", "Seleziona prima un movimento nella tabella.")
            return
        id_ = int(selezione[0])
        valori = self.tabella.item(selezione[0], "values")
        if messagebox.askyesno("Elimina", f"Eliminare {valori[1]} di {valori[2]} ({valori[3]}) del {valori[0]}?"):
            self.registro.elimina(id_)
            self.registro.salva()
            self.aggiorna()

    def esporta(self) -> None:
        destinazione = filedialog.asksaveasfilename(
            title="Esporta in CSV", defaultextension=".csv", initialfile="spese.csv",
            filetypes=[("File CSV", "*.csv")],
        )
        if destinazione:
            movimenti = self._movimenti_filtrati()
            esporta_csv(movimenti, Path(destinazione))
            messagebox.showinfo("Esporta", f"Esportati {len(movimenti)} movimenti.")

    # --- Aggiornamento della vista ------------------------------------------------------

    def _movimenti_filtrati(self):
        mese = self.mesi_disponibili.get(self.filtro_mese.get())
        categoria = self.filtro_categoria.get()
        return self.registro.filtra(mese=mese, categoria=None if categoria in ("", TUTTE) else categoria)

    def aggiorna(self) -> None:
        categorie = sorted({m.categoria for m in self.registro.movimenti})
        self.categoria["values"] = categorie
        self.filtro_categoria["values"] = [TUTTE, *categorie]
        if self.filtro_categoria.get() not in self.filtro_categoria["values"]:
            self.filtro_categoria.set(TUTTE)

        mesi = sorted({(m.data.year, m.data.month) for m in self.registro.movimenti}, reverse=True)
        self.mesi_disponibili = {nome_mese(*m): m for m in mesi}
        self.filtro_mese["values"] = [TUTTI, *self.mesi_disponibili]
        if self.filtro_mese.get() not in self.filtro_mese["values"]:
            self.filtro_mese.set(TUTTI)

        movimenti = self._movimenti_filtrati()
        self.tabella.delete(*self.tabella.get_children())
        for m in reversed(movimenti):
            segno = "+" if m.tipo == ENTRATA else "-"
            self.tabella.insert("", "end", iid=str(m.id), tags=(m.tipo,), values=(
                m.data.strftime("%d/%m/%Y"), m.tipo, segno + euro(m.importo), m.categoria, m.descrizione))

        self.r = riepilogo(movimenti)
        self.totali["entrate"].configure(text=euro(self.r.entrate), foreground=VERDE)
        self.totali["uscite"].configure(text=euro(self.r.uscite), foreground=ROSSO)
        self.totali["saldo"].configure(text=euro(self.r.saldo), foreground=VERDE if self.r.saldo >= 0 else ROSSO)
        self._disegna_grafico()

    def _disegna_grafico(self) -> None:
        c = self.grafico
        c.delete("all")
        if not self.r.per_categoria:
            c.create_text(10, 10, anchor="nw", text="Nessuna uscita.", fill="gray")
            return
        larghezza = max(c.winfo_width(), 200)
        massimo = max(self.r.per_categoria.values())
        y = 4
        for categoria, totale in self.r.per_categoria.items():
            quota = totale / self.r.uscite * 100
            c.create_text(0, y, anchor="nw", text=categoria)
            c.create_text(larghezza - 2, y, anchor="ne", text=f"{euro(totale)}  ({quota:.0f}%)")
            lunghezza = float(totale / massimo) * (larghezza - 4)
            c.create_rectangle(0, y + 18, max(lunghezza, 2), y + 28, fill=COLORE_BARRE, outline="")
            y += 40


def main(percorso: Path | None = None) -> None:
    root = tk.Tk()
    App(root, Registro(percorso or percorso_predefinito()))
    root.mainloop()


if __name__ == "__main__":
    main()
