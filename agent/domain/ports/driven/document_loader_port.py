"""
agent/domain/ports/driven/document_loader_port.py
 
Port (contrato) para carregamento e extração de texto de documentos.
"""

from typing import Protocol

from agent.domain.value_objects.documento_extraido import DocumentoExtraido


class DocumentLoaderPort(Protocol):
    """
    Contrato para extração de texto puro de documentos.
 
    Abstrai a origem (PDF local, URL, S3...) e a biblioteca de extração
    (PyMuPDF, pdfplumber, BeautifulSoup...) — o domínio recebe apenas
    um DocumentoExtraido com páginas rastreáveis.
    """
 
    async def carregar(self, origem: str) -> DocumentoExtraido:
        """
        Extrai o texto de um documento preservando rastreabilidade por página.
 
        Parâmetros
        ----------
        origem : str
            Caminho local ou URL do documento a ser carregado.
 
        Retorna
        -------
        DocumentoExtraido
            Documento com todas as páginas extraídas, cada uma com texto
            e metadados de rastreabilidade prontos para o splitter.
 
        Levanta
        -------
        DocumentoNaoEncontradoError
            Se o arquivo não existir no caminho informado.
        """
        ...
