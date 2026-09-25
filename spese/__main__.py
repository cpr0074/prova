import sys

from spese.cli import main

# Senza argomenti si apre la finestra grafica.
sys.exit(main(sys.argv[1:] or ["finestra"]))
