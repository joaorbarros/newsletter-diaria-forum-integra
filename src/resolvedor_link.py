# -*- coding: utf-8 -*-
"""
Resolvedor de link original — Newsletter Diária Fórum INTEGRA

Converte os links "embrulhados" do Google Notícias
(news.google.com/rss/articles/...) no link real da matéria (g1.globo.com/...).

Correções desta versão:
- Compatível com googlenewsdecoder 0.2.x (campo "success") E com as versões
  antigas (campo "status"). A troca desse campo na 0.2.1 era a causa dos
  links gigantes do Google na newsletter.
- Decodifica todos os links em UM lote (menos requisições ao Google).
- Tenta de novo, com espera crescente, os links que falharem.
- Registra no log o MOTIVO de cada falha, em vez de engolir o erro.
- Notícias cujo link não foi resolvido são DESCARTADAS: um link do Google
  esconde o domínio de destino, o que não é aceitável para o nosso público.
"""

import time

from googlenewsdecoder import gnewsdecoder

TENTATIVAS_MAXIMAS = 3
ESPERA_ENTRE_TENTATIVAS_SEGUNDOS = [2, 5, 10]
INTERVALO_ENTRE_PAGINAS_SEGUNDOS = 1


def _eh_link_do_google(url: str) -> bool:
    return bool(url) and "news.google.com" in url


def _foi_sucesso(resultado: dict) -> bool:
    """Aceita o formato novo ("success") e o antigo ("status")."""
    if not isinstance(resultado, dict):
        return False
    sucesso = resultado.get("success", resultado.get("status", False))
    return bool(sucesso) and bool(resultado.get("decoded_url"))


def _decodificar_lote(urls: list[str]) -> list[dict]:
    """Chama a biblioteca em lote. Se o lote inteiro quebrar, cai para um
    por um, para que uma falha não derrube todos os links."""
    try:
        resultados = gnewsdecoder(urls, interval=INTERVALO_ENTRE_PAGINAS_SEGUNDOS)
        if isinstance(resultados, dict):  # versões antigas não aceitam lista
            raise TypeError("versão sem suporte a lote")
        return resultados
    except Exception:
        resultados = []
        for url in urls:
            try:
                resultados.append(gnewsdecoder(url, interval=INTERVALO_ENTRE_PAGINAS_SEGUNDOS))
            except Exception as erro:
                resultados.append({"success": False, "message": str(erro)})
        return resultados


def resolver_links_das_noticias(noticias: list) -> list:
    """Resolve o link de cada notícia no próprio dicionário e marca
    noticia["link_resolvido"] = True/False."""
    pendentes = []
    for noticia in noticias:
        if _eh_link_do_google(noticia.get("link", "")):
            noticia["link_resolvido"] = False
            pendentes.append(noticia)
        else:
            noticia["link_resolvido"] = bool(noticia.get("link"))

    for tentativa in range(TENTATIVAS_MAXIMAS):
        if not pendentes:
            break
        if tentativa > 0:
            espera = ESPERA_ENTRE_TENTATIVAS_SEGUNDOS[tentativa - 1]
            print(f"[Resolvedor] Nova tentativa para {len(pendentes)} link(s) em {espera}s...")
            time.sleep(espera)

        resultados = _decodificar_lote([n["link"] for n in pendentes])

        ainda_pendentes = []
        for noticia, resultado in zip(pendentes, resultados):
            if _foi_sucesso(resultado):
                noticia["link"] = resultado["decoded_url"]
                noticia["link_resolvido"] = True
            else:
                motivo = resultado.get("message", "sem detalhe") if isinstance(resultado, dict) else "resposta inválida"
                print(f"[Resolvedor] Falha ({tentativa + 1}/{TENTATIVAS_MAXIMAS}) em '{noticia['titulo'][:60]}': {motivo}")
                ainda_pendentes.append(noticia)
        pendentes = ainda_pendentes

    total_ok = sum(1 for n in noticias if n.get("link_resolvido"))
    print(f"[Resolvedor] {total_ok} de {len(noticias)} link(s) resolvido(s).")
    return noticias


def resolver_e_filtrar(noticias: list, meta_total: int) -> list:
    """Resolve os links, descarta as notícias que continuaram com link do
    Google e devolve no máximo `meta_total` notícias."""
    resolver_links_das_noticias(noticias)
    validas = [n for n in noticias if n.get("link_resolvido")]
    descartadas = len(noticias) - len(validas)
    if descartadas:
        print(f"[Resolvedor] {descartadas} notícia(s) descartada(s) por não ter link original.")
    if not validas and noticias:
        print("[Resolvedor] ATENÇÃO: nenhum link foi resolvido. Verifique o log acima "
              "(o Google pode estar bloqueando o servidor do GitHub Actions).")
    return validas[:meta_total]
