# -*- coding: utf-8 -*-
"""
Módulo 1d — Catalogação.

Gera:
  - tabela_documentos.csv   <DocId, Título, Autor, Total de termos significativos>
  - registro_totpal.txt     <DocId, TotPal> com o último identificador e o total
                            de palavras
"""

import csv
import os


def gravar_tabela_documentos(registros: list, pasta_saida: str) -> str:
    """
    registros: lista de dicts com doc_id, titulo, autores, total_termos_significativos.
    Gravado em CSV (separador ";", UTF-8 com BOM) para abrir direto no Excel
    ou no Google Planilhas, já que títulos contêm vírgulas.
    """
    os.makedirs(pasta_saida, exist_ok=True)
    caminho = os.path.join(pasta_saida, "tabela_documentos.csv")
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["DocId", "Título", "Autor", "Total de termos significativos"])
        for r in registros:
            escritor.writerow([r["doc_id"], r["titulo"], r["autores"],
                               r["total_termos_significativos"]])
    return caminho


def gravar_registro_totpal(registros: list, pasta_saida: str) -> str:
    """
    Registro de controle <DocId, TotPal>:
      - DocId  = último identificador atribuído (o próximo documento
                 indexado recebe DocId + 1);
      - TotPal = total de palavras da coleção (soma das palavras dos
                 resumos, antes da remoção das stopwords).
    Abaixo do registro vai o detalhamento <DocId, TotPal> de cada documento.
    """
    os.makedirs(pasta_saida, exist_ok=True)
    caminho = os.path.join(pasta_saida, "registro_totpal.txt")
    ultimo_doc_id = max((r["doc_id"] for r in registros), default=0)
    total_palavras = sum(r["total_palavras"] for r in registros)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("# Registro <DocId, TotPal>: último identificador e total de palavras da coleção\n")
        f.write(f"<{ultimo_doc_id}, {total_palavras}>\n\n")
        f.write("# Detalhamento por documento <DocId, TotPal>\n")
        for r in registros:
            f.write(f"<{r['doc_id']}, {r['total_palavras']}>\n")
    return caminho
