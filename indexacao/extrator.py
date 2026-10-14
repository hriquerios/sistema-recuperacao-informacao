# -*- coding: utf-8 -*-
"""
Módulo 1a — Extração.

Lê cada artigo diretamente do arquivo PDF (pasta artigos/) e extrai:
  1) Título      -> linhas com a maior fonte da primeira página;
  2) Autor(es)   -> linhas logo abaixo do título, antes das afiliações;
  3) Resumo      -> trecho entre "Resumo." e o próximo marcador de fim
                    (Abstract, Palavras-chave, Introdução, rodapé...).

Correção de acentos dos PDFs gerados em LaTeX:
    Muitos PDFs da SBC (template LaTeX) guardam os acentos como caracteres
    separados da letra: "n˜ao", "´e", "an´alise", "c¸˜ao". A função
    `corrigir_acentos` recompõe esses pares ("não", "é", "análise", "ção").
    Os PDFs gerados no Word já vêm com os acentos corretos e não são afetados.
    Depois da correção, `validar_qualidade_texto` confere se sobrou algum
    acento solto, para sinalizar extrações que precisem de revisão manual.
"""

import re
import unicodedata

import pymupdf

# Acento "solto" (espaçado) -> acento combinante Unicode equivalente
_ACENTOS_SOLTOS = {
    "´": "́",  # agudo      (´a -> á)
    "`": "̀",  # grave      (`a -> à)
    "˜": "̃",  # til        (˜a -> ã)
    "ˆ": "̂",  # circunflexo(ˆe -> ê)
    "¨": "̈",  # trema      (¨u -> ü)
    "ˇ": "̌",  # caron      (ˇz -> ž)
}
_PADRAO_ACENTO_ANTES = re.compile(r"([´`˜ˆ¨ˇ])([A-Za-zı])")
# A cedilha vem DEPOIS da letra: "c¸" -> "ç"
_PADRAO_CEDILHA = re.compile(r"([cC])¸")

# O resumo em português começa com "Resumo." (ou "Resumo:") no início da linha
_PADRAO_INICIO_RESUMO = re.compile(r"^\s*Resumo\s*[.:—–-]", re.MULTILINE)

# Marcadores que indicam o FIM do resumo
_MARCADORES_FIM_RESUMO = [
    r"^\s*Abstract\s*[.:—–-]",
    r"^\s*Palavras[- ]?chave",
    r"^\s*Keywords",
    r"^\s*1\.?\s*Introdu",
    r"^\s*(Companion\s+)?Proceedings of",
]

# Palavras que indicam linha de afiliação/e-mail (fim da lista de autores)
_PADRAO_AFILIACAO = re.compile(
    r"@|Universi|Institut|Departament|Faculdade|Laborat|Escola|Centro|"
    r"Abstract|Resumo",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Limpeza de texto
# ---------------------------------------------------------------------------

def corrigir_acentos(texto: str) -> str:
    """Recompõe acentos desencaixados ("n˜ao" -> "não", "c¸˜ao" -> "ção")."""
    texto = _PADRAO_CEDILHA.sub(lambda m: m.group(1) + "̧", texto)
    texto = _PADRAO_ACENTO_ANTES.sub(
        lambda m: m.group(2).replace("ı", "i") + _ACENTOS_SOLTOS[m.group(1)],
        texto,
    )
    # NFKC junta letra + acento combinante ("a" + "̃" -> "ã") e também
    # desfaz ligaduras tipográficas ("ﬁ" -> "fi", "ﬂ" -> "fl")
    return unicodedata.normalize("NFKC", texto)


def limpar_texto(texto: str) -> str:
    """Corrige acentos, junta palavras hifenizadas na quebra de linha e
    transforma o texto em uma única linha."""
    texto = texto.replace("​", "").replace("­", "")
    texto = corrigir_acentos(texto)
    # "en-\ncontrar" -> "encontrar" (hifenização de fim de linha)
    texto = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
    return re.sub(r"\s+", " ", texto).strip()


# ---------------------------------------------------------------------------
# Título e autores (a partir das fontes da primeira página)
# ---------------------------------------------------------------------------

def _linhas_primeira_pagina(pagina) -> list:
    """Lista as linhas da página como (texto, tamanho_da_fonte), descartando
    os sobrescritos (números de afiliação, asteriscos de nota de rodapé)."""
    linhas = []
    for bloco in pagina.get_text("dict")["blocks"]:
        for linha in bloco.get("lines", []):
            spans = [s for s in linha["spans"]
                     if s["text"].strip() and not s["flags"] & 1]  # 1 = sobrescrito
            if not spans:
                continue
            # Junta os trechos inserindo espaço apenas quando há distância
            # visual entre eles (alguns PDFs separam cada palavra num trecho)
            texto = spans[0]["text"]
            for anterior, atual in zip(spans, spans[1:]):
                distancia = atual["bbox"][0] - anterior["bbox"][2]
                separador = " " if distancia > 0.15 * atual["size"] else ""
                texto += separador + atual["text"]
            tamanho = max(s["size"] for s in spans)
            primeiro_tamanho = spans[0]["size"]
            linhas.append((texto, tamanho, primeiro_tamanho))
    return linhas


def extrair_titulo_autores(pagina) -> dict:
    """
    Título = linhas consecutivas com a maior fonte da página (≈16pt no
    template da SBC). Autores = linhas seguintes, até a primeira linha de
    afiliação (que começa com um marcador pequeno, ex.: "1", ou contém
    "Universidade", "Instituto", "@"...).
    """
    linhas = _linhas_primeira_pagina(pagina)
    if not linhas:
        return {"titulo": "", "autores": ""}

    maior_fonte = max(tam for _, tam, _ in linhas)
    inicio = next(i for i, (_, tam, _) in enumerate(linhas) if tam >= maior_fonte - 0.5)

    titulo_partes, i = [], inicio
    while i < len(linhas) and linhas[i][1] >= maior_fonte - 0.5:
        titulo_partes.append(linhas[i][0])
        i += 1

    autores_partes = []
    while i < len(linhas):
        texto, _, primeiro_tamanho = linhas[i]
        if primeiro_tamanho < 10 or _PADRAO_AFILIACAO.search(texto):
            break
        autores_partes.append(texto)
        i += 1

    titulo = limpar_texto(" ".join(titulo_partes))
    nomes = limpar_texto(", ".join(autores_partes)).split(",")
    autores = "; ".join(n.strip() for n in nomes if n.strip())
    return {"titulo": titulo, "autores": autores}


# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------

def extrair_resumo(texto_pagina: str) -> dict:
    """
    Isola o resumo em português: começa após "Resumo." e termina no primeiro
    marcador de fim encontrado (Abstract, Palavras-chave, Introdução ou o
    rodapé "Proceedings of...").
    """
    inicio = _PADRAO_INICIO_RESUMO.search(texto_pagina)
    if not inicio:
        return {"resumo": "", "fim_encontrado": False}

    trecho = texto_pagina[inicio.end():]
    fim = len(trecho)
    for padrao in _MARCADORES_FIM_RESUMO:
        m = re.search(padrao, trecho, re.MULTILINE | re.IGNORECASE)
        if m and m.start() < fim:
            fim = m.start()

    return {"resumo": limpar_texto(trecho[:fim]), "fim_encontrado": fim < len(trecho)}


def validar_qualidade_texto(resumo: str, fim_encontrado: bool) -> dict:
    """Aponta problemas na extração que exigem revisão manual."""
    problemas = []
    if not resumo:
        problemas.append("resumo não encontrado")
    else:
        if not fim_encontrado:
            problemas.append("fim do resumo não identificado (pode conter texto a mais)")
        restantes = re.findall(r"[´`˜ˆ¨ˇ¸]", resumo)
        if restantes:
            problemas.append(f"{len(restantes)} acento(s) solto(s) não corrigido(s)")
    return {"ok": not problemas, "problemas": problemas}


# ---------------------------------------------------------------------------
# Pipeline de extração de um artigo
# ---------------------------------------------------------------------------

def processar_artigo(caminho_pdf: str) -> dict:
    """Extrai título, autores e resumo de um artigo em PDF."""
    with pymupdf.open(caminho_pdf) as documento:
        primeira_pagina = documento[0]
        metadados = extrair_titulo_autores(primeira_pagina)
        resumo_info = extrair_resumo(primeira_pagina.get_text())

    qualidade = validar_qualidade_texto(resumo_info["resumo"], resumo_info["fim_encontrado"])
    if not metadados["titulo"]:
        qualidade["ok"] = False
        qualidade["problemas"].append("título não identificado")
    if not metadados["autores"]:
        qualidade["ok"] = False
        qualidade["problemas"].append("autores não identificados")

    return {
        "titulo": metadados["titulo"],
        "autores": metadados["autores"],
        "resumo": resumo_info["resumo"],
        "qualidade": qualidade,
    }
