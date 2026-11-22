# agentic-ai

## Instalação com pip

Use Python 3.11.5 ou superior. Na raiz do projeto, crie e ative o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

No Windows (PowerShell), a ativação é `.venv\Scripts\Activate.ps1`.
Se `python3` apontar para uma versão antiga no seu computador, use um executável
compatível, por exemplo `python3.11 -m venv .venv`.

Todas as dependências, incluindo FastMCP, Fetch e testes, ficam em
`requirements.txt`. O `pyproject.toml` contém apenas as configurações do pytest.

## Executar e testar

Com o ambiente ativado, execute:

```bash
python -m pytest -q
python -m mcp_servers.ctb_tools.client
python -m mcp_servers.client
python -m mcp_servers.client --url https://example.com
```

O primeiro cliente lista as quatro ferramentas do CTB Tools. O cliente conjunto
lista também `fetch_fetch`; com `--url`, busca e imprime o conteúdo da página.
Os clientes iniciam e encerram os servidores automaticamente por stdio.
Ambos os servidores usam o Python do ambiente ativo. Fetch é iniciado com
`python -m mcp_server_fetch` e precisa de internet para acessar páginas.

Para iniciar apenas o servidor próprio manualmente:

```bash
python -m mcp_servers.ctb_tools.server
```

Ele fica aguardando mensagens MCP; não abre uma página web. Encerre com Ctrl+C.

Para configurar o agente, copie `.env.example` para `.env` e preencha a chave do
provedor escolhido. O MCP próprio e os testes com componentes simulados não
precisam dessa chave.

O grafo usa o `FastMCPAdapter` (`agent/adapters/mcp/`), que conecta ao CTB Tools e ao
Fetch (desligável com `MCP_FETCH_ENABLED=false`) e envia nomes e JSON Schemas das
ferramentas ao roteador.
a memória padrão fica em RAM. Os testes não comprovam indexação real ou chamadas ao LLM.

## Interface (Streamlit)

Com o ambiente ativado e o `.env` preenchido (veja `.env.example`), inicie a interface:

```bash
streamlit run app.py
```

Ela abre em `http://localhost:8501`. O servidor MCP próprio e o Fetch são iniciados
automaticamente pelo agente; não é preciso subir nada à parte.

- **Chat:** cada pergunta vai ao agente com o `thread_id` da conversa, então ele lembra os turnos anteriores.
- **Nova conversa:** o botão da barra lateral cria um novo `thread_id` e limpa a tela; a memória de cada conversa é isolada.
- **Rastros:** abaixo de cada resposta aparecem as skills carregadas e as ferramentas MCP chamadas (✅/❌). No expansor "Detalhes" ficam os argumentos, os resultados ou erros e as fontes recuperadas.
- **Avisos:** mensagens bloqueadas pelo guardrail, falta de evidência e falhas (chave de API ausente, servidor indisponível, tempo esgotado) aparecem como mensagens amigáveis, sem derrubar a interface.

A interface só apresenta resultados; a lógica jurídica e os cálculos ficam no agente e nas ferramentas MCP.
O código está em `app.py` (tela) e em `streamlit_app/` (ponte assíncrona com o agente e formatação). A conversa fica em memória:
reiniciar o processo apaga o histórico.

## Skills do CTB Assist

As skills ficam em `skills/<nome>/SKILL.md`, no formato do notebook 13: cabeçalho YAML
com `name` e `description`, seguido das instruções em etapas.

| Skill | Tarefa |
|---|---|
| [analisar-infracoes](skills/analisar-infracoes/SKILL.md) | Analisar uma infração: enquadramento no CTB, regras do MBFT, exceções, cálculos via MCP e orientação fundamentada |
| [orientar-habilitacao](skills/orientar-habilitacao/SKILL.md) | Orientar sobre habilitação, PPD, renovação e toxicológico com o CTB e a Resolução CONTRAN 1.020/2025 |

São arquivos de orientação, não ferramentas MCP nem código. O nome e a descrição de cada
skill entram no catálogo do roteador; o corpo só é lido quando o roteador escolhe a skill,
e passa a valer nas decisões seguintes e na resposta final.
