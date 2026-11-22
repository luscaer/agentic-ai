import json
from typing import Any


def mensagem_de_erro(erro: BaseException) -> str:
    """Traduz falhas técnicas em uma mensagem amigável, sem esconder a causa."""
    texto = f"{type(erro).__name__}: {erro}".strip()
    baixo = texto.lower()
    if isinstance(erro, TimeoutError) or "timeout" in baixo:
        dica = "O agente demorou demais para responder. Tente novamente."
    elif any(t in baixo for t in ("api key", "api_key", "apikey", "credential", "authentication")):
        dica = "Não encontrei a chave de API do modelo. Preencha o arquivo .env (veja .env.example)."
    elif any(t in baixo for t in ("connection", "network", "resolve", "unreachable")):
        dica = "Falha de conexão com um serviço externo. Verifique a internet e tente de novo."
    else:
        dica = "Não foi possível concluir a resposta."
    return f"{dica}\n\nDetalhe técnico: `{texto[:300]}`"


def resumo_ferramenta(chamada: dict[str, Any]) -> str:
    """Uma linha por ferramenta chamada: ✅/❌, nome e servidor."""
    marca = "✅" if chamada.get("sucesso") else "❌"
    servidor = chamada.get("servidor")
    return f"{marca} `{chamada.get('ferramenta', '?')}`" + (f" ({servidor})" if servidor else "")


def como_json(valor: Any, limite: int = 1500) -> str:
    """JSON legível e truncado, para exibir argumentos e resultados."""
    try:
        texto = json.dumps(valor, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        texto = str(valor)
    return texto if len(texto) <= limite else texto[:limite] + "\n… (truncado)"


def rotulo_fonte(fonte: dict[str, Any]) -> str:
    """Citação curta da fonte, preferindo a referência já montada pelo backend."""
    return fonte.get("referencia") or fonte.get("fonte") or fonte.get("documento") or "Fonte"
