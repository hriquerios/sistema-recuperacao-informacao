# -*- coding: utf-8 -*-
"""
Módulo 2e — Interface gráfica de busca (Tkinter, desktop).

Aba "Busca":
    - o usuário digita a consulta e escolhe o modelo (Booleano ou Espaço Vetorial);
    - a consulta é processada como na indexação (os termos usados e as stopwords
      descartadas aparecem logo abaixo da caixa de busca);
    - os resultados aparecem ordenados por relevância (Título e Autor);
    - ao clicar em um resultado, o painel da direita mostra os detalhes
      (DocId, autores, resumo com os termos da consulta destacados e o cálculo
      da similaridade no modelo vetorial);
    - o botão "Abrir documento" (ou duplo clique) abre o PDF original.

Aba "Consultas de teste":
    - executa as 5 consultas fixas nos dois modelos e mostra precisão e
      revocação calculadas sobre o julgamento de relevância feito a priori.
"""

import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import consultas_teste
import modelo_booleano
from colecao import Colecao, PASTA_RECUPERACAO
from modelo_vetorial import ModeloVetorial

MODELO_BOOLEANO = "booleano"
MODELO_VETORIAL = "vetorial"

AJUDA = {
    MODELO_BOOLEANO: ("Operadores: AND, OR, NOT (ou E, OU, NÃO em maiúsculas) e parênteses para aninhar. "
                      "Termos lado a lado = AND.   Ex.: (nosql OR newsql) AND NOT levantamento"),
    MODELO_VETORIAL: ("Digite palavras-chave ou uma frase. Peso TF-IDF (tf = 1 + log2 f, idf = log2 N/n) "
                      "e similaridade do cosseno.   Ex.: governança de dados em data lakes"),
}

# Mesmo padrão de palavra do pré-processador (usado para destacar termos no resumo)
_PADRAO_PALAVRA = re.compile(r"[^\W_]+(?:-[^\W_]+)*")


def abrir_arquivo(caminho: str):
    """Abre o arquivo com o programa padrão do sistema operacional (leitor de PDF)."""
    if sys.platform.startswith("win"):
        os.startfile(caminho)  # noqa: S606 - abre com o aplicativo associado ao .pdf
    elif sys.platform == "darwin":
        subprocess.Popen(["open", caminho])
    else:
        subprocess.Popen(["xdg-open", caminho])


class AplicacaoSRI(tk.Tk):
    """Janela principal do SRI."""

    def __init__(self):
        super().__init__()
        self.title("SRI — Engenharia de Dados (Módulo 2: Recuperação de Informações)")
        self.geometry("1280x760")
        self.minsize(980, 600)

        # Carrega a coleção indexada (indexacao/) e pré-calcula os pesos do modelo vetorial
        self.colecao = Colecao()
        self.modelo_vetorial = ModeloVetorial(self.colecao)

        self.modelo_escolhido = tk.StringVar(value=MODELO_VETORIAL)
        self.ultima_busca = None       # resultado da última busca (para o painel de detalhes)
        self.resultados_teste = []     # resultados das 5 consultas de teste

        self._configurar_estilo()
        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True, padx=8, pady=8)
        abas.add(self._montar_aba_busca(abas), text="  Busca  ")
        abas.add(self._montar_aba_testes(abas), text="  Consultas de teste  ")

        self._atualizar_ajuda()
        self.campo_consulta.focus_set()

    def _configurar_estilo(self):
        """Fontes e espaçamentos dos widgets ttk."""
        estilo = ttk.Style(self)
        if "vista" in estilo.theme_names():
            estilo.theme_use("vista")
        estilo.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        estilo.configure("Ajuda.TLabel", foreground="#555555")
        estilo.configure("Info.TLabel", foreground="#1a5fb4")

    # ==================================================================
    # Aba "Busca"
    # ==================================================================

    def _montar_aba_busca(self, pai):
        """Monta a caixa de consulta, a escolha do modelo, a lista de resultados e os detalhes."""
        aba = ttk.Frame(pai, padding=8)

        # --- Linha da consulta
        linha = ttk.Frame(aba)
        linha.pack(fill="x")
        ttk.Label(linha, text="Consulta:", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.campo_consulta = ttk.Entry(linha, font=("Segoe UI", 12))
        self.campo_consulta.pack(side="left", fill="x", expand=True, padx=6)
        self.campo_consulta.bind("<Return>", lambda _e: self.buscar())
        ttk.Button(linha, text="Buscar", command=self.buscar).pack(side="left")

        # --- Escolha do modelo + atalho para carregar uma consulta de teste
        linha_modelo = ttk.Frame(aba)
        linha_modelo.pack(fill="x", pady=(6, 0))
        ttk.Label(linha_modelo, text="Modelo:").pack(side="left")
        for texto, valor in (("Espaço Vetorial", MODELO_VETORIAL), ("Booleano", MODELO_BOOLEANO)):
            ttk.Radiobutton(linha_modelo, text=texto, value=valor, variable=self.modelo_escolhido,
                            command=self._atualizar_ajuda).pack(side="left", padx=6)

        self.combo_testes = ttk.Combobox(
            linha_modelo, state="readonly", width=48,
            values=[f"{t['id']} — {t['nome']}" for t in consultas_teste.CONSULTAS_TESTE])
        self.combo_testes.set("Carregar consulta de teste...")
        self.combo_testes.bind("<<ComboboxSelected>>", self._carregar_consulta_teste)
        self.combo_testes.pack(side="right")

        self.rotulo_ajuda = ttk.Label(aba, style="Ajuda.TLabel")
        self.rotulo_ajuda.pack(fill="x", pady=(4, 0))
        self.rotulo_info = ttk.Label(aba, style="Info.TLabel", wraplength=1200)
        self.rotulo_info.pack(fill="x", pady=(2, 6))

        # --- Resultados (esquerda) e detalhes (direita)
        divisor = ttk.PanedWindow(aba, orient="horizontal")
        divisor.pack(fill="both", expand=True)

        quadro_resultados = ttk.Frame(divisor)
        colunas = ("pos", "relevancia", "titulo", "autores")
        self.lista = ttk.Treeview(quadro_resultados, columns=colunas, show="headings", selectmode="browse")
        for col, titulo, largura, esticar in (("pos", "#", 40, False), ("relevancia", "Relevância", 90, False),
                                              ("titulo", "Título", 380, True), ("autores", "Autor(es)", 240, True)):
            self.lista.heading(col, text=titulo)
            self.lista.column(col, width=largura, stretch=esticar, anchor="center" if not esticar else "w")
        barra = ttk.Scrollbar(quadro_resultados, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        self.lista.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.lista.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_detalhes())
        self.lista.bind("<Double-1>", lambda _e: self.abrir_documento())
        divisor.add(quadro_resultados, weight=3)

        quadro_detalhes = ttk.Frame(divisor)
        self.texto_detalhes = self._criar_caixa_texto(quadro_detalhes)
        self.botao_abrir = ttk.Button(quadro_detalhes, text="Abrir documento (PDF)",
                                      command=self.abrir_documento, state="disabled")
        self.botao_abrir.pack(fill="x", pady=(6, 0))
        divisor.add(quadro_detalhes, weight=2)

        self._escrever(self.texto_detalhes, [("Digite uma consulta e clique em Buscar.\n\n", "normal"),
                                             ("Clique em um resultado para ver os detalhes; "
                                              "dê duplo clique para abrir o PDF.", "suave")])
        return aba

    def _criar_caixa_texto(self, pai):
        """Caixa de texto somente leitura com barra de rolagem e estilos de formatação."""
        quadro = ttk.Frame(pai)
        quadro.pack(fill="both", expand=True)
        texto = tk.Text(quadro, wrap="word", font=("Segoe UI", 10), padx=10, pady=8,
                        relief="flat", background="#fbfbfb", state="disabled")
        barra = ttk.Scrollbar(quadro, orient="vertical", command=texto.yview)
        texto.configure(yscrollcommand=barra.set)
        texto.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        texto.tag_configure("titulo", font=("Segoe UI", 13, "bold"), spacing3=6)
        texto.tag_configure("rotulo", font=("Segoe UI", 10, "bold"))
        texto.tag_configure("normal", font=("Segoe UI", 10))
        texto.tag_configure("suave", font=("Segoe UI", 9), foreground="#666666")
        texto.tag_configure("mono", font=("Consolas", 9))
        texto.tag_configure("destaque", background="#ffe066", font=("Segoe UI", 10, "bold"))
        return texto

    @staticmethod
    def _escrever(caixa, trechos):
        """Substitui o conteúdo da caixa por uma lista de (texto, estilo)."""
        caixa.configure(state="normal")
        caixa.delete("1.0", "end")
        for texto, estilo in trechos:
            caixa.insert("end", texto, estilo)
        caixa.configure(state="disabled")
        caixa.yview_moveto(0)

    def _atualizar_ajuda(self):
        """Mostra a sintaxe aceita pelo modelo selecionado."""
        self.rotulo_ajuda.configure(text=AJUDA[self.modelo_escolhido.get()])

    def _carregar_consulta_teste(self, _evento=None):
        """Preenche a caixa com a consulta de teste escolhida (na versão do modelo selecionado) e busca."""
        teste = consultas_teste.CONSULTAS_TESTE[self.combo_testes.current()]
        self.campo_consulta.delete(0, "end")
        self.campo_consulta.insert(0, teste[self.modelo_escolhido.get()])
        self.buscar()

    # ------------------------------------------------------------------
    # Execução da busca
    # ------------------------------------------------------------------

    def buscar(self):
        """Processa a consulta no modelo escolhido e preenche a lista de resultados."""
        consulta = self.campo_consulta.get().strip()
        if not consulta:
            return
        modelo = self.modelo_escolhido.get()

        try:
            if modelo == MODELO_BOOLEANO:
                resultado = modelo_booleano.buscar(consulta, self.colecao)
            else:
                resultado = self.modelo_vetorial.buscar(consulta)
        except modelo_booleano.ErroConsulta as erro:
            messagebox.showerror("Consulta inválida", str(erro))
            return
        resultado["modelo"] = modelo
        self.ultima_busca = resultado

        # Linha informativa: como a consulta foi processada
        partes = [f"Termos processados: {', '.join(resultado['termos']) or '(nenhum)'}"]
        if resultado["ignorados"]:
            partes.append(f"descartados (stopwords): {', '.join(resultado['ignorados'])}")
        if modelo == MODELO_BOOLEANO:
            partes.append(f"expressão: {resultado['expressao']}")
        elif resultado["fora_vocab"]:
            partes.append(f"fora do vocabulário: {', '.join(resultado['fora_vocab'])}")
        partes.append(f"{len(resultado['resultados'])} documento(s) recuperado(s)")
        self.rotulo_info.configure(text="   |   ".join(partes))

        # Lista de resultados (vetorial: ordem de similaridade; booleano: todos com relevância 1)
        self.lista.delete(*self.lista.get_children())
        for pos, (doc_id, relevancia) in enumerate(resultado["resultados"], start=1):
            doc = self.colecao.documentos[doc_id]
            texto_relevancia = f"{relevancia:.4f}" if modelo == MODELO_VETORIAL else "satisfaz"
            self.lista.insert("", "end", iid=str(doc_id),
                              values=(pos, texto_relevancia, doc["titulo"], doc["autores"].replace(";", ",")))

        self.botao_abrir.configure(state="disabled")
        if resultado["resultados"]:
            self._escrever(self.texto_detalhes, [("Clique em um resultado para ver os detalhes.", "suave")])
        else:
            self._escrever(self.texto_detalhes, [("Nenhum documento recuperado.\n\n", "titulo"),
                                                 ("Nenhum documento da coleção satisfaz a consulta.", "normal")])

    # ------------------------------------------------------------------
    # Painel de detalhes e abertura do documento
    # ------------------------------------------------------------------

    def _doc_selecionado(self):
        """DocId do resultado selecionado na lista (ou None)."""
        selecao = self.lista.selection()
        return int(selecao[0]) if selecao else None

    def _mostrar_detalhes(self):
        """Mostra título, autores, resumo (com termos destacados) e a justificativa da relevância."""
        doc_id = self._doc_selecionado()
        if doc_id is None or self.ultima_busca is None:
            return
        doc = self.colecao.documentos[doc_id]
        busca = self.ultima_busca
        termos_consulta = set(busca["termos"])

        trechos = [(doc["titulo"] + "\n", "titulo"),
                   ("Autor(es): ", "rotulo"), (doc["autores"].replace(";", ",") + "\n", "normal"),
                   ("DocId: ", "rotulo"), (f"{doc_id}    ", "normal"),
                   ("Termos significativos: ", "rotulo"), (f"{doc['total_termos']}\n", "normal"),
                   ("Arquivo: ", "rotulo"), (os.path.basename(doc["pdf"] or "(não encontrado)") + "\n\n", "suave")]

        # Por que o documento foi recuperado
        if busca["modelo"] == MODELO_VETORIAL:
            sim = dict(busca["resultados"])[doc_id]
            trechos += [("Similaridade do cosseno: ", "rotulo"), (f"{sim:.4f}\n", "normal")]
            linhas = self.modelo_vetorial.explicar(doc_id, busca["vetor_q"])
            tabela = f"{'termo':<16}{'f':>3}{'tf':>7}{'idf':>7}{'w doc':>8}{'w cons':>8}{'w·w':>8}\n"
            for termo, f, tf, idf, w_d, w_q, prod in linhas:
                tabela += f"{termo[:15]:<16}{f:>3}{tf:>7.3f}{idf:>7.3f}{w_d:>8.3f}{w_q:>8.3f}{prod:>8.3f}\n"
            tabela += (f"|d| = {self.modelo_vetorial.normas[doc_id]:.3f}   |q| = {busca['norma_q']:.3f}   "
                       f"sim = Σ w·w / (|d|·|q|)\n\n")
            trechos.append((tabela, "mono"))
        else:
            vocab = self.colecao.vocabulario[doc_id]
            presentes = [f"{t} (f={vocab[t]})" for t in busca["termos"] if t in vocab]
            ausentes = [t for t in busca["termos"] if t not in vocab]
            trechos += [("Expressão satisfeita: ", "rotulo"), (busca["expressao"] + "\n", "normal"),
                        ("Termos presentes: ", "rotulo"), ((", ".join(presentes) or "—") + "\n", "normal"),
                        ("Termos ausentes: ", "rotulo"), ((", ".join(ausentes) or "—") + "\n\n", "normal")]

        # Resumo com os termos da consulta destacados
        trechos.append(("Resumo\n", "rotulo"))
        resumo = doc["resumo"]
        inicio = 0
        for m in _PADRAO_PALAVRA.finditer(resumo):
            if m.group().lower() in termos_consulta:
                trechos += [(resumo[inicio:m.start()], "normal"), (m.group(), "destaque")]
                inicio = m.end()
        trechos.append((resumo[inicio:], "normal"))

        self._escrever(self.texto_detalhes, trechos)
        self.botao_abrir.configure(state="normal" if doc["pdf"] else "disabled")

    def abrir_documento(self):
        """Abre o PDF original do documento selecionado."""
        doc_id = self._doc_selecionado()
        if doc_id is None:
            return
        caminho = self.colecao.documentos[doc_id]["pdf"]
        if not caminho or not os.path.exists(caminho):
            messagebox.showerror("Documento não encontrado", f"PDF do DocId {doc_id} não encontrado.")
            return
        try:
            abrir_arquivo(caminho)
        except OSError as erro:
            messagebox.showerror("Erro ao abrir", str(erro))

    # ==================================================================
    # Aba "Consultas de teste"
    # ==================================================================

    def _montar_aba_testes(self, pai):
        """Tabela com as métricas das 5 consultas fixas + detalhamento da consulta selecionada."""
        aba = ttk.Frame(pai, padding=8)

        topo = ttk.Frame(aba)
        topo.pack(fill="x")
        ttk.Label(topo, text="5 consultas fixas com julgamento de relevância definido a priori. "
                             "Precisão (P) e Revocação (R) de cada modelo:",
                  font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(topo, text="Exportar relatório (.txt)", command=self._exportar_relatorio).pack(side="right")
        ttk.Button(topo, text="Executar testes", command=self._executar_testes).pack(side="right", padx=6)

        k = consultas_teste.K_CORTE
        colunas = ("id", "nome", "relev", "b_rec", "b_p", "b_r", "v_rec", "v_p", "v_r", "v_pk", "v_rk")
        cabecalhos = ("Teste", "Consulta", "Relevantes", "Bool: recup.", "Bool: P", "Bool: R",
                      "Vet: recup.", "Vet: P", "Vet: R", f"Vet: P@{k}", f"Vet: R@{k}")
        self.tabela_testes = ttk.Treeview(aba, columns=colunas, show="headings", height=5, selectmode="browse")
        for col, cab in zip(colunas, cabecalhos):
            self.tabela_testes.heading(col, text=cab)
            largura = 330 if col == "nome" else (60 if col == "id" else 85)
            self.tabela_testes.column(col, width=largura, stretch=(col == "nome"),
                                      anchor="w" if col == "nome" else "center")
        self.tabela_testes.pack(fill="x", pady=6)
        self.tabela_testes.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_teste())

        ttk.Label(aba, text="n/d = indefinida (0/0). Selecione uma linha para ver o gabarito, "
                            "os resultados de cada modelo (✔ relevante / ✘ não relevante) e a análise.",
                  style="Ajuda.TLabel").pack(fill="x")

        self.texto_teste = self._criar_caixa_texto(aba)
        self.texto_teste.configure(font=("Consolas", 10))
        self._executar_testes()
        return aba

    def _executar_testes(self):
        """Roda as 5 consultas nos dois modelos e preenche a tabela de métricas."""
        fmt = consultas_teste.formatar_metrica
        self.resultados_teste = consultas_teste.executar_todos(self.colecao, self.modelo_vetorial)
        self.tabela_testes.delete(*self.tabela_testes.get_children())
        for i, r in enumerate(self.resultados_teste):
            t = r["teste"]
            mb, mv, mk = r["metricas_booleano"], r["metricas_vetorial"], r["metricas_vetorial_k"]
            self.tabela_testes.insert("", "end", iid=str(i), values=(
                t["id"], t["nome"], len(t["relevantes"]),
                mb["recuperados"], fmt(mb["precisao"]), fmt(mb["revocacao"]),
                mv["recuperados"], fmt(mv["precisao"]), fmt(mv["revocacao"]),
                fmt(mk["precisao"]), fmt(mk["revocacao"])))
        self.tabela_testes.selection_set("0")

    def _mostrar_teste(self):
        """Mostra o detalhamento da consulta de teste selecionada."""
        selecao = self.tabela_testes.selection()
        if not selecao:
            return
        texto = consultas_teste.descrever_teste(self.resultados_teste[int(selecao[0])], self.colecao)
        self._escrever(self.texto_teste, [(texto, "mono")])

    def _exportar_relatorio(self):
        """Grava o relatório completo das consultas de teste em recuperacao/saida/."""
        pasta = os.path.join(PASTA_RECUPERACAO, "saida")
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, "avaliacao_consultas_teste.txt")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(consultas_teste.gerar_relatorio(self.colecao, self.modelo_vetorial) + "\n")
        messagebox.showinfo("Relatório exportado", f"Relatório gravado em:\n{caminho}")


def iniciar():
    """Cria e executa a janela principal."""
    AplicacaoSRI().mainloop()
