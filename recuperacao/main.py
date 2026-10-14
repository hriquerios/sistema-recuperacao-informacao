# -*- coding: utf-8 -*-
"""
Módulo 2 — Recuperação de Informações (SRI Simplificado, área: Engenharia de Dados).

Abre a interface gráfica de busca. Os índices são lidos da saída da indexação
("../indexacao/saida"), portanto a indexação precisa ter sido executada antes.

    colecao.py          -> carrega tabela de documentos, vocabulários e monta o índice invertido
    modelo_booleano.py  -> AND / OR / NOT com parênteses (operadores aninhados)
    modelo_vetorial.py  -> TF-IDF + similaridade do cosseno
    consultas_teste.py  -> 5 consultas fixas, julgamento a priori, precisão e revocação
    interface.py        -> janela Tkinter (busca + aba de testes)

Uso:
    python main.py
"""

import os

from interface import iniciar

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # permite rodar a partir de qualquer pasta
    iniciar()
