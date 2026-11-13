import hashlib
from pathlib import Path
def vig(text,key):
    out=[]; j=0
    for c in text:
        if c.isalpha():
            b=ord("A") if c.isupper() else ord("a")
            out.append(chr((ord(c)-b-(ord(key[j%len(key)])-ord("A")))%26+b)); j+=1
        else: out.append(c)
    return "".join(out)
def solve():
    path=Path(__file__).parents[1]/"dist/shield_phase.bin"
    blob=bytes.fromhex(path.read_text().strip())
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.padding import PKCS7
    decryptor=Cipher(algorithms.AES(hashlib.md5(b"shield").digest()),modes.ECB()).decryptor()
    padded=decryptor.update(blob)+decryptor.finalize()
    unpadder=PKCS7(128).unpadder()
    dec=(unpadder.update(padded)+unpadder.finalize()).decode()
    import re
    return re.search(r"flag\{[^}]+\}",vig(dec,"MICROBOT")).group()
