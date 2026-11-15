import re
import unicodedata


def sem_acento(texto: str) -> str:
    """Minúsculas e sem acento, para comparar palavra-chave sem depender de grafia."""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def limpa(texto: str) -> str:
    """Tira espaço repetido e quebra de linha."""
    return re.sub(r"\s+", " ", texto).strip()
