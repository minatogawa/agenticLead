"""
Módulo de banco de dados para AgenticLead
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()

class RawEntry(Base):
    """Tabela para armazenar entradas brutas do Telegram"""
    __tablename__ = 'raw_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp_captura = Column(DateTime, default=datetime.utcnow)
    agente_id = Column(String(50))  # ID do usuário do Telegram
    texto_original = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    processado = Column(Boolean, default=False)
    telegram_message_id = Column(Integer, nullable=True)
    
class StructuredEntry(Base):
    """Tabela para armazenar dados estruturados extraídos"""
    __tablename__ = 'structured_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_text_id = Column(Integer, nullable=False)  # FK para raw_entries
    
    # Campos extraídos
    data_contato = Column(String(10))  # YYYY-MM-DD
    hora_contato = Column(String(5))   # HH:MM
    nome = Column(String(100))
    telefone = Column(String(20))
    bairro = Column(String(100))
    referencia_local = Column(String(200))
    tipo_demanda = Column(String(20))
    descricao_curta = Column(String(120))
    prioridade_percebida = Column(String(10))
    consentimento_comunicacao = Column(Boolean)
    fonte = Column(String(20), default="texto_digitado")
    
    # Metadados
    confianca_global = Column(Float)
    flags = Column(JSON)  # Array de flags
    confianca_campos = Column(JSON)  # Dict com confiança por campo
    timestamp_processamento = Column(DateTime, default=datetime.utcnow)
    revisado = Column(Boolean, default=False)

class Database:
    """Classe para gerenciar conexões com o banco"""
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def save_raw_entry(self, agente_id: str, texto: str, message_id: int = None, lat: float = None, lon: float = None):
        """Salva uma entrada bruta no banco"""
        entry = RawEntry(
            agente_id=agente_id,
            texto_original=texto,
            telegram_message_id=message_id,
            latitude=lat,
            longitude=lon
        )
        self.session.add(entry)
        self.session.commit()
        return entry.id
    
    def get_unprocessed_entries(self):
        """Retorna entradas que ainda não foram processadas"""
        return self.session.query(RawEntry).filter(RawEntry.processado == False).all()
    
    def mark_as_processed(self, raw_id: int):
        """Marca uma entrada como processada"""
        entry = self.session.query(RawEntry).filter(RawEntry.id == raw_id).first()
        if entry:
            entry.processado = True
            self.session.commit()
    
    def save_structured_entry(self, structured_data: dict):
        """Salva dados estruturados extraídos"""
        entry = StructuredEntry(**structured_data)
        self.session.add(entry)
        self.session.commit()
        return entry.id
    
    def get_entries_for_review(self, confidence_threshold: float = 0.75):
        """Retorna entradas que precisam de revisão manual"""
        return self.session.query(StructuredEntry).filter(
            StructuredEntry.confianca_global < confidence_threshold,
            StructuredEntry.revisado == False
        ).all()
    
    def close(self):
        """Fecha a conexão com o banco"""
        self.session.close()

# Instância global do banco
db = Database()