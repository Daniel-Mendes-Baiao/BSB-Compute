import time
import os

def ts(elapsed_seconds):
    m = int(elapsed_seconds // 60)
    s = int(elapsed_seconds % 60)
    return f"[{m:02d}:{s:02d}]"

def salvar_relatorio(texto, nome):
    base = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(base, "..", nome)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
