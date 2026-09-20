import os
from pydantic import BaseModel, Field
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Garante que a chave da API esteja disponível no ambiente
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-mock-key-for-now")

class AppointmentExtraction(BaseModel):
    """
    Esquema de dados (Function Calling) que força a IA a retornar
    as variáveis exatas que precisamos para o sistema.
    """
    intent: str = Field(description="A intenção do usuário: deve ser exatamente 'AGENDAR', 'CANCELAR', ou 'OUTRO'")
    name: Optional[str] = Field(description="Nome do cliente, se ele tiver fornecido na conversa")
    cpf: Optional[str] = Field(description="CPF do cliente contendo apenas números, se fornecido")
    date: Optional[str] = Field(description="Data e horário solicitados para o agendamento, se fornecidos")
    reply_message: str = Field(description="A mensagem de resposta natural e cordial que enviaremos de volta ao WhatsApp do cliente")

def analyze_message_with_llm(message_text: str) -> AppointmentExtraction:
    """
    Utiliza o GPT (OpenAI) para interpretar o texto natural do usuário.
    O método '.with_structured_output' mapeia a saída da LLM para o objeto Pydantic.
    """
    # Inicializa o modelo configurado para zero alucinação (temperature=0)
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    structured_llm = llm.with_structured_output(AppointmentExtraction)

    system_prompt = (
        "Você é um assistente virtual cordial de uma empresa, focado em gerenciar agendamentos via WhatsApp.\n"
        "Seu objetivo principal é identificar se o usuário deseja AGENDAR ou CANCELAR.\n\n"
        "REGRAS DE NEGÓCIO:\n"
        "1. Para confirmar um agendamento, é OBRIGATÓRIO ter: Nome, CPF e Data desejada.\n"
        "2. Se o usuário quiser agendar mas faltar algum dado, a sua 'reply_message' deve solicitar "
        "educadamente o dado faltante.\n"
        "3. Se ele já forneceu tudo, agradeça e confirme o agendamento na 'reply_message'.\n"
        "4. Se a intenção for apenas bater papo ou dúvidas, classifique como 'OUTRO'."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{text}")
    ])

    chain = prompt | structured_llm

    # Invoca o modelo passando a mensagem do WhatsApp
    result = chain.invoke({"text": message_text})
    
    return result
