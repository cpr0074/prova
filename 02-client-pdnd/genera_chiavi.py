"""Genera la coppia di chiavi RSA da usare con il client PDND.

Equivale ai comandi openssl indicati nel manuale PDND:
    openssl genrsa -out chiave.rsa.pem 2048
    openssl rsa -in chiave.rsa.pem -pubout -out chiave.pub.pem
    openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in chiave.rsa.pem -out chiave.priv

Uso:  python genera_chiavi.py [cartella] [--forza]
"""

import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def genera(cartella: Path, forza: bool = False) -> tuple[Path, Path]:
    privata = cartella / "privata.pem"
    pubblica = cartella / "pubblica.pem"
    if privata.exists() and not forza:
        raise FileExistsError(f"{privata} esiste già: usa --forza per sovrascriverla")

    chiave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cartella.mkdir(parents=True, exist_ok=True)
    privata.write_bytes(chiave.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    os.chmod(privata, 0o600)  # leggibile solo dal proprietario (ignorato su Windows)
    pubblica.write_bytes(chiave.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    return privata, pubblica


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cartella", nargs="?", default="chiavi", type=Path)
    parser.add_argument("--forza", action="store_true", help="sovrascrive le chiavi esistenti")
    args = parser.parse_args()

    privata, pubblica = genera(args.cartella, args.forza)
    print(f"Chiave privata: {privata}  (non condividerla, non caricarla su Git)")
    print(f"Chiave pubblica: {pubblica}  (questa va caricata sul client nel back office PDND)")
