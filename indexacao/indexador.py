# -*- coding: utf-8 -*-
"""
Módulo 1c — Indexação.

Recebe o vetor de termos significativos de um documento e:
  1) elimina as repetições contabilizando a frequência de cada termo;
  2) grava o vocabulário controlado do documento em um .txt, formato <Termo, Freq>;
  3) acumula as frequências no dicionário de termos da coleção
     (quantidade TOTAL de ocorrências de cada termo, somando todos os docs).
"""

import os
from collections import Counter


def contar_frequencias(termos: list) -> Counter:
    """Elimina as repetições do vetor, contabilizando a frequência de cada termo."""
    return Counter(termos)


def _ordenar(frequencias: Counter) -> list:
    """Frequência decrescente; empates em ordem alfabética."""
    return sorted(frequencias.items(), key=lambda x: (-x[1], x[0]))


def gravar_vocabulario_documento(doc_id: int, frequencias: Counter, pasta: str) -> str:
    """Grava o vocabulário controlado de UM documento, formato <Termo, Freq>."""
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"doc_{doc_id:02d}.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        for termo, freq in _ordenar(frequencias):
            f.write(f"<{termo}, {freq}>\n")
    return caminho


def gravar_dicionario_global(dicionario_global: Counter, pasta: str) -> str:
    """Grava o dicionário de termos da coleção com a quantidade TOTAL de ocorrências."""
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "dicionario_termos.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        for termo, freq in _ordenar(dicionario_global):
            f.write(f"<{termo}, {freq}>\n")
    return caminho
