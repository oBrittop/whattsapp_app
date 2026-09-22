import os
import json
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from typing import List
from datetime import datetime
from contextlib import asynccontextmanager

from app.ai.agent import analyze_message_with_llm
from app.core.security import encrypt_data
from app.db.database import SessionLocal, Base, engine
from app.db.models import Client, Appointment

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executa no momento em que o servidor FastAPI liga.
    Cria as tabelas físicas no PostgreSQL caso não existam, garantindo
    que a persistência esteja pronta para receber dados.
    """
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="WhatsApp Scheduling MVP", lifespan=lifespan)

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
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

ws_manager = ConnectionManager()

async def process_intent_with_ai(sender_id: str, message_text: str) -> str:
    """
    Recebe o texto livre do usuário, aciona a IA para extração de entidades estruturadas
    e aplica a lógica de negócios correspondente à intenção (AGENDAR ou CANCELAR).
    Realiza a persistência criptografada no banco e emite alertas via WebSocket.
    """
    extraction = analyze_message_with_llm(message_text)
    
    db = SessionLocal()
    try:
        if extraction.intent == "AGENDAR" and extraction.cpf and extraction.date:
            cpf_enc = encrypt_data(extraction.cpf)
            
            client = db.query(Client).filter(Client.whatsapp_id == sender_id).first()
            if not client:
                client = Client(
                    whatsapp_id=sender_id, 
                    name=extraction.name or "Cliente", 
                    cpf_encrypted=cpf_enc
                )
                db.add(client)
                db.commit()
                db.refresh(client)
                
            new_appt = Appointment(
                client_id=client.id, 
                appointment_date=datetime.now(), 
                status="CONFIRMED"
            )
            db.add(new_appt)
            db.commit()
            
            event_data = {
                "type": "NEW_APPOINTMENT",
                "client": client.name,
                "status": "CONFIRMED",
                "timestamp": datetime.now().isoformat()
            }
            await ws_manager.broadcast(json.dumps(event_data))
            
        elif extraction.intent == "CANCELAR":
            event_data = {
                "type": "CANCELLATION",
                "client": sender_id,
                "status": "CANCELLED",
                "timestamp": datetime.now().isoformat()
            }
            await ws_manager.broadcast(json.dumps(event_data))

    finally:
        db.close()

    return extraction.reply_message

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Endpoint de verificação de Webhook exigido pela Meta.
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
    Processa o payload JSON da Meta, localiza o texto enviado e encaminha 
    para o pipeline da Inteligência Artificial.
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
                        print(f"[{sender_id}] Resposta Enviada: {ai_response}")
                        
        return {"status": "success"}
    raise HTTPException(status_code=404)

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    Endpoint WebSocket para conexão do Dashboard em React/Next.js.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
