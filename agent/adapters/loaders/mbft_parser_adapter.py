"""
agent/adapters/loaders/mbft_parser_adapter.py

Parser dedicado para o MBFT — Manual Brasileiro de Fiscalização de Trânsito
(Resolução CONTRAN nº 985/2022, docs/MBFT_CONTRAN.pdf).

Resolve os dois desafios centrais do PDF do MBFT:
1. Separa a Parte Geral (págs. 1..23) por seções numeradas (responsabilidade,
   infrações simultâneas/concomitantes, regras de abordagem, AIT).
2. Agrupa todas as páginas pertencentes à mesma Ficha de Fiscalização (~435 fichas),
   extrai as tabelas com PyMuPDF (`page.find_tables()`) sem misturar as 4 colunas
   ('Quando AUTUAR', 'Quando NÃO Autuar', 'Definições e Procedimentos',
   'Exemplos do Campo de Observações do AIT') e gera 1 chunk Markdown estruturado
   por ficha, vinculado ao `artigo` do CTB e ao `codigo_enquadramento`.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import fitz
from loguru import logger

from agent.domain.exceptions import DocumentoNaoEncontradoError
from agent.domain.value_objects.documento_extraido import PaginaExtraida

_MBFT_NORMA = "Resolução CONTRAN nº 985/2022 (MBFT)"
_MBFT_URL = "https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-contran/resolucoes/Resolucao9852022.pdf"

_RE_SECAO_GERAL = re.compile(r"(?m)^(?=\d+\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,})")
_RE_AMPARO_ART = re.compile(
    r"Art\.?\s*(\d+(?:-[A-Z])?)[ºo°]?(?:\s*,\s*([IVXLCDM]+|§\s*\d+[ºo°]?|parágrafo único))?",
    re.IGNORECASE,
)


def _limpar_celula(valor: Any) -> str:
    if not valor:
        return ""
    texto = str(valor).replace("\r\n", "\n").replace("\r", "\n")
    linhas = [re.sub(r"[ \t]+", " ", ln).strip() for ln in texto.split("\n")]
    return "\n".join(ln for ln in linhas if ln).strip()


def _extrair_artigo_inciso(amparo_legal: str) -> tuple[str | None, str | None]:
    m = _RE_AMPARO_ART.search(amparo_legal or "")
    if not m:
        return None, None
    artigo = m.group(1)
    inciso = m.group(2).strip() if m.group(2) else None
    return artigo, inciso


class MBFTParserAdapter:
    """
    Extrai e estrutura o MBFT (Parte Geral + Fichas de Fiscalização) em
    `list[PaginaExtraida]` prontas para indexação no Qdrant.
    """

    def __init__(self, salvar_cache_dir: str | None = None) -> None:
        self._salvar_cache_dir = salvar_cache_dir

    async def carregar_e_estruturar(self, caminho_pdf: str) -> list[PaginaExtraida]:
        """Executa o parsing completo do MBFT de forma assíncrona."""
        return await asyncio.to_thread(self._processar_sync, caminho_pdf)

    def _processar_sync(self, caminho_pdf: str) -> list[PaginaExtraida]:
        path = Path(caminho_pdf)
        if not path.exists():
            raise DocumentoNaoEncontradoError(documento_id=caminho_pdf)

        chunks: list[PaginaExtraida] = []
        fichas_estruturadas: list[dict[str, Any]] = []

        with fitz.open(caminho_pdf) as doc:
            total_paginas = len(doc)
            logger.info(
                "MBFTParserAdapter | abrindo '{}' ({} páginas)...",
                caminho_pdf,
                total_paginas,
            )

            # 1. Identifica em qual página começa a primeira Ficha de Fiscalização
            primeira_ficha_idx = self._encontrar_primeira_ficha(doc)

            # 2. Parte Geral (páginas anteriores à primeira ficha)
            if primeira_ficha_idx > 0:
                chunks_geral = self._extrair_parte_geral(
                    doc, 0, primeira_ficha_idx, caminho_pdf
                )
                chunks.extend(chunks_geral)
                logger.info(
                    "MBFT Parte Geral extraída | páginas=1..{} | chunks={}",
                    primeira_ficha_idx,
                    len(chunks_geral),
                )

            # 3. Agrupa páginas por Ficha de Fiscalização
            grupos_fichas = self._agrupar_paginas_por_ficha(doc, primeira_ficha_idx)
            logger.info("MBFT Fichas detectadas | total={}", len(grupos_fichas))

            for paginas_idx in grupos_fichas:
                ficha = self._extrair_ficha(doc, paginas_idx, caminho_pdf)
                if not ficha:
                    continue
                fichas_estruturadas.append(ficha)
                chunks.append(self._ficha_para_chunk(ficha))

        if self._salvar_cache_dir:
            self._salvar_cache(fichas_estruturadas, self._salvar_cache_dir)

        logger.info(
            "MBFTParserAdapter concluído | chunks_totais={} | fichas={}",
            len(chunks),
            len(fichas_estruturadas),
        )
        return chunks

    def _encontrar_primeira_ficha(self, doc: fitz.Document) -> int:
        for i in range(len(doc)):
            txt = doc[i].get_text()
            if "FICHA DE FISCALIZAÇÃO" in txt and "Código do Enquadramento" in txt:
                return i
        return len(doc)

    def _extrair_parte_geral(
        self,
        doc: fitz.Document,
        inicio: int,
        fim: int,
        origem: str,
    ) -> list[PaginaExtraida]:
        partes: list[str] = []
        for idx in range(inicio, fim):
            txt = doc[idx].get_text().strip()
            if txt:
                partes.append(f"[[PAGINA:{idx + 1}]]\n{txt}")

        texto_completo = "\n".join(partes)
        secoes = _RE_SECAO_GERAL.split(texto_completo)
        chunks: list[PaginaExtraida] = []
        pagina_atual = 1

        for sec in secoes:
            marcadores = re.findall(r"\[\[PAGINA:(\d+)\]\]", sec)
            pagina_sec = int(marcadores[0]) if marcadores else pagina_atual
            if marcadores:
                pagina_atual = int(marcadores[-1])

            limpo = re.sub(r"\[\[PAGINA:\d+\]\]", "", sec).strip()
            if len(limpo) < 60:
                continue

            # Quebra seções muito grandes em blocos de até ~1800 chars por parágrafo
            if len(limpo) <= 1800:
                chunks.append(
                    PaginaExtraida(
                        pagina=pagina_sec,
                        texto=f"[{_MBFT_NORMA} — Parte Geral]\n{limpo}",
                        metadados={
                            "origem": origem,
                            "documento": "MBFT",
                            "norma": _MBFT_NORMA,
                            "url": _MBFT_URL,
                            "artigo": None,
                            "inciso": None,
                            "codigo_enquadramento": None,
                            "tema": "fiscalizacao_geral",
                        },
                    )
                )
            else:
                titulo = limpo.splitlines()[0].strip()
                paragrafos = [p.strip() for p in limpo.split("\n\n") if p.strip()]
                buf: list[str] = []
                for p in paragrafos:
                    if buf and sum(len(x) for x in buf) + len(p) > 1600:
                        chunks.append(
                            PaginaExtraida(
                                pagina=pagina_sec,
                                texto=f"[{_MBFT_NORMA} — Parte Geral | {titulo}]\n"
                                + "\n\n".join(buf),
                                metadados={
                                    "origem": origem,
                                    "documento": "MBFT",
                                    "norma": _MBFT_NORMA,
                                    "url": _MBFT_URL,
                                    "artigo": None,
                                    "inciso": None,
                                    "codigo_enquadramento": None,
                                    "tema": "fiscalizacao_geral",
                                },
                            )
                        )
                        buf = []
                    buf.append(p)
                if buf:
                    chunks.append(
                        PaginaExtraida(
                            pagina=pagina_sec,
                            texto=f"[{_MBFT_NORMA} — Parte Geral | {titulo}]\n"
                            + "\n\n".join(buf),
                            metadados={
                                "origem": origem,
                                "documento": "MBFT",
                                "norma": _MBFT_NORMA,
                                "url": _MBFT_URL,
                                "artigo": None,
                                "inciso": None,
                                "codigo_enquadramento": None,
                                "tema": "fiscalizacao_geral",
                            },
                        )
                    )

        return chunks

    def _agrupar_paginas_por_ficha(
        self, doc: fitz.Document, start_idx: int
    ) -> list[list[int]]:
        grupos: list[list[int]] = []
        grupo_atual: list[int] = []

        for i in range(start_idx, len(doc)):
            txt = doc[i].get_text()
            if not txt.strip():
                continue
            eh_inicio_ficha = (
                "FICHA DE FISCALIZAÇÃO" in txt and "Código do Enquadramento" in txt
            )
            if eh_inicio_ficha:
                if grupo_atual:
                    grupos.append(grupo_atual)
                grupo_atual = [i]
            elif grupo_atual:
                grupo_atual.append(i)

        if grupo_atual:
            grupos.append(grupo_atual)

        return grupos

    def _extrair_ficha(
        self,
        doc: fitz.Document,
        paginas_idx: list[int],
        origem: str,
    ) -> dict[str, Any] | None:
        campos: dict[str, str] = {
            "tipificacao_resumida": "",
            "codigo_enquadramento": "",
            "amparo_legal": "",
            "tipificacao_enquadramento": "",
            "gravidade": "",
            "penalidade": "",
            "medida_administrativa": "",
            "crime_transito": "",
            "infrator": "",
            "competencia": "",
            "pontuacao": "",
            "constatacao": "",
        }
        colunas: dict[str, list[str]] = {
            "quando_autuar": [],
            "quando_nao_autuar": [],
            "definicoes_procedimentos": [],
            "exemplos_ait": [],
            "informacoes_complementares": [],
        }

        em_tabela_4col = False
        # Guarda (x0_centro, chave_coluna) detectados no cabeçalho das 4 colunas
        col_x_centros: list[tuple[float, str]] = []

        for p_idx in paginas_idx:
            pagina = doc[p_idx]
            try:
                finder = pagina.find_tables()
                tabelas = finder.tables if finder else []
            except Exception:
                tabelas = []

            if not tabelas:
                txt_solto = _limpar_celula(pagina.get_text())
                if txt_solto:
                    colunas["informacoes_complementares"].append(txt_solto)
                continue

            for tabela in tabelas:
                for row in tabela.rows:
                    celulas_texto: list[tuple[tuple[float, float, float, float], str]] = []
                    for bbox in row.cells:
                        if bbox is None:
                            continue
                        txt = _limpar_celula(pagina.get_text("text", clip=fitz.Rect(bbox)))
                        if txt:
                            celulas_texto.append((bbox, txt))

                    if not celulas_texto:
                        continue

                    row_joined = " ".join(t for _, t in celulas_texto)
                    row_norm = re.sub(r"\s+", "", row_joined).lower()

                    if "quandoautuar" in row_norm and "quandonãoautuar" in row_norm:
                        em_tabela_4col = True
                        col_x_centros = []
                        for bbox, txt in celulas_texto:
                            tn = re.sub(r"\s+", "", txt).lower()
                            xc = (bbox[0] + bbox[2]) / 2.0
                            if "quandonãoautuar" in tn:
                                col_x_centros.append((xc, "quando_nao_autuar"))
                            elif "quandoautuar" in tn:
                                col_x_centros.append((xc, "quando_autuar"))
                            elif "definições" in tn or "procedimentos" in tn:
                                col_x_centros.append((xc, "definicoes_procedimentos"))
                            elif "exemplos" in tn or "observações" in tn:
                                col_x_centros.append((xc, "exemplos_ait"))
                        continue

                    if "informaçõescomplementares" in row_norm:
                        em_tabela_4col = False
                        texto_info = re.sub(
                            r"Informações\s+Complementares\s*:?",
                            "",
                            row_joined,
                            flags=re.IGNORECASE,
                        ).strip()
                        if texto_info:
                            colunas["informacoes_complementares"].append(texto_info)
                        continue

                    if em_tabela_4col and col_x_centros:
                        for bbox, txt in celulas_texto:
                            xc = (bbox[0] + bbox[2]) / 2.0
                            # Associa à coluna cujo centro X é mais próximo
                            _, chave_col = min(
                                col_x_centros, key=lambda item: abs(item[0] - xc)
                            )
                            colunas[chave_col].append(txt)
                        continue

                    self._preencher_campos_cabecalho(
                        [t for _, t in celulas_texto], campos
                    )

        # Fallback via texto da primeira página caso o código/amparo não tenha vindo da tabela
        if not campos["codigo_enquadramento"] or not campos["amparo_legal"]:
            txt_p0 = doc[paginas_idx[0]].get_text()
            if not campos["codigo_enquadramento"]:
                m_cod = re.search(
                    r"Código do Enquadramento:\s*\n?\s*([\d-]+)", txt_p0
                )
                if m_cod:
                    campos["codigo_enquadramento"] = m_cod.group(1).strip()
            if not campos["amparo_legal"]:
                m_amp = re.search(r"Amparo Legal:\s*\n?\s*([^\n]+)", txt_p0)
                if m_amp:
                    campos["amparo_legal"] = m_amp.group(1).strip()
            if not campos["tipificacao_resumida"]:
                m_tip = re.search(r"Tipificação Resumida:\s*\n?\s*([^\n]+)", txt_p0)
                if m_tip:
                    campos["tipificacao_resumida"] = m_tip.group(1).strip()

        if not campos["codigo_enquadramento"] and not campos["tipificacao_resumida"]:
            return None

        artigo, inciso = _extrair_artigo_inciso(campos["amparo_legal"])

        return {
            "pagina_inicio": paginas_idx[0] + 1,
            "pagina_fim": paginas_idx[-1] + 1,
            "origem": origem,
            "artigo": artigo,
            "inciso": inciso,
            **campos,
            "quando_autuar": "\n".join(colunas["quando_autuar"]).strip(),
            "quando_nao_autuar": "\n".join(colunas["quando_nao_autuar"]).strip(),
            "definicoes_procedimentos": "\n".join(
                colunas["definicoes_procedimentos"]
            ).strip(),
            "exemplos_ait": "\n".join(colunas["exemplos_ait"]).strip(),
            "informacoes_complementares": "\n".join(
                colunas["informacoes_complementares"]
            ).strip(),
        }

    def _preencher_campos_cabecalho(
        self, celulas: list[str], campos: dict[str, str]
    ) -> None:
        mapa = {
            "Tipificação Resumida:": "tipificacao_resumida",
            "Código do Enquadramento:": "codigo_enquadramento",
            "Amparo Legal:": "amparo_legal",
            "Tipificação do Enquadramento:": "tipificacao_enquadramento",
            "Gravidade:": "gravidade",
            "Penalidade:": "penalidade",
            "Medida Administrativa:": "medida_administrativa",
            "Pode Configurar Crime de": "crime_transito",
            "Infrator:": "infrator",
            "Competência:": "competencia",
            "Pontuação:": "pontuacao",
            "Constatação da Infração:": "constatacao",
        }
        for cel in celulas:
            if not cel:
                continue
            for prefixo, chave in mapa.items():
                if prefixo in cel and not campos[chave]:
                    valor = cel.split(prefixo, 1)[1]
                    valor = re.sub(r"^Trânsito\s*:?\s*", "", valor).strip()
                    valor = valor.lstrip(":").strip()
                    if valor:
                        campos[chave] = valor

    def _ficha_para_chunk(self, ficha: dict[str, Any]) -> PaginaExtraida:
        linhas = [
            f"# Ficha MBFT {ficha['codigo_enquadramento']} — {ficha['amparo_legal']}",
            f"**Norma:** {_MBFT_NORMA}",
        ]
        if ficha["tipificacao_resumida"]:
            linhas.append(f"**Tipificação Resumida:** {ficha['tipificacao_resumida']}")
        if ficha["tipificacao_enquadramento"]:
            linhas.append(
                f"**Tipificação do Enquadramento:** {ficha['tipificacao_enquadramento']}"
            )
        resumo_meta = [
            f"Gravidade: {ficha['gravidade']}" if ficha["gravidade"] else "",
            f"Pontuação: {ficha['pontuacao']}" if ficha["pontuacao"] else "",
            f"Constatação: {ficha['constatacao']}" if ficha["constatacao"] else "",
            f"Infrator: {ficha['infrator']}" if ficha["infrator"] else "",
            f"Crime de Trânsito: {ficha['crime_transito']}"
            if ficha["crime_transito"]
            else "",
        ]
        resumo_str = " | ".join(x for x in resumo_meta if x)
        if resumo_str:
            linhas.append(f"**Resumo:** {resumo_str}")
        if ficha["penalidade"]:
            linhas.append(f"**Penalidade:** {ficha['penalidade']}")
        if ficha["medida_administrativa"]:
            linhas.append(f"**Medida Administrativa:** {ficha['medida_administrativa']}")

        if ficha["quando_autuar"]:
            linhas.append(f"\n## Quando Autuar\n{ficha['quando_autuar']}")
        if ficha["quando_nao_autuar"]:
            linhas.append(f"\n## Quando NÃO Autuar\n{ficha['quando_nao_autuar']}")
        if ficha["definicoes_procedimentos"]:
            linhas.append(
                f"\n## Definições e Procedimentos\n{ficha['definicoes_procedimentos']}"
            )
        if ficha["exemplos_ait"]:
            linhas.append(
                f"\n## Exemplos do Campo de Observações do AIT\n{ficha['exemplos_ait']}"
            )
        if ficha["informacoes_complementares"]:
            linhas.append(
                f"\n## Informações Complementares\n{ficha['informacoes_complementares']}"
            )

        texto_md = "\n".join(linhas).strip()

        return PaginaExtraida(
            pagina=ficha["pagina_inicio"],
            texto=texto_md,
            metadados={
                "origem": ficha["origem"],
                "documento": "MBFT",
                "norma": _MBFT_NORMA,
                "url": _MBFT_URL,
                "artigo": ficha["artigo"],
                "inciso": ficha["inciso"],
                "codigo_enquadramento": ficha["codigo_enquadramento"],
                "gravidade": ficha["gravidade"],
                "constatacao": ficha["constatacao"],
                "tema": "fiscalizacao_mbft",
            },
        )

    def _salvar_cache(
        self, fichas: list[dict[str, Any]], diretorio: str
    ) -> None:
        out_dir = Path(diretorio)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "mbft_fichas_estruturadas.json"
        out_file.write_text(
            json.dumps(fichas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Cache estruturado do MBFT salvo em '{}'", out_file)
