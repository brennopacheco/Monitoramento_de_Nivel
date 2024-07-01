import json
import requests
from influxdb_client import InfluxDBClient

# Configurações do InfluxDB
influxdb_url = "http://localhost:8086"
influxdb_token = "HmZZYsPoUqW_KMDt5XNC8jLcbZLnqweBtK88kEsOycnWhUmZBjett0gTN8zVkdE-had-H4BRBx05ppl88iayHQ=="
influxdb_org = "faustino"
influxdb_bucket = "bucket_01"

# Configurações da API Intercity
intercity_api = "http://cidadesinteligentes.lsdi.ufma.br"

# Função para criar uma 'capability'


def criar_capability():
    capability_json = {
        "name": "level_meter2",
        "description": "Mede o nível em unidades de medida",
        "capability_type": "sensor"
    }
    r = requests.post(intercity_api + '/catalog/capabilities/',
                      json=capability_json)
    if r.status_code == 201:
        content = json.loads(r.text)
        print("Capability criada com sucesso:", json.dumps(
            content, indent=2, sort_keys=True))
    else:
        print('Falha ao criar capability. Status code:', r.status_code)
        print('Detalhes do erro:', r.text)

# Função para criar um 'resource'


def criar_resource():
    resource_json = {
        "data": {
            "description": "level_meter_resource",
            "capabilities": ["level_meter"],
            "status": "active",
            "lat": -3.559616,
            "lon": -6.731386
        }
    }
    r = requests.post(intercity_api + '/catalog/resources', json=resource_json)
    if r.status_code == 201:
        resource = json.loads(r.text)
        uuid = resource['data']['uuid']
        print("Resource criado com sucesso:", json.dumps(resource, indent=2))
        return uuid
    else:
        print('Falha ao criar resource. Status code:', r.status_code)
        print('Detalhes do erro:', r.text)
        return None

# Função para enviar dados para a API Intercity


def enviar_dados_para_intercity(uuid, dado):
    capability_data_json = {
        "data": [
            {
                "level_meter": dado["value"],
                # Converter datetime para string no formato ISO 8601
                "timestamp": dado["time"].isoformat()
            }
        ]
    }
    r = requests.post(intercity_api + '/adaptor/resources/' + uuid +
                      '/data/environment_monitoring', json=capability_data_json)
    if r.status_code == 201:
        print('Dados enviados com sucesso!')
    else:
        print('Falha ao enviar dados. Status code:', r.status_code)
        print('Detalhes do erro:', r.text)


# Conectar ao InfluxDB
client = InfluxDBClient(
    url=influxdb_url, token=influxdb_token, org=influxdb_org)
query_api = client.query_api()

# Consultar o último valor do campo level_meter na Tabela_tanque
query = f'''
from(bucket: "{influxdb_bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "Tabela_tanque")
  |> filter(fn: (r) => r._field == "level_meter")
  |> last()
'''
result = query_api.query(org=influxdb_org, query=query)

# Processar o resultado da consulta
dado = None
if result:
    for table in result:
        for record in table.records:
            dado = {
                "time": record.get_time(),
                "measurement": record.get_measurement(),
                "field": record.get_field(),
                "value": record.get_value()
            }

if dado:
    # Criar capability e resource na API Intercity
    criar_capability()
    uuid = criar_resource()
    if uuid:
        # Enviar o dado obtido para a API Intercity
        enviar_dados_para_intercity(uuid, dado)
else:
    print("Nenhum dado encontrado para enviar.")

# Fechar a conexão com o InfluxDB
client.close()
