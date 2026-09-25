"""
buscador.py
============
AGENTE 1 - BUSCADOR (100% gratuito)

Em vez de usar uma API de IA para buscar (que teria custo de tokens),
este agente consulta diretamente o feed RSS público do Google Notícias.
É gratuito, não exige chave de API, e cobre milhares de fontes públicas
(G1, UOL, Estadão, portais regionais, etc.) em mar aberto.

Duas regras adicionais controlam o volume e a atualidade da busca:
- Janela de tempo: descarta notícias publicadas fora do intervalo
  configurado (ex: mais de 48h atrás).
- Meta de notícias: para de buscar assim que atingir o número de
  notícias únicas e recentes configurado -- não busca além do necessário.

CONCEITO ENSINADO:
- Nem todo "agente" precisa de um modelo de linguagem por trás. Buscar
  dados de uma fonte pública estruturada (RSS) é mais rápido, mais
  confiável e mais barato do que pedir pra uma IA "procurar na web".
- Parada antecipada (early stopping): um agente de busca não precisa
  esgotar todos os termos configurados -- ele deve parar assim que a
  meta é atingida, economizando tempo e requisições.
"""

import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import feedparser
from dateutil import parser as date_parser

from deduplicador import sao_a_mesma_noticia

CABECALHOS = {
    "User-Agent": "Mozilla/5.0 (compatible; AgenteNoticiasINTEGRA/1.0; +https://forumintegra.org)"
}

# Pausa entre requisições, para sermos educados com o serviço gratuito
# (evita bloqueios por excesso de requisições em sequência)
PAUSA_ENTRE_BUSCAS_SEGUNDOS = 1.5


def dentro_da_janela_de_tempo(data_publicacao: str, horas_maximas: int = 48) -> bool:
    """
    Verifica se uma notícia foi publicada dentro da janela de tempo aceita
    (ex: nas últimas 48 horas). Notícias sem data reconhecível são
    descartadas por segurança -- preferimos perder uma notícia duvidosa a
    incluir algo desatualizado sem querer.
    """
    if not data_publicacao:
        return False
    try:
        data = date_parser.parse(data_publicacao, fuzzy=True)
    except (ValueError, OverflowError):
        return False

    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)

    agora = datetime.now(timezone.utc)
    diferenca = agora - data

    # Notícias "do futuro" (relógio de fonte errado) também são descartadas
    return timedelta(0) <= diferenca <= timedelta(hours=horas_maximas)


def buscar_por_termo(termo: str, max_resultados: int = 15) -> list[dict]:
    """
    Busca notícias no Google Notícias (RSS público) para um único termo.

    Args:
        termo: palavra-chave ou frase de busca, ex: "operação policial tráfico"
        max_resultados: quantos itens do feed pegar

    Returns:
        Lista de dicts com titulo, link, fonte, data_publicacao, termo_busca
    """
    consulta = urllib.parse.quote(termo)
    url = f"https://news.google.com/rss/search?q={consulta}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

    feed = feedparser.parse(url, request_headers=CABECALHOS)

    resultados = []
    for entrada in feed.entries[:max_resultados]:
        fonte = "Fonte não identificada"
        if hasattr(entrada, "source") and hasattr(entrada.source, "title"):
            fonte = entrada.source.title

        resultados.append({
            "titulo": entrada.get("title", "").strip(),
            "link": entrada.get("link", "").strip(),
            "fonte": fonte,
            "data_publicacao": entrada.get("published", ""),
            "termo_busca": termo,
        })

    return resultados


def buscar_ate_atingir_meta(
    categorias: dict,
    meta_total: int = 10,
    janela_horas: int = 48,
    max_por_termo: int = 15,
) -> list[dict]:
    """
    Percorre as categorias/termos configurados, aplicando em cada notícia
    encontrada, na hora:
      1. Filtro de janela de tempo (descarta notícias antigas)
      2. Filtro de duplicata (compara com o que já foi coletado)

    Para assim que atingir `meta_total` notícias únicas e recentes --
    não continua buscando os termos restantes.

    Returns:
        Lista de até `meta_total` notícias únicas, cada uma já marcada
        com sua categoria.
    """
    coletadas: list[dict] = []

    for nome_categoria, termos in categorias.items():
        print(f"[Buscador] Categoria: {nome_categoria}")

        for termo in termos:
            print(f"   buscando: '{termo}'...")
            resultados = buscar_por_termo(termo, max_por_termo)

            for noticia in resultados:
                if len(coletadas) >= meta_total:
                    break

                if not dentro_da_janela_de_tempo(noticia["data_publicacao"], janela_horas):
                    continue

                noticia["categoria"] = nome_categoria

                eh_duplicada = any(
                    sao_a_mesma_noticia(noticia, existente)
                    for existente in coletadas
                )
                if not eh_duplicada:
                    coletadas.append(noticia)

            if len(coletadas) >= meta_total:
                print(f"[Buscador] Meta de {meta_total} notícia(s) atingida. Parando busca.")
                return coletadas

            time.sleep(PAUSA_ENTRE_BUSCAS_SEGUNDOS)

    if len(coletadas) < meta_total:
        print(
            f"[Buscador] Aviso: busca esgotou todos os termos configurados e encontrou "
            f"apenas {len(coletadas)} de {meta_total} notícia(s) dentro da janela de "
            f"{janela_horas}h. Considere adicionar mais termos em config.py ou aumentar a janela."
        )

    return coletadas


if __name__ == "__main__":
    # Teste manual rápido
    exemplo = buscar_por_termo("operação policial tráfico de drogas", max_resultados=5)
    for item in exemplo:
        dentro = dentro_da_janela_de_tempo(item["data_publicacao"], 48)
        print(item["titulo"], "-> dentro das 48h?", dentro, "->", item["link"])

