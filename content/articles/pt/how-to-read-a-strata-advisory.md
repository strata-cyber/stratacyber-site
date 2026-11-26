+++
title = "Como ler um alerta da Strata Cyber"
summary = "TLP, severidade, probabilidade, confiança e dados pessoais: o que cada parte dos nossos alertas significa e o que ela pede de você."
date = 2026-11-26
kind = "Método"
author = "Jefferson Andrade"
tlp = "CLEAR"
+++

Todo alerta que publicamos segue o mesmo formato. Isso não é estética: é para que quem recebe saiba, em poucos segundos, **com quem pode compartilhar**, **quão grave é**, **se há dados pessoais envolvidos** e **o que fazer primeiro**. Este texto explica cada parte.

## O rótulo TLP: com quem você pode compartilhar

O Traffic Light Protocol (TLP 2.0, mantido pelo FIRST) aparece no topo de todo relatório e alerta. Ele diz até onde a informação pode circular, e não quão grave ela é.

| Rótulo | Quem pode receber |
|---|---|
| `TLP:RED` | Somente os destinatários nomeados. Não repasse. |
| `TLP:AMBER+STRICT` | Somente a sua organização. |
| `TLP:AMBER` | A sua organização e clientes dela que precisem saber para se proteger. |
| `TLP:GREEN` | A sua comunidade (setor, ISAC, parceiros), mas não em canais públicos. |
| `TLP:CLEAR` | Qualquer pessoa. Pode ser publicado. |

As cores do TLP são o padrão FIRST, sempre sobre fundo preto. Por isso elas não seguem a paleta da nossa marca.

## Severidade: quão grave é para você

A severidade resume o impacto provável **para o destinatário**, considerando exposição e controles existentes. Usamos cinco níveis: <span class="sev sev-critical">Crítico</span> <span class="sev sev-high">Alto</span> <span class="sev sev-medium">Médio</span> <span class="sev sev-low">Baixo</span> <span class="sev sev-info">Info</span>

Um mesmo evento pode ser *Alto* para um banco e *Baixo* para uma indústria. Quando o alerta é para um cliente específico, a severidade é calculada para o ambiente dele.

## Probabilidade e confiança são coisas diferentes

Em cada julgamento-chave, dizemos duas coisas:

- **Probabilidade**: a chance de algo acontecer, em faixas fixas.
- **Confiança**: o quanto confiamos na evidência e no raciocínio por trás da estimativa.

> Avaliamos com confiança moderada que é provável (55–80%) que grupos de ransomware mirem o setor nos próximos 90 dias.

Usamos sempre as mesmas palavras para as mesmas faixas. A escala vem dos padrões analíticos da comunidade de inteligência dos EUA (ICD 203):

| Termo | Faixa |
|---|---|
| Quase nenhuma chance | 1–5% |
| Muito improvável | 5–20% |
| Improvável | 20–45% |
| Chance equilibrada | 45–55% |
| Provável | 55–80% |
| Muito provável | 80–95% |
| Quase certo | 95–99% |

A confiança tem três níveis, seguindo a prática comum em inteligência:

| Confiança | O que significa |
|---|---|
| Alta | Evidência de boa qualidade, vinda de várias fontes independentes. Ainda assim, não é certeza. |
| Moderada | Crível e plausível, mas sem corroboração suficiente para confiança alta. |
| Baixa | Evidência escassa, fragmentada ou de fontes que não conseguimos verificar. |

!!! note "Por que não dizemos “com certeza”"
    Inteligência trabalha com informação incompleta. Escrever “com certeza vai acontecer” esconde o risco de erro de quem precisa decidir. Uma faixa fixa permite comparar alertas e cobrar a nossa precisão ao longo do tempo.

## Dados pessoais: quando o prazo começa

Se um alerta descreve uma atividade que pode expor dados pessoais, ele diz isso de forma explícita e aponta as perguntas de proteção de dados que você precisa responder. Os prazos de comunicação podem começar a correr assim que você sabe que dados pessoais foram afetados:

- **LGPD**: a ANPD e os titulares afetados, em até três dias úteis a partir do conhecimento de que o incidente afetou dados pessoais, quando ele puder acarretar risco ou dano relevante aos titulares (Resolução CD/ANPD nº 15/2024).
- **GDPR**: a autoridade de controle, sem demora injustificada e, quando possível, em até 72 horas a partir do conhecimento (art. 33), salvo se for improvável que a violação gere risco às pessoas. Os titulares também devem ser avisados quando o risco para eles for alto (art. 34).

A decisão de comunicar é do controlador, tomada com o encarregado e com base no risco às pessoas afetadas, não no risco à empresa. O alerta traz os fatos para essa decisão sair rápido.

## Indicadores vêm “desarmados”

Domínios, URLs e IPs maliciosos aparecem com colchetes ou `hxxp` no lugar de `http`. Isso evita cliques acidentais e que filtros de email tratem o próprio alerta como ameaça.

```
login-portal-banco[.]example
hxxps://login-portal-banco[.]example/acesso
198.51.100[.]23
```

Para usar os indicadores em bloqueios ou buscas, remova os colchetes na ferramenta de destino, nunca no navegador.

## O que fazer agora

Todo alerta termina em ações numeradas, em ordem de prioridade. A primeira é sempre a que mais reduz o risco no menor tempo. Se você só tiver cinco minutos, faça a primeira.
