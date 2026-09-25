# Newsletter Diária de Notícias Policiais para WhatsApp (100% gratuito)

Pipeline de agentes em Python puro que busca notícias sobre operações policiais, crimes, fraudes e segurança pública em fontes públicas na web, filtra duplicatas, respeita uma janela de tempo configurável, encurta links e gera uma **newsletter diária** pronta para envio via WhatsApp — **sem usar nenhuma API de IA paga ou cobrada por token**.

## Contexto

Este projeto nasceu de uma necessidade real de comunicação institucional: monitorar e consolidar notícias sobre segurança pública para distribuição diária via WhatsApp — a "Newsletter Diária - Fórum Integra" —, um processo que antes era feito manualmente. A primeira versão usava a API da Anthropic (Claude) para buscar e estruturar as notícias; esta versão foi reconstruída do zero para eliminar qualquer custo por token, usando técnicas determinísticas onde IA generativa não era, na prática, necessária.

## O que este projeto demonstra

- **Arquitetura de pipeline com múltiplos agentes** especializados (buscador, deduplicador, encurtador, organizador, formatador), cada um com responsabilidade única e testável isoladamente.
- **Critério técnico sobre quando usar IA e quando não usar.** Nem todo "agente" precisa de um LLM por trás — comparação de texto, filtro de datas e formatação de string são resolvidos com Python puro, de forma mais rápida, previsível e barata.
- **Engenharia com restrições reais de custo e produção:** parada antecipada (early stopping) para não desperdiçar requisições, fallback gracioso quando um serviço externo (encurtador) falha, e limites de janela de tempo para manter a relevância do conteúdo.
- **Documentação honesta de limitações técnicas** (veja a seção sobre o filtro de duplicatas abaixo) — a abordagem determinística tem trade-offs conhecidos frente a uma abordagem com IA, e isso está documentado, não escondido.

## Por que não usa IA generativa

Todo o pipeline anterior (baseado em Claude/Gemini) foi substituído por técnicas determinísticas e gratuitas:

| Etapa | Como era (com IA) | Como é agora (gratuito) |
|---|---|---|
| Buscar notícias | Tool `web_search` da Anthropic (pago por token) | RSS público do Google Notícias (gratuito, sem chave) |
| Detectar duplicatas | Modelo julgando semanticamente | `difflib` (similaridade de texto) + sobreposição de palavras-chave + data + localidade |
| Organizar por tópico | Modelo classificando | Mapeamento direto configurado em `config.py` |
| Gerar mensagem final | Modelo escrevendo HTML/texto | Formatação de string determinística |

Nenhuma chamada de API é feita em nenhuma etapa. O custo de rodar este projeto é **zero**, independentemente de quantas vezes ou quantas notícias você processar.

## Arquitetura

```
config.py (categorias, termos, janela de tempo, meta)
        │
        ▼
┌─────────────────────┐  RSS público do Google Notícias. Aplica NA HORA:
│  1. Buscador         │  - filtro de janela de tempo (só notícias das
│  buscador.py         │    últimas N horas, ex: 48h)
│  buscar_ate_          │  - filtro de duplicata (compara com o que já
│  atingir_meta()       │    foi coletado)
└──────────┬───────────┘  PARA assim que atingir a meta (ex: 10 notícias)
           ▼
┌─────────────────────┐  Decodifica o link "embrulhado" do Google
│  2. Resolvedor de     │  Notícias, entregando a URL real da matéria
│     Link              │  (ex: g1.globo.com/...).
│  resolver_link.py     │
└──────────┬───────────┘
           ▼
┌─────────────────────┐  (Opcional, desativado por padrão) Encurta os
│  3. Encurtador        │  links via TinyURL. Se falhar, mantém o link
│  encurtador.py        │  original (fallback).
└──────────┬───────────┘
           ▼
┌─────────────────────┐  Agrupa as notícias selecionadas nas categorias
│  4. Organizador       │  definidas em config.py.
│  organizador.py       │
└──────────┬───────────┘
           ▼
┌─────────────────────┐  Monta a mensagem final no formato exato do seu
│  5. Formatador        │  modelo, usando o link curto.
│  formatador_whatsapp  │
└──────────┬───────────┘
           ▼
   mensagem_whatsapp_*.txt (pronta para copiar/colar no WhatsApp)
```

## Regras de busca (ajustáveis em `config.py`)

- **Janela de tempo:** só considera notícias publicadas dentro de `JANELA_HORAS_MAXIMA` (padrão: 48h). Notícias sem data reconhecível são descartadas por segurança.
- **Meta de notícias:** a busca **para automaticamente** assim que atingir `META_TOTAL_NOTICIAS` (padrão: 10) — não continua buscando os termos restantes.
- **Encurtamento de link:** feito só nas notícias finais selecionadas (não nas descartadas), usando a API gratuita do TinyURL. Se o serviço estiver fora do ar, o link original é usado sem quebrar o pipeline.

## Agendamento automático (GitHub Actions)

O arquivo `.github/workflows/newsletter.yml` roda a newsletter automaticamente **de segunda a sexta-feira, às 09:30 (horário de Brasília)**, e envia o resultado por e-mail para `contato@forumintegra.org` — sem depender do Google Colab, sem assinatura paga, direto na nuvem do GitHub.

Para funcionar, é necessário configurar 4 *secrets* no repositório (credenciais de e-mail) — veja o passo a passo completo na seção de configuração do repositório, mais abaixo.

## Como configurar o envio automático por e-mail

1. No repositório do GitHub, vá em **Settings → Secrets and variables → Actions → New repository secret**
2. Crie os seguintes secrets, um de cada vez:

| Nome do secret | O que colocar |
|---|---|
| `MAIL_SERVER` | Endereço SMTP do seu provedor de e-mail (ex: `smtp.gmail.com`) |
| `MAIL_PORT` | Porta SMTP (geralmente `465`) |
| `MAIL_USERNAME` | O e-mail usado para autenticar o envio |
| `MAIL_PASSWORD` | Senha de app (não a senha normal da conta, veja nota abaixo) |

3. Pronto — o workflow já está configurado para rodar automaticamente. Você também pode testá-lo manualmente a qualquer momento em **Actions → Newsletter Diária - Fórum Integra → Run workflow**, sem precisar esperar o horário agendado.

**Nota sobre senha:** a maioria dos provedores de e-mail (Gmail, Google Workspace, Outlook) não aceita mais a senha normal da conta para envio via SMTP por scripts — é necessário gerar uma **senha de app** específica nas configurações de segurança da conta. Se `contato@forumintegra.org` for uma conta do Google Workspace, o processo é o mesmo do Gmail pessoal (Conta Google → Segurança → Senhas de app), desde que a verificação em duas etapas esteja ativada.

**Limitação do GitHub Actions:** o agendamento (`cron`) é gratuito, mas o GitHub não garante o horário exato ao segundo — pode haver alguns minutos de atraso em horários de pico. Além disso, se o repositório ficar 60 dias sem nenhuma atividade (commits, etc.), o GitHub desativa automaticamente os agendamentos por segurança — nesse caso, basta reativar em **Actions**.

## Como usar

```bash
pip install -r requirements.txt
cd src
python main.py
```

O resultado aparece no terminal e também é salvo em `saidas/mensagem_whatsapp_<timestamp>.txt` — é só copiar o conteúdo e colar na conversa do WhatsApp.

## Link real da matéria (sem redirecionamento do Google Notícias)

O RSS do Google Notícias entrega links "embrulhados" (`news.google.com/rss/articles/...`), que escondem o domínio de destino até o clique — o mesmo problema de segurança que motivou desativar o encurtador (veja seção abaixo). Um agente adicional (`src/resolver_link.py`) decodifica automaticamente esses links, entregando a URL real da matéria (ex: `g1.globo.com/...`), usando a biblioteca open-source `googlenewsdecoder` (gratuita, sem chave de API).

Se a decodificação falhar por qualquer motivo (fora do ar, rate limit), o link original do Google é mantido como fallback — o pipeline nunca quebra por causa disso.

## Segurança: links originais por padrão (proteção contra phishing)

O encurtador de links vem **desativado por padrão**. A mensagem final mostra o **link de origem completo** (ex: `g1.globo.com/...`), não um link encurtado.

Motivo: links encurtados escondem o domínio de destino até o clique — uma técnica comum em golpes de phishing. Para um público que inclui agentes de segurança pública e equipes de inteligência (que, por rotina profissional, verificam o domínio antes de clicar em qualquer link), isso é uma preocupação legítima mesmo usando um encurtador confiável como o TinyURL.

Para reativar o encurtamento (se preferir mensagens mais compactas e o público não tiver essa restrição), edite em `src/config.py`:

```python
ATIVAR_ENCURTADOR_DE_LINK = True
```

## Como ajustar a busca (o que você vai mexer com frequência)

Edite **`src/config.py`**. Cada categoria é uma lista de termos de busca:

```python
NOME_ORGANIZACAO = "Newsletter Diária - Fórum Integra"

CATEGORIAS_DE_BUSCA = {
    "OPERAÇÕES POLICIAIS": [
        "operação policial prisão",
        "operação policial tráfico de drogas",
        "operação policial facção criminosa",
    ],
    "CRIMES E INVESTIGAÇÕES": [
        "polícia civil investigação homicídio",
        "polícia prende suspeito",
        "polícia investiga fraude",
    ],
    "APREENSÕES": [
        "polícia apreensão armas",
        "polícia apreensão drogas",
    ],
    "SEGURANÇA PÚBLICA - GERAL": [
        "segurança pública Brasil",
        "polícia militar ação",
        "polícia civil ação",
    ],
    # adicione novas categorias ou termos aqui
}
```

Cada termo vira uma busca separada no Google Notícias. Quanto mais termos, mais cobertura — mas também mais tempo de execução (o buscador espera um intervalo entre requisições para não sobrecarregar o serviço gratuito).

## Formato da mensagem final

O cabeçalho é gerado com a data em **português**, no formato:

```
🖥 - *Newsletter Diária - Fórum Integra*
*Brasília,* *28* *de* *julho* *de* *2026*

 *===* *OPERAÇÕES POLICIAIS* *===*
=====================================
*Título da notícia em negrito*
https://link-encurtado
--------------------------------------
```

Quando você tiver ajustes adicionais no modelo oficial, é só mexer em `src/formatador_whatsapp.py` — a lógica de divisão em partes e organização por categoria continua igual.

## Como o filtro de duplicatas identifica o mesmo fato

Sem usar um modelo de linguagem, a detecção de "é a mesma notícia?" cruza:
1. Datas próximas (tolerância de até 2 dias)
2. Localidade em comum — reconhece tanto **estados** quanto **principais cidades brasileiras** (ex: "Niterói" é reconhecida como RJ, "Curitiba" como PR)
3. Parecença de texto caractere a caractere, OU sobreposição de palavras-chave significativas
4. Uma regra combinada: se a localidade é confirmada igual em ambas E há pelo menos 2 palavras-chave em comum, já é considerado o mesmo fato — mesmo que a redação seja bem diferente

Para o passo 3 e 4, o filtro remove automaticamente **palavras genéricas do domínio policial** ("polícia", "operação", "prende", "suspeito" etc.) antes de comparar — essas palavras aparecem em quase toda manchete e só atrapalhavam a comparação. Também normaliza sinônimos comuns (ex: "tráfico", "drogas" e "entorpecentes" contam como o mesmo termo; "presídios" e "prisões" também).

Isso resolveu, por exemplo, um caso real em que 5 notícias sobre a mesma operação no Rio de Janeiro (envolvendo drogas e celulares em presídios), escritas de formas bem diferentes por 5 veículos diferentes, apareciam como notícias separadas — agora são corretamente unificadas em uma só.

**Ainda assim, é uma abordagem determinística (gratuita), não semântica de verdade.** Pode, em casos raros, deixar passar duas notícias sobre o mesmo fato se as fontes usarem vocabulário muito diferente e sem palavras-chave específicas em comum. Se isso continuar acontecendo com frequência, o próximo passo — ainda gratuito — é usar embeddings locais (biblioteca `sentence-transformers`, roda no seu computador, sem API, sem custo por token) para comparar o *significado* dos títulos em vez de só o texto.

## Limitações técnicas do RSS gratuito

- O Google Notícias pode limitar requisições muito frequentes — por isso há uma pausa de 1,5s entre buscas.
- Nem toda fonte pública tem RSS indexado pelo Google Notícias; a cobertura é ampla, mas não é 100% de tudo que existe na web.
- Este projeto não roda no ambiente do Claude (sandbox sem acesso à internet geral) — rode na sua própria máquina, onde há acesso normal à web.


## Próximos passos possíveis

- [ ] Automatizar o envio da mensagem (ex: `pywhatkit`, biblioteca gratuita que abre o WhatsApp Web e envia automaticamente)
- [ ] Agendar execução diária (ex: `cron` no Linux, Agendador de Tarefas no Windows, ou um workflow no N8N)
- [ ] Trocar o filtro de duplicatas por embeddings locais gratuitos (`sentence-transformers`) se a precisão atual não for suficiente
- [ ] Guardar notícias já enviadas (ex: em um `.json` local) para nunca repetir a mesma notícia em execuções futuras

## Stack

`Python` · `feedparser` (RSS) · `python-dateutil` · `difflib` (biblioteca padrão) — **zero APIs pagas, zero custo por token**

## Licença

Este projeto está sob a licença MIT — veja o arquivo [`LICENSE`](LICENSE) para o texto completo. Em resumo: qualquer pessoa pode usar, copiar, modificar e redistribuir este código, inclusive para fins comerciais, desde que o aviso de copyright original seja mantido.

## Como citar este projeto

Se este projeto for referenciado em outro trabalho (acadêmico, técnico ou institucional), a citação sugerida no padrão ABNT é:

```
BARROS, João. Newsletter Diária de Notícias Policiais para WhatsApp. GitHub, 2026.
Disponível em: https://github.com/jarb1611/newsletter-diaria-forum-integra.
Acesso em: [data de acesso].
```

Este repositório também inclui um arquivo [`CITATION.cff`](CITATION.cff), reconhecido nativamente pelo GitHub — isso habilita o botão **"Cite this repository"** na página principal, que gera a citação automaticamente em formatos como APA e BibTeX.
