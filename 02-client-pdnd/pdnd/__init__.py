"""Client minimale per fruire degli e-service tramite PDND Interoperabilità."""

from pdnd.client import ClientEService
from pdnd.config import Config
from pdnd.voucher import ErrorePDND, Voucher, crea_client_assertion, richiedi_voucher

__all__ = ["ClientEService", "Config", "ErrorePDND", "Voucher", "crea_client_assertion", "richiedi_voucher"]
