"""
agent/domain/value_objects/documento_extraido.py

Value Objects que representam o resultado da extração de um documento,
prontos para serem fatiados pelo DocumentSplitterPort e indexados no VectorStore.

Esses VOs existem exclusivamente na camada de ingestão nascem no
DocumentLoaderPort e são consumidos pelo DocumentSplitterPort. Nunca
chegam à camada de resposta ao usuário (essa responsabilidade é do FonteDocumento).
"""

from dataclasses import dataclass, field
from typing import Any

from agent.domain.exceptions import ValorInvalidoError


@dataclass(frozen=True)
class PaginaExtraida:
    """
    Value Object imutável que representa uma página extraída de um documento.

    Armazena o texto bruto da página e seus metadados de rastreabilidade.
    O dicionário `metadados` é flexível por design — diferentes loaders
    podem enriquecer com campos distintos (autor, data, seção, etc.),
    e o VectorStore espera exatamente um dicionário no payload.

    Exemplos
    --------
    >>> pagina = PaginaExtraida(
    ...     pagina=3,
    ...     texto="Art. 5º O empenho da despesa...",
    ...     metadados={"manual_id": 42, "origem": "siafi_2024.pdf"},
    ... )
    >>> pagina.pagina
    3
    >>> pagina.metadados["manual_id"]
    42
    """

    pagina: int
    texto: str
    metadados: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.pagina < 1:
            raise ValorInvalidoError(
                "pagina",
                f"deve ser um número maior ou igual a 1 (recebido: {self.pagina})",
            )

        if not self.texto.strip():
            raise ValorInvalidoError(
                "texto",
                f"não pode ser vazio na página {self.pagina}",
            )

    def __str__(self) -> str:
        return f"Página {self.pagina} | {len(self.texto)} chars | metadados={list(self.metadados.keys())}"


@dataclass(frozen=True)
class DocumentoExtraido:
    """
    Value Object imutável que representa um documento completo após extração.

    Agrupa todas as páginas extraídas de uma origem, preservando a
    rastreabilidade individual de cada página para o pipeline de ingestão.

    O DocumentLoaderPort produz um DocumentoExtraido.
    O DocumentSplitterPort consome um DocumentoExtraido e produz list[PaginaExtraida],
    onde cada chunk herda os metadados da página de origem.

    Exemplos
    --------
    >>> doc = DocumentoExtraido(
    ...     origem="manuais/siafi_2024.pdf",
    ...     paginas=(
    ...         PaginaExtraida(pagina=1, texto="Introdução...", metadados={"manual_id": 42}),
    ...         PaginaExtraida(pagina=2, texto="Art. 5º...", metadados={"manual_id": 42}),
    ...     ),
    ... )
    >>> doc.total_paginas
    2
    >>> doc.total_caracteres
    24
    """

    origem: str
    paginas: tuple[PaginaExtraida, ...]

    def __post_init__(self) -> None:
        if not self.origem.strip():
            raise ValorInvalidoError("origem", "não pode ser vazia")

        if not self.paginas:
            raise ValorInvalidoError(
                "paginas",
                f"documento '{self.origem}' não contém páginas extraídas",
            )

    @property
    def total_paginas(self) -> int:
        """Número de páginas extraídas do documento."""
        return len(self.paginas)

    @property
    def total_caracteres(self) -> int:
        """Total de caracteres extraídos em todas as páginas."""
        return sum(len(p.texto) for p in self.paginas)

    def __str__(self) -> str:
        return (
            f"DocumentoExtraido(origem='{self.origem}' | "
            f"páginas={self.total_paginas} | "
            f"caracteres={self.total_caracteres})"
        )
