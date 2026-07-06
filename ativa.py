import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Integração Ativa - Endpoint Recebedor")

# Configuração de CORS para permitir que o Streamlit Cloud aceda à API com segurança
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, pode substituir pelo link do seu Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_FILE = "logs_recebidos.json"

def salvar_log(tipo_integracao, payload, headers):
    """Guarda os dados recebidos num arquivo JSON local na VM."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []
        
    # Adiciona o novo log no início da lista
    logs.insert(0, {
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo": tipo_integracao,
        "headers": dict(headers),
        "payload": payload
    })
    
    # Mantém apenas os 50 logs mais recentes
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs[:50], f, indent=4)


# ==========================================
# ENDPOINT PARA ENTREGA DE LOGS (NOVO)
# ==========================================
@app.get("/api/logs")
async def obter_logs():
    """Endpoint que o Streamlit vai consumir para exibir o Monitor."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ==========================================
# ENDPOINTS DE RECEBIMENTO (WEBHOOKS)
# ==========================================
@app.post("/api/rest/receber")
async def receber_rest(request: Request):
    """Endpoint para receber requisições REST (JSON)."""
    try:
        payload = await request.json()
    except Exception:
        payload = (await request.body()).decode("utf-8")
        
    salvar_log("REST", payload, request.headers)
    return {"status": "sucesso", "mensagem": "Dados REST recebidos pela VM do GCP."}


@app.post("/api/soap/receber")
async def receber_soap(request: Request):
    """Endpoint para receber requisições SOAP (XML)."""
    body = await request.body()
    conteudo_xml = body.decode("utf-8")
    
    salvar_log("SOAP", conteudo_xml, request.headers)
    
    # Resposta padrão em envelope SOAP para o cliente emissor (Toledo)
    soap_response = """<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <Resposta>Recebido com sucesso pelo endpoint ativo na VM</Resposta>
      </soap:Body>
    </soap:Envelope>"""
    
    return Response(content=soap_response, media_type="text/xml")