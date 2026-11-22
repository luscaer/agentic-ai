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

## Skill do CTB Assist

A skill está em [skills/orientacao-ctb/SKILL.md](skills/orientacao-ctb/SKILL.md).
Segue o formato do notebook 13: cabeçalho YAML com `name` e `description`, seguido
das instruções para escolher ferramentas, preparar entradas e apresentar respostas.

É um arquivo de orientação para o futuro agente, não uma ferramenta MCP nem código
executável. Os clientes atuais não carregam a skill automaticamente. Na integração
do agente, o nome e a descrição entram no catálogo, e o corpo é lido quando a skill
é selecionada, seguindo o exemplo `load_skill` do professor.
