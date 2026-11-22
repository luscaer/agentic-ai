---
name: analisar-infracoes
description: Procedimento estruturado em múltiplas etapas para analisar infrações de trânsito, enquadramento no CTB, regras práticas de fiscalização do MBFT (Quando Autuar / Não Autuar / Abordagem), fatores multiplicadores, pontuação e risco de suspensão da CNH.
---

# Skill: Análise Estruturada de Infrações de Trânsito (CTB + MBFT)

Use esta skill sempre que o usuário relatar uma conduta no trânsito, perguntar sobre enquadramento, valor de multa, pontuação, fatores multiplicadores, autuação sem abordagem, infrações simultâneas ou impacto na pontuação da CNH.

## Etapas Obrigatórias

### Etapa 1 — Identificação da Conduta e Verificação de Dados Faltantes
1. Identifique a conduta relatada (ex.: avançar sinal vermelho, recusa ao etilômetro, excesso de velocidade, estacionamento irregular, celular ao volante).
2. Verifique se faltam dados decisivos para o enquadramento ou cálculo exato:
   - Houve **reincidência nos últimos 12 meses**? (Altera penalidades e dobra fatores multiplicadores em casos como Art. 165/165-A/165-C.)
   - O condutor está em **PPD (Permissão para Dirigir)** ou **CNH definitiva**?
   - O condutor possui **EAR (Exerce Atividade Remunerada)**?
   - Quantas **infrações gravíssimas** já constam no prontuário nos últimos 12 meses? (Define o limite escalonado de 20, 30 ou 40 pontos do Art. 261, § 1º.)
3. Caso algum dado essencial não tenha sido informado, **não invente**: apresente a regra geral e destaque explicitamente qual informação falta para uma conclusão personalizada.

### Etapa 2 — Consulta à Legislação (CTB)
1. Consulte o RAG para localizar o artigo e inciso exatos no **CTB (Lei nº 9.503/1997)**.
2. Extraia obrigatoriamente:
   - Número do artigo e inciso/parágrafo;
   - Natureza da infração (Leve, Média, Grave ou Gravíssima);
   - Penalidade prevista (multa, fator multiplicador explícito se houver, suspensão do direito de dirigir se autossuspensiva);
   - Medida administrativa (retenção, remoção do veículo, recolhimento da CNH/CRLV, etc.).

### Etapa 3 — Verificação Prática no MBFT (Resolução CONTRAN nº 985/2022)
1. Sempre que houver dúvida prática sobre fiscalização, abordagem, concomitância ou exceções, consulte também o **MBFT**:
   - Verifique **Quando AUTUAR** e **Quando NÃO Autuar** na ficha do enquadramento.
   - Verifique **Constatação da Infração** (se exige *Mediante Abordagem* ou permite *Sem Abordagem*).
   - Verifique vedações de autuação simultânea (ex.: vedação de lavratura simultânea dos arts. 165 e 165-A na mesma abordagem).

### Etapa 4 — Checagem de Exceções e Fatores Multiplicadores
1. Nunca assuma que toda infração gravíssima tem o mesmo valor base (Art. 258, § 2º).
2. Confirme no texto do artigo se há fator multiplicador (`2x`, `3x`, `5x`, `10x`, `20x`, `60x`) ou se a infração é **autossuspensiva** (suspende o direito de dirigir independentemente da soma de pontos).
3. Verifique se cabe **advertência por escrito** (Art. 267 CTB: infração leve ou média sem outra infração nos últimos 12 meses).

### Etapa 5 — Cálculos Determinísticos via Ferramentas MCP
1. **Nunca faça contas de pontuação, soma de multas ou análise de limite de pontos de cabeça.** Use as ferramentas do servidor CTB Tools, pelo nome exato:
   - `ctb_tools_calcular_pontos`: soma os pontos por natureza (lista `infracoes`, cada uma com `natureza` e `quantidade`);
   - `ctb_tools_calcular_valor_multas`: soma os valores das multas (natureza, quantidade e multiplicador; multiplicador maior que 1 exige `fundamento_multiplicador`, citando o artigo confirmado na Etapa 4);
   - `ctb_tools_analisar_pontuacao`: simula a janela de 12 meses (cada infração com `data` AAAA-MM-DD, mais `data_referencia` e `ear`, que vêm do usuário conforme a Etapa 1; nunca presuma EAR).
2. Use na chamada a natureza e o multiplicador extraídos do CTB nas Etapas 2 e 4. Se faltar algum dado obrigatório, não chame a ferramenta: peça o dado ao usuário.
3. Se a ferramenta devolver erro, corrija apenas o que os dados do usuário permitirem; nunca apresente um total inventado.
4. Use na resposta o valor retornado pela ferramenta e preserve as ressalvas que ela informar (não é saldo oficial da CNH nem decisão de suspensão).

### Etapa 6 — Formatação da Orientação Fundamentada
Estruture a resposta final de forma clara, objetiva e consultiva:
1. **Enquadramento Legal:** Artigo, inciso/parágrafo do CTB e, quando aplicável, Ficha/Código de Enquadramento do MBFT.
2. **Natureza, Pontuação e Penalidade:** Pontos, valor (com multiplicador, se houver) e medida administrativa.
3. **Regras Práticas / Exceções (MBFT e CTB):** Abordagem, casos em que não cabe autuação, reincidência ou advertência por escrito.
4. **Impacto na CNH/PPD:** Diferencie sempre simulação de pontuação de suspensão automática (que depende de processo administrativo com ampla defesa).
5. **Limitações / Dados Pendentes:** Liste eventuais dados não informados pelo usuário e reforce o caráter informativo (não substitui defesa jurídica formal).
