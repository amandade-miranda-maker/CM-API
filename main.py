import requests


menu_moedas = """

=== Opções de Moedas para Consulta ===

Tradicionais:

USD-BRL (Dólar Americano)
EUR-BRL (Euro)
GBP-BRL (Libra Esterlina)
ARS-BRL (Peso Argentino)

Criptomoedas:

BTC-BRL (Bitcoin)
ETH-BRL (Ethereum)

=====================================

"""
def consultar_moeda(moeda):
    url  = f'https://economia.awesomeapi.com.br/json/last/{moeda}'

    resposta = requests.get(url)

    if resposta.status_code == 200:
        print("Deus certo!")
        print(resposta.json())
        return resposta.json()

    elif resposta.status_code == 404:
        erro_bonito = resposta.json
        status = erro_bonito[status]
        code = erro_bonito [code]
        mensagem = erro_bonito [mensagem]
        print('status {status}, mensagem {mensagem}, codigo {code}')
        return resposta.json


    else:
        print(resposta.json)


moeda_desejada = input('Digite a moeda que deseja consultar (ex: USD_BRL):')   

dados_api = consultar_moeda(moeda_desejada)

#----------- tratamento do json  --------------

if dados_api:
    #chave = moeda_desejada.replace("-","")
    valor = dados_api[moeda_desejada]['bid']
    print('\nRequisição bem-sucedida!')
    print(f'O valor atual de {moeda_desejada} é:')
    print(f"R$ {float(valor):.2f}")




else:
    print(f"\n Erro ao consultar moeda: {moeda_desejada} \nVerifique se o formato esta correto?")


