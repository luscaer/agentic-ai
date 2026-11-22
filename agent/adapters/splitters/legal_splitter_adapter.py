"""
agent/adapters/splitters/legal_splitter_adapter.py

Parser e splitter legislativo dedicado para normas brasileiras em PDF
(CTB — Lei nº 9.503/1997 e Resolução CONTRAN nº 1.020/2025).

Principais garantias:
1. Remove ruídos de cabeçalho/rodapé do Planalto e do Diário Oficial da União (DOU).
2. Reconstrói artigos que atravessam quebras de página sem perder o número real da página.
3. Mantém artigos normais inteiros (caput + parágrafos + incisos + penalidade/medida administrativa).
4. Para artigos extensos (ex.: Art. 181, Art. 230), divide por blocos de incisos
   injetando o caput do artigo no início de cada sub-chunk.
5. Extrai metadados estruturados (artigo, inciso, capítulo, seção, documento, norma, tema).
"""

import asyncio
import re
from typing import Any

from loguru import logger

from agent.config.configuration import settings
from agent.domain.exceptions import ValorInvalidoError
from agent.domain.value_objects.documento_extraido import (
    DocumentoExtraido,
    PaginaExtraida,
)

# Padrões de cabeçalhos/rodapés ruidosos
_RE_PLANALTO_HEADER = re.compile(
    r"^\s*L9503Compilado\s*$|^\s*\d{2}/\d{2}/\d{4},?\s*\d{2}:\d{2}\s*$"
    r"|^\s*https?://www\.planalto\.gov\.br/\S+\s*$|^\s*\d+/\d+\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_RE_DOU_HEADER = re.compile(
    r"^\s*DIÁRIO OFICIAL DA UNIÃO\s*$"
    r"|^\s*Publicado em:.*$"
    r"|^\s*Edição:.*$"
    r"|^\s*Órgão:.*$"
    r"|^\s*Página:\s*\d+\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_RE_CAPITULO = re.compile(
    r"^\s*(CAPÍTULO\s+[IVXLCDM0-9]+(?:-[A-Z])?(?:\s*[-–—]?\s*[^\n]*)?)",
    re.MULTILINE,
)
_RE_SECAO = re.compile(
    r"^\s*(Seção\s+[IVXLCDM0-9]+(?:\s*[-–—]?\s*[^\n]*)?)",
    re.MULTILINE,
)
_RE_ARTIGO_START = re.compile(
    r"(?m)^(?=\s*(?:Art\.|Artigo)\s+(\d+(?:\.\d+)?(?:-[A-Z])?)[ºo°]?\.?\s)"
)
_RE_ARTIGO_NUM = re.compile(
    r"^\s*(?:Art\.|Artigo)\s+(\d+(?:\.\d+)?(?:-[A-Z])?)[ºo°]?\.?\s",
    re.IGNORECASE,
)
_RE_INCISO_START = re.compile(r"(?m)^(?=\s*([IVXLCDM]+)\s*[-–—]\s+)")
_RE_PAGE_MARKER = re.compile(r"\[\[PAGINA:(\d+)\]\]")


def inferir_metadados_norma(origem: str) -> dict[str, Any]:
    """Infere metadados padrão da norma a partir do nome/caminho do arquivo."""
    nome_lower = origem.lower()
    if "9503" in nome_lower or "ctb" in nome_lower:
        return {
            "documento": "CTB",
            "norma": "Lei nº 9.503/1997 (CTB)",
            "url": "https://www.planalto.gov.br/ccivil_03/leis/l9503compilado.htm",
            "tema_padrao": "legislacao_ctb",
        }
    if "1020" in nome_lower or "resolucao" in nome_lower or "contran" in nome_lower:
        return {
            "documento": "CONTRAN",
            "norma": "Resolução CONTRAN nº 1.020/2025",
            "url": "https://www.in.gov.br/en/web/dou/-/resolucao-contran-n-1.020-de-1-de-dezembro-de-2025",
            "tema_padrao": "habilitacao",
        }
    return {
        "documento": "NORMA",
        "norma": origem,
        "url": None,
        "tema_padrao": "geral",
    }


def _limpar_texto_pagina(texto: str, documento: str) -> str:
    """Remove ruídos de cabeçalho/rodapé específicos do Planalto ou DOU."""
    limpo = texto.replace("\r\n", "\n").replace("\r", "\n")
    if documento == "CTB":
        limpo = _RE_PLANALTO_HEADER.sub("", limpo)
    elif documento == "CONTRAN":
        limpo = _RE_DOU_HEADER.sub("", limpo)
    # Normaliza múltiplas quebras de linha excessivas
    limpo = re.sub(r"\n{3,}", "\n\n", limpo)
    return limpo.strip()


def _inferir_tema_artigo(texto: str, capitulo: str | None, tema_padrao: str) -> str:
    """Classifica o tema principal do artigo para facilitar filtros e rastreio."""
    base = f"{capitulo or ''} {texto[:400]}".lower()
    if any(k in base for k in ("infração -", "infracao -", "das infrações", "capítulo xv")):
        return "infracoes"
    if any(k in base for k in ("habilitação", "habilitacao", "permissão para dirigir", "ppd", "cnh", "toxicológico", "instrutor")):
        return "habilitacao"
    if any(k in base for k in ("penalidades", "suspensão do direito de dirigir", "cassação", "advertência por escrito", "pontuação")):
        return "penalidades"
    if any(k in base for k in ("processo administrativo", "notificação da autuação", "jari", "defesa", "recurso")):
        return "processo_administrativo"
    if any(k in base for k in ("crimes de trânsito", "detenção", "reclusão")):
        return "crimes_transito"
    return tema_padrao


class LegalArticleSplitterAdapter:
    """
    Implementa DocumentSplitterPort para textos legislativos estruturados em artigos.
    """

    def __init__(
        self,
        max_chunk_size: int | None = None,
    ) -> None:
        self._max_chunk_size = max_chunk_size or max(settings.SPLITTER_CHUNK_SIZE, 1600)

    async def dividir(self, documento: DocumentoExtraido) -> list[PaginaExtraida]:
        """Divide um documento legislativo em chunks por artigo (com caput preservado)."""
        return await asyncio.to_thread(self._dividir_sync, documento)

    def _dividir_sync(self, documento: DocumentoExtraido) -> list[PaginaExtraida]:
        info_norma = inferir_metadados_norma(documento.origem)
        doc_tipo = info_norma["documento"]

        # Une páginas com marcadores para não cortar artigos na virada de página
        partes_unidas: list[str] = []
        for pag in documento.paginas:
            texto_limpo = _limpar_texto_pagina(pag.texto, doc_tipo)
            if texto_limpo:
                partes_unidas.append(f"[[PAGINA:{pag.pagina}]]\n{texto_limpo}")

        texto_completo = "\n".join(partes_unidas)
        if not texto_completo.strip():
            raise ValorInvalidoError(
                "chunks",
                f"nenhum texto utilizável encontrado em '{documento.origem}'",
            )

        # Divide preservando fronteiras de Art. X
        blocos = _RE_ARTIGO_START.split(texto_completo)

        chunks: list[PaginaExtraida] = []
        pagina_atual = 1
        capitulo_atual: str | None = None
        secao_atual: str | None = None

        # Nota: _RE_ARTIGO_START tem 1 grupo de captura (número do artigo), então split
        # intercala [texto_bloco, num_artigo_proximo, texto_bloco_proximo, ...]
        # Por isso fazemos split sem grupo de captura para iterar blocos limpos.
        blocos_limpos = re.split(
            r"(?m)^(?=\s*(?:Art\.|Artigo)\s+\d+(?:\.\d+)?(?:-[A-Z])?[ºo°]?\.?\s)",
            texto_completo,
        )

        for bloco in blocos_limpos:
            # Atualiza página inicial do bloco
            marcadores = _RE_PAGE_MARKER.findall(bloco)
            pagina_bloco = int(marcadores[0]) if marcadores else pagina_atual
            if marcadores:
                pagina_atual = int(marcadores[-1])

            texto_bloco = _RE_PAGE_MARKER.sub("", bloco).strip()
            if not texto_bloco or len(texto_bloco) < 30:
                continue

            # Atualiza capítulo/seção se aparecerem no bloco
            cap_matches = _RE_CAPITULO.findall(texto_bloco)
            if cap_matches:
                capitulo_atual = re.sub(r"\s+", " ", cap_matches[-1]).strip()
            sec_matches = _RE_SECAO.findall(texto_bloco)
            if sec_matches:
                secao_atual = re.sub(r"\s+", " ", sec_matches[-1]).strip()

            m_art = _RE_ARTIGO_NUM.match(texto_bloco)
            artigo_num = m_art.group(1).replace(".", "") if m_art else None

            tema = _inferir_tema_artigo(
                texto_bloco, capitulo_atual, info_norma["tema_padrao"]
            )

            metadados_base: dict[str, Any] = {
                "origem": documento.origem,
                "documento": doc_tipo,
                "norma": info_norma["norma"],
                "url": info_norma["url"],
                "artigo": artigo_num,
                "inciso": None,
                "capitulo": capitulo_atual,
                "secao": secao_atual,
                "tema": tema,
            }

            if len(texto_bloco) <= self._max_chunk_size or not artigo_num:
                cabecalho_ctx = self._montar_cabecalho(
                    info_norma["norma"], capitulo_atual, secao_atual
                )
                texto_final = f"{cabecalho_ctx}{texto_bloco}" if cabecalho_ctx else texto_bloco
                chunks.append(
                    PaginaExtraida(
                        pagina=pagina_bloco,
                        texto=texto_final,
                        metadados=metadados_base,
                    )
                )
            else:
                sub_chunks = self._dividir_artigo_extenso(
                    texto_bloco=texto_bloco,
                    pagina=pagina_bloco,
                    metadados_base=metadados_base,
                )
                chunks.extend(sub_chunks)

        if not chunks:
            raise ValorInvalidoError(
                "chunks",
                f"nenhum chunk legislativo gerado para '{documento.origem}'",
            )

        logger.info(
            "LegalArticleSplitterAdapter | origem='{}' | documento={} | chunks={}",
            documento.origem,
            doc_tipo,
            len(chunks),
        )
        return chunks

    def _montar_cabecalho(
        self, norma: str, capitulo: str | None, secao: str | None
    ) -> str:
        partes = [norma]
        if capitulo:
            partes.append(capitulo)
        if secao:
            partes.append(secao)
        return f"[{' | '.join(partes)}]\n"

    def _dividir_artigo_extenso(
        self,
        texto_bloco: str,
        pagina: int,
        metadados_base: dict[str, Any],
    ) -> list[PaginaExtraida]:
        """
        Divide artigos longos (ex.: Art. 181, Art. 230) por blocos de incisos,
        injetando o caput do artigo no topo de cada sub-chunk.
        """
        partes = re.split(r"(?m)^(?=\s*[IVXLCDM]+\s*[-–—]\s+)", texto_bloco)
        caput = partes[0].strip()
        incisos = [p.strip() for p in partes[1:] if p.strip()]

        cabecalho = self._montar_cabecalho(
            metadados_base["norma"],
            metadados_base.get("capitulo"),
            metadados_base.get("secao"),
        )

        # Se não houver incisos romanos claros, divide por parágrafos preservando a primeira frase
        if not incisos:
            paragrafos = [p.strip() for p in texto_bloco.split("\n\n") if p.strip()]
            primeiro = paragrafos[0] if paragrafos else texto_bloco[:250]
            return self._agrupar_blocos_com_caput(
                cabecalho=cabecalho,
                caput=primeiro,
                itens=paragrafos[1:] if len(paragrafos) > 1 else [texto_bloco],
                pagina=pagina,
                metadados_base=metadados_base,
                extrair_inciso=False,
            )

        return self._agrupar_blocos_com_caput(
            cabecalho=cabecalho,
            caput=caput,
            itens=incisos,
            pagina=pagina,
            metadados_base=metadados_base,
            extrair_inciso=True,
        )

    def _agrupar_blocos_com_caput(
        self,
        cabecalho: str,
        caput: str,
        itens: list[str],
        pagina: int,
        metadados_base: dict[str, Any],
        extrair_inciso: bool,
    ) -> list[PaginaExtraida]:
        resultado: list[PaginaExtraida] = []
        buffer: list[str] = []
        incisos_no_buffer: list[str] = []
        tamanho_base = len(cabecalho) + len(caput) + 4

        def flush() -> None:
            if not buffer:
                return
            inciso_label: str | None = None
            if incisos_no_buffer:
                if len(incisos_no_buffer) == 1:
                    inciso_label = f"Inciso {incisos_no_buffer[0]}"
                else:
                    inciso_label = (
                        f"Incisos {incisos_no_buffer[0]} a {incisos_no_buffer[-1]}"
                    )
            corpo = f"{cabecalho}{caput}\n" + "\n".join(buffer)
            meta = dict(metadados_base)
            meta["inciso"] = inciso_label
            resultado.append(
                PaginaExtraida(pagina=pagina, texto=corpo.strip(), metadados=meta)
            )
            buffer.clear()
            incisos_no_buffer.clear()

        for item in itens:
            tamanho_atual = tamanho_base + sum(len(x) + 1 for x in buffer)
            if buffer and (tamanho_atual + len(item) > self._max_chunk_size):
                flush()
            buffer.append(item)
            if extrair_inciso:
                m_inc = re.match(r"^([IVXLCDM]+)\s*[-–—]", item)
                if m_inc:
                    incisos_no_buffer.append(m_inc.group(1))

        flush()
        return resultado
