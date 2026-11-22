"""
agent/domain/ports/driven/document_splitter_port.py
 
Port (contrato) para divisão de texto em chunks.
"""
 
from typing import Protocol
 
from agent.domain.value_objects.documento_extraido import DocumentoExtraido, PaginaExtraida
 
 
class DocumentSplitterPort(Protocol):
    """
    Contrato para o divisor de texto em chunks.
 
    Abstrai a estratégia de divisão (tamanho fixo, por parágrafo, semântica...)
    e a biblioteca utilizada (LangChain, LlamaIndex...).
 
    Recebe um DocumentoExtraido com páginas rastreáveis e devolve chunks
    onde cada um herda os metadados da página de origem — garantindo que
    o VectorStore saiba exatamente de qual página veio cada trecho.
    """
 
    async def dividir(self, documento: DocumentoExtraido) -> list[PaginaExtraida]:
        """
        Divide um documento em chunks preservando rastreabilidade de página.
 
        Parâmetros
        ----------
        documento : DocumentoExtraido
            Documento completo com páginas extraídas pelo DocumentLoaderPort.
 
        Retorna
        -------
        list[PaginaExtraida]
            Lista de chunks prontos para indexação, cada um com o número
            da página de origem e os metadados herdados para o payload do VectorStore.
        """
        ...

