# -*- coding: utf-8 -*-
"""
Módulo 1 — Extração + Indexação (SRI Simplificado, área: Engenharia de Dados).

Para cada artigo em PDF da pasta artigos/ (DocId atribuído pela ordem
alfabética do nome do arquivo):
    1. Extração          (extrator.py)      -> título, autor(es) e resumo lidos do PDF
    2. Pré-processamento (preprocessador.py) -> vetor de palavras sem stopwords
    3. Indexação         (indexador.py)     -> <Termo, Freq> por documento + dicionário
    4. Catalogação       (catalogador.py)   -> tabela de documentos + registro <DocId, TotPal>

Saída gerada em ./saida/:
    - vocabulario/doc_XX.txt    vocabulário controlado de cada documento <Termo, Freq>
    - dicionario_termos.txt     dicionário de termos da coleção (total de ocorrências)
    - tabela_documentos.csv     <DocId, Título, Autor, Total de termos significativos>
    - registro_totpal.txt       <DocId, TotPal> (último identificador e total de palavras)
    - resumos/doc_XX.txt        resumo extraído de cada PDF (para conferência)
    - relatorio_extracao.txt    somente se algum PDF apresentar problema na extração

Uso:
    python main.py
"""

import glob
import os
from collections import Counter

from extrator import processar_artigo
from preprocessador import carregar_stopwords, tokenizar, remover_stopwords
from indexador import contar_frequencias, gravar_vocabulario_documento, gravar_dicionario_global
from catalogador import gravar_tabela_documentos, gravar_registro_totpal

PASTA_ARTIGOS = "artigos"
PASTA_SAIDA = "saida"
PASTA_VOCABULARIO = os.path.join(PASTA_SAIDA, "vocabulario")
PASTA_RESUMOS = os.path.join(PASTA_SAIDA, "resumos")
ARQUIVO_STOPWORDS = "stopwords.txt"


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)  # permite rodar o script a partir de qualquer pasta

    pdfs = sorted(glob.glob(os.path.join(PASTA_ARTIGOS, "*.pdf")))
    if not pdfs:
        print(f"Nenhum PDF encontrado em ./{PASTA_ARTIGOS}/")
        return

    os.makedirs(PASTA_RESUMOS, exist_ok=True)
    stopwords = carregar_stopwords(ARQUIVO_STOPWORDS)

    dicionario_global = Counter()
    registros = []
    avisos = []

    for doc_id, caminho_pdf in enumerate(pdfs, start=1):
        nome_arquivo = os.path.basename(caminho_pdf)
        print(f"[{doc_id:02d}/{len(pdfs)}] {nome_arquivo}")

        try:
            info = processar_artigo(caminho_pdf)
        except Exception as e:
            print(f"    ERRO: {e}")
            avisos.append(f"DocId {doc_id} ({nome_arquivo}): falha na leitura do PDF — {e}")
            continue

        if not info["qualidade"]["ok"]:
            aviso = f"DocId {doc_id} ({nome_arquivo}): " + "; ".join(info["qualidade"]["problemas"])
            avisos.append(aviso)
            print(f"    AVISO: {aviso}")

        with open(os.path.join(PASTA_RESUMOS, f"doc_{doc_id:02d}.txt"), "w", encoding="utf-8") as f:
            f.write(info["resumo"] + "\n")

        palavras = tokenizar(info["resumo"])                # vetor de palavras
        termos = remover_stopwords(palavras, stopwords)     # termos significativos
        frequencias = contar_frequencias(termos)            # <Termo, Freq>

        gravar_vocabulario_documento(doc_id, frequencias, PASTA_VOCABULARIO)
        dicionario_global.update(frequencias)

        registros.append({
            "doc_id": doc_id,
            "titulo": info["titulo"],
            "autores": info["autores"],
            "total_palavras": len(palavras),
            "total_termos_significativos": len(termos),
        })

    gravar_dicionario_global(dicionario_global, PASTA_SAIDA)
    gravar_tabela_documentos(registros, PASTA_SAIDA)
    gravar_registro_totpal(registros, PASTA_SAIDA)

    caminho_relatorio = os.path.join(PASTA_SAIDA, "relatorio_extracao.txt")
    if avisos:
        with open(caminho_relatorio, "w", encoding="utf-8") as f:
            f.write("Documentos com problema na extração (revisar manualmente):\n\n")
            f.write("\n".join(avisos) + "\n")
        print(f"\n{len(avisos)} aviso(s) — ver {caminho_relatorio}")
    elif os.path.exists(caminho_relatorio):
        os.remove(caminho_relatorio)

    print(f"\nConcluído: {len(registros)}/{len(pdfs)} documentos indexados, "
          f"{len(dicionario_global)} termos distintos na coleção. Saída em ./{PASTA_SAIDA}/")


if __name__ == "__main__":
    main()
