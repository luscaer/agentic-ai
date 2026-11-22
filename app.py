import uuid
from typing import Any
import streamlit as st
from streamlit_app import runtime
from streamlit_app.formatting import como_json, mensagem_de_erro, resumo_ferramenta, rotulo_fonte

EXEMPLOS = [
    "Qual artigo trata de avançar o sinal vermelho?",
    "Tenho duas multas graves e uma gravíssima. Qual é o total de pontos?",
    "Uma infração gravíssima sempre tem o mesmo valor?",
    "Posso tirar a habilitação com instrutor autônomo?",
]

BOAS_VINDAS = (
    "Olá! Sou o **CTB Assist**. Explico infrações, pontuação da CNH, multas e habilitação "
    "com base no CTB, na Resolução CONTRAN 1.020/2025 e no MBFT. As respostas são "
    "informativas e não substituem um advogado nem a decisão do órgão de trânsito."
)

st.set_page_config(page_title="CTB Assist", page_icon="🚦", layout="wide")


@st.cache_resource
def obter_servico() -> runtime.AgentService:
    """Um único serviço por processo: mantém o event loop, o orquestrador e a memória em RAM."""
    return runtime.AgentService()


def nova_thread() -> str:
    return f"ctb-{uuid.uuid4().hex[:8]}"


def iniciar_conversa() -> None:
    st.session_state.thread_id = nova_thread()
    st.session_state.mensagens = []
    st.session_state.pendente = None


def renderizar_rastro(resposta: dict[str, Any]) -> None:
    """Avisos, skills e ferramentas de uma resposta (sempre visíveis) + detalhes recolhíveis."""
    if resposta.get("bloqueado_guardrail"):
        st.warning("Esta mensagem foi bloqueada pelo guardrail de segurança.", icon="🛡️")
    elif resposta.get("faltou_informacao"):
        st.info("O agente indicou que não encontrou evidência suficiente nas fontes.", icon="ℹ️")

    skills = resposta.get("skills_carregadas") or []
    ferramentas = resposta.get("ferramentas_usadas") or []
    fontes = resposta.get("fontes") or []

    st.caption(
        "🧠 **Skills carregadas:** "
        + (", ".join(f"`{s}`" for s in skills) if skills else "nenhuma")
    )
    if ferramentas:
        st.caption("🔧 **Ferramentas chamadas:** " + " · ".join(resumo_ferramenta(f) for f in ferramentas))
    else:
        st.caption("🔧 **Ferramentas chamadas:** nenhuma")

    if not (ferramentas or fontes):
        return
    with st.expander("Detalhes: ferramentas e fontes"):
        for chamada in ferramentas:
            st.markdown(resumo_ferramenta(chamada))
            st.code(como_json(chamada.get("argumentos", {})), language="json")
            if chamada.get("sucesso"):
                st.code(como_json(chamada.get("resultado")), language="json")
            else:
                st.error(chamada.get("erro") or "A ferramenta falhou.")
        if fontes:
            st.markdown("**Fontes recuperadas**")
            for fonte in fontes:
                titulo = rotulo_fonte(fonte)
                st.markdown(f"- [{titulo}]({fonte['url']})" if fonte.get("url") else f"- {titulo}")
        st.caption(
            f"Confiança: {resposta.get('confianca', 0):.2f} · "
            f"Buscas no RAG: {resposta.get('tentativas_rag', 0)}"
        )


def renderizar_conteudo(mensagem: dict[str, Any]) -> None:
    """Conteúdo de uma mensagem, dentro de um `st.chat_message` já aberto."""
    if mensagem.get("erro"):
        st.error(mensagem["content"], icon="⚠️")
        return
    st.markdown(mensagem["content"])
    if mensagem["role"] == "assistant" and mensagem.get("meta"):
        renderizar_rastro(mensagem["meta"])


def renderizar_mensagem(mensagem: dict[str, Any]) -> None:
    with st.chat_message(mensagem["role"]):
        renderizar_conteudo(mensagem)


def perguntar(pergunta: str) -> None:
    """Envia a pergunta ao agente e registra a resposta (ou um erro amigável) na conversa."""
    usuario = {"role": "user", "content": pergunta}
    st.session_state.mensagens.append(usuario)
    renderizar_mensagem(usuario)
    with st.chat_message("assistant"):
        with st.spinner("Consultando a legislação…"):
            try:
                resposta = obter_servico().perguntar(pergunta, st.session_state.thread_id)
            except Exception as erro:  # a interface nunca deve cair por falha do agente
                mensagem = {"role": "assistant", "content": mensagem_de_erro(erro), "erro": True}
            else:
                mensagem = {"role": "assistant", "content": resposta["resposta"], "meta": resposta}
        renderizar_conteudo(mensagem)
    st.session_state.mensagens.append(mensagem)


if "thread_id" not in st.session_state:
    iniciar_conversa()

with st.sidebar:
    st.title("🚦 CTB Assist")
    st.caption("Infrações, pontuação da CNH, multas e habilitação.")
    if st.button("➕ Nova conversa", use_container_width=True):
        iniciar_conversa()
        st.rerun()
    st.caption(f"Conversa atual: `{st.session_state.thread_id}`")
    st.divider()
    st.markdown("**Experimente:**")
    for indice, exemplo in enumerate(EXEMPLOS):
        if st.button(exemplo, key=f"exemplo-{indice}", use_container_width=True):
            st.session_state.pendente = exemplo

st.header("Assistente de trânsito")
if not st.session_state.mensagens:
    st.info(BOAS_VINDAS)
for mensagem in st.session_state.mensagens:
    renderizar_mensagem(mensagem)

digitada = st.chat_input("Pergunte sobre infrações, pontos, multas ou habilitação")
pergunta = digitada or st.session_state.pop("pendente", None)
if pergunta:
    perguntar(pergunta)
