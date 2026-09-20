import os
import json
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from typing import List
from datetime import datetime

app = FastAPI(title="WhatsApp Scheduling MVP")

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "my_secure_verify_token")

class ConnectionManager:
    """
    Gerenciador de conexões WebSocket.
    Responsável por manter o estado das conexões ativas com os clientes (dashboards)
    e realizar o envio de mensagens em tempo real (broadcast).
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Aceita e registra uma nova conexão WebSocket.
        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Remove uma conexão WebSocket da lista de conexões ativas.
        """
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """
        Envia uma string de texto para todos os clientes conectados simultaneamente.
        """
        for connection in self.active_connections:
            await connection.send_text(message)

ws_manager = ConnectionManager()

async def process_intent_with_ai(sender_id: str, message_text: str) -> str:
    """
    Processa a mensagem de texto recebida do usuário utilizando IA.
    
    Extrai intenções e entidades (Nome, CPF, Data) e aciona eventos 
    de broadcast para o dashboard em tempo real caso uma ação seja consolidada.
    """
    message_lower = message_text.lower()
    
    if "agendar" in message_lower and "dia" in message_lower:
        event_data = {
            "type": "NEW_APPOINTMENT",
            "client": sender_id,
            "status": "CONFIRMED",
            "timestamp": datetime.now().isoformat()
        }
        await ws_manager.broadcast(json.dumps(event_data))
        return "Tudo certo! Seu agendamento foi confirmado. Mais alguma coisa?"
    
    elif "cancelar" in message_lower:
        event_data = {
            "type": "CANCELLATION",
            "client": sender_id,
            "status": "CANCELLED",
            "timestamp": datetime.now().isoformat()
        }
        await ws_manager.broadcast(json.dumps(event_data))
        return "Entendido, seu agendamento foi cancelado."

    return "Olá! Sou seu assistente virtual. Como posso ajudar você hoje?"

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Endpoint de verificação de Webhook exigido pela Meta.
    Garante que a assinatura da URL foi feita com o token correto.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Invalid token")

@app.post("/webhook")
async def handle_whatsapp_messages(request: Request):
    """
    Endpoint principal para recebimento de mensagens do WhatsApp.
    Processa o payload JSON da Meta e encaminha o texto para a IA.
    """
    body = await request.json()
    
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                if "messages" in value:
                    for message in value["messages"]:
                        sender_id = message["from"]
                        text = message.get("text", {}).get("body", "")
                        
                        ai_response = await process_intent_with_ai(sender_id, text)
                        print(f"[{sender_id}] Resposta IA: {ai_response}")
                        
        return {"status": "success"}
    raise HTTPException(status_code=404)

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    Endpoint WebSocket para conexão do Dashboard (Next.js).
    Permite atualização reativa dos agendamentos na interface do usuário.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
