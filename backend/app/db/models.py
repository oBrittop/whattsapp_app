from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Client(Base):
    """
    Modelo de Cliente.
    O campo 'cpf_encrypted' armazena o CPF ofuscado pela camada de seguranca.
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    whatsapp_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    cpf_encrypted = Column(String, nullable=False)
    
    appointments = relationship("Appointment", back_populates="client")

class Appointment(Base):
    """
    Modelo de Agendamento.
    Vinculado a um cliente especifico e contem o status da reserva.
    """
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    status = Column(String, default="CONFIRMED")
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="appointments")
