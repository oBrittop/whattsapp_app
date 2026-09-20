import os
import json
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from typing import List
from datetime import datetime

from contextlib import asynccontextmanager

# Importações das novas camadas (Banco de Dados e IA)
from app.ai.agent import analyze_message_with_llm
from app.core.security import encrypt_data
from app.db.database import SessionLocal, Base, engine
from app.db.models import Client, Appointment

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executa no momento em que o servidor FastAPI liga.
    Aqui estamos forçando o SQLAlchemy a criar as tabelas no PostgreSQL 
    caso elas ainda não existam. (Ideal para MVPs rápidos).
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
    Recebe a mensagem, envia para a Inteligência Artificial analisar, 
    persiste os dados sensíveis de forma segura e notifica o Dashboard.
    """
    # 1. IA analisa o texto livre e extrai os dados de forma estruturada
    extraction = analyze_message_with_llm(message_text)
    
    db = SessionLocal()
    try:
        # 2. Lógica de Negócio: Se a intenção for agendar e tivermos todos os dados
        if extraction.intent == "AGENDAR" and extraction.cpf and extraction.date:
            
            # Criptografa o CPF antes de bater no banco
            cpf_enc = encrypt_data(extraction.cpf)
            
            # Busca ou cria o cliente
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
                
            # Salva o agendamento
            # (No app real, transformaríamos 'extraction.date' em um objeto datetime válido)
            new_appt = Appointment(
                client_id=client.id, 
                appointment_date=datetime.now(), 
                status="CONFIRMED"
            )
            db.add(new_appt)
            db.commit()
            
            # 3. Dispara evento em tempo real para a tela do Gestor
            event_data = {
                "type": "NEW_APPOINTMENT",
                "client": client.name,
                "status": "CONFIRMED",
                "timestamp": datetime.now().isoformat()
            }
            await ws_manager.broadcast(json.dumps(event_data))
            
        elif extraction.intent == "CANCELAR":
            # Aqui iria a lógica de buscar o agendamento no banco e mudar status para CANCELLED
            event_data = {
                "type": "CANCELLATION",
                "client": sender_id,
                "status": "CANCELLED",
                "timestamp": datetime.now().isoformat()
            }
            await ws_manager.broadcast(json.dumps(event_data))

    finally:
        db.close()

    # 4. A própria IA gerou a resposta conversacional e amigável!
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
                        
                        # POST back para a API do WhatsApp com o 'ai_response'
                        print(f"[{sender_id}] Resposta Enviada: {ai_response}")
                        
        return {"status": "success"}
    raise HTTPException(status_code=404)

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    Endpoint WebSocket para conexão do Dashboard (Next.js).
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
