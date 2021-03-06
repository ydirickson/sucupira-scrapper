import csv
import http
import json
import logging as log
import requests
from bs4 import BeautifulSoup


log.basicConfig(level=log.INFO,  format='%(name)s - %(levelname)s - %(message)s')

PAGINA_URL = 'https://catalogodeteses.capes.gov.br/catalogo-teses/rest/busca'
TERMO = '"sala de recursos" OR "salas de recursos"'


def request_pagina(pagina):
    data = {
        'termo': TERMO,
        'pagina': pagina,
        'registrosPorPagina': 50
    }
    with requests.post(PAGINA_URL, json=data) as resposta:
        try:
            return json.loads(resposta.text)
        except:
            log.error(f'Erro ao obter a página {pagina}')


def processar_pagina(numero, teses):
    log.info(f'Processando página {numero} com {len(teses)} elementos')
    lista = []
    for tese in teses:
        ano = int(tese['dataDefesa'].split('-')[0])
        link = tese['link']
        if link and ano >= 2014:
            dados = obter_dados_tese(link, tese['id'], ano)
            if dados:
                lista.append(dados)
        else:
            log.debug(f'Pulando tese {tese["id"]} por falta de link ou por data anterior a 2014')
    return lista


def obter_dados_tese(link, id, ano):
    with requests.get(link) as resposta:
        soup = BeautifulSoup(resposta.content,'html.parser')
        try:
            return {
                'ID': id,
                'ANO': ano,
                'LINK': link,
                'IES': get_dado(soup, 'ies'),
                'PROGRAMA': get_dado(soup, 'programa'),
                'TITULO': get_dado(soup, 'nome'),
                'AUTOR': get_dado(soup, 'autor'),
                'TIPO': get_dado(soup, 'tipo'),
                'DATA': get_dado(soup, 'data'),
                'RESUMO': get_dado(soup, 'resumo'),
                'PALAVRAS-CHAVE': get_dado(soup, 'palavras'),
                'PAGINAS': get_dado(soup, 'paginas'),
                'ORIENTADOR': get_dado(soup, 'orientador')
            }
        except http.client.IncompleteRead:
            log.error(f'Problemas ao parsear os dados do trabalho {id}, tentando novamente')
            return obter_dados_tese(link, id, ano)
        else:
            log.error(f'Dados não encontrados no link {link}')


def get_dado(soup, key):
    campo = soup.find(id=key)
    return campo.text if campo else 'NÃO ENCONTRADO'

def escrever_csv(lista):
    with open('resultados.csv', mode='w') as csv_file:
        writer = csv.DictWriter(csv_file, delimiter=';', quoting=csv.QUOTE_ALL, fieldnames=lista[0].keys(), quotechar='"')
        writer.writeheader()
        for item in lista:
            if item:
                writer.writerow(item)
            else:
                print(item)

if __name__ == '__main__':
    log.info('Começando a extração de dados do Sucupira')
    log.info(f'Buscando a primeira página com informações báscias pelo termo ({TERMO})')
    pagina = request_pagina(1)
    total = pagina['total']
    numPagina = pagina['registrosPorPagina']
    paginas = (total // numPagina) + 1
    log.info(f'Serão processados um total de {total} registros, separados em {paginas} de {numPagina} elementos por página')
    
    lista = processar_pagina(1, pagina['tesesDissertacoes'])
    for n in range(2, paginas+1):
        pagina = request_pagina(n)
        lista += processar_pagina(n, pagina['tesesDissertacoes'])

    escrever_csv(lista)

