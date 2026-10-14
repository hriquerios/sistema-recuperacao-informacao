# -*- coding: utf-8 -*-
"""
Módulo 1b — Pré-processamento.

Recebe o texto do resumo e o transforma em um vetor de palavras:
  1) separa as palavras (hífen interno faz parte da palavra, ex.: "espaço-temporais");
  2) normaliza (minúsculas, mantendo a acentuação);
  3) compara cada palavra com a lista de stopwords e elimina as que constarem nela.
"""

import re
import unicodedata

# Palavra = sequência de letras/dígitos, podendo conter hífen internamente.
# Tokens sem nenhuma letra (números como "2025", "80") são descartados.
_PADRAO_PALAVRA = re.compile(r"[^\W_]+(?:-[^\W_]+)*")

# Termos adicionais eliminados por serem genéricos e muito frequentes em
# QUALQUER resumo desta área (Engenharia de Dados), não ajudando a
# diferenciar um documento do outro no modelo de espaço vetorial.
# Para usar somente a lista fornecida, basta esvaziar este conjunto.
STOPWORDS_EXPANSAO_AREA = {
    "dados", "dado", "sistema", "sistemas", "informação", "informações",
    "artigo", "trabalho", "trabalhos", "resultado", "resultados",
    "proposta", "propõe", "propomos", "estudo", "estudos", "apresenta",
    "apresentamos", "utiliza", "utilizamos", "possível", "forma",
}


def normalizar(palavra: str) -> str:
    """Minúsculas, mantendo acentuação (forma Unicode NFC)."""
    return unicodedata.normalize("NFC", palavra).lower()


def carregar_stopwords(caminho_arquivo: str) -> set:
    """
    Carrega a lista de stopwords fornecida (uma por linha) e soma a expansão
    da área. O arquivo fornecido está salvo em ISO-8859-1 (Latin-1), não em
    UTF-8: tentamos UTF-8 primeiro (caso alguém salve o arquivo novamente) e
    caímos para Latin-1 automaticamente caso contrário.
    """
    try:
        with open(caminho_arquivo, encoding="utf-8") as f:
            linhas = f.read().splitlines()
    except UnicodeDecodeError:
        with open(caminho_arquivo, encoding="iso-8859-1") as f:
            linhas = f.read().splitlines()
    base = {normalizar(linha.strip()) for linha in linhas if linha.strip()}
    return base | {normalizar(p) for p in STOPWORDS_EXPANSAO_AREA}


def tokenizar(texto: str) -> list:
    """Transforma o texto em um vetor de palavras (normalizadas)."""
    return [normalizar(p) for p in _PADRAO_PALAVRA.findall(texto)
            if any(c.isalpha() for c in p)]


def remover_stopwords(palavras: list, stopwords: set) -> list:
    """Elimina do vetor as stopwords e as palavras de uma letra só."""
    return [p for p in palavras if p not in stopwords and len(p) > 1]
