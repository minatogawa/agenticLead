"""
Módulo de banco de dados PostgreSQL para AgenticLead
Schema otimizado para PostgreSQL com compatibilidade total
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()

class RawEntry(Base):
    """Tabela para armazenar entradas brutas do Telegram"""
    __tablename__ = 'raw_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp_captura = Column(DateTime, default=datetime.utcnow, nullable=False)
    agente_id = Column(String(50), nullable=False)  # ID do usuário do Telegram
    texto_original = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    processado = Column(Boolean, default=False, nullable=False)
    telegram_message_id = Column(Integer, nullable=True)
    
    # Relationship
    structured_entries = relationship("StructuredEntry", back_populates="raw_entry")
    
    def __repr__(self):
        return f"<RawEntry(id={self.id}, agente_id='{self.agente_id}', processado={self.processado})>"

class StructuredEntry(Base):
    """Tabela para armazenar dados estruturados extraídos"""
    __tablename__ = 'structured_entries'
    
    # Chaves primárias e relacionamentos
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_text_id = Column(Integer, ForeignKey('raw_entries.id'), nullable=False)
    
    # Campos extraídos - Dados do contato
    data_contato = Column(String(10), nullable=True)  # YYYY-MM-DD
    hora_contato = Column(String(5), nullable=True)   # HH:MM
    nome = Column(String(100), nullable=True)
    telefone = Column(String(20), nullable=True)
    
    # Campos extraídos - Localização
    bairro = Column(String(100), nullable=True)
    referencia_local = Column(String(200), nullable=True)
    
    # Campos extraídos - Demanda
    tipo_demanda = Column(String(20), nullable=True)
    descricao_curta = Column(String(500), nullable=True)  # Aumentado para PostgreSQL
    prioridade_percebida = Column(String(10), nullable=True)
    
    # Metadados de controle
    fonte = Column(String(20), default="texto_digitado", nullable=False)
    confianca_global = Column(Float, nullable=True)
    flags = Column(JSON, nullable=True)  # Array de flags
    confianca_campos = Column(JSON, nullable=True)  # Dict com confiança por campo
    
    # Timestamps
    timestamp_processamento = Column(DateTime, default=datetime.utcnow, nullable=False)
    revisado = Column(Boolean, default=False, nullable=False)
    
    # Campos de controle LLM
    extraction_status = Column(String(20), default="pending", nullable=False)
    error_msg = Column(Text, nullable=True)
    llm_metadata = Column(JSON, nullable=True)  # Metadados do LLM em JSON
    processing_attempts = Column(Integer, default=0, nullable=False)
    last_processed_at = Column(DateTime, nullable=True)
    
    # Relationship
    raw_entry = relationship("RawEntry", back_populates="structured_entries")
    
    def __repr__(self):
        return f"<StructuredEntry(id={self.id}, nome='{self.nome}', status='{self.extraction_status}')>"

class DatabaseManager:
    """Classe para gerenciar conexões PostgreSQL de forma robusta"""
    
    def __init__(self, database_url=None):
        # Usar URL fornecida ou da variável de ambiente
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL não configurada!")
        
        # Ajustar URL para PostgreSQL se necessário
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
        
        # Configurar engine com pool de conexões otimizado para PostgreSQL
        self.engine = create_engine(
            self.database_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            echo=False  # Mudar para True para debug SQL
        )
        
        # Criar sessão
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Inicializar tabelas
        self.init_database()
    
    def init_database(self):
        """Inicializa as tabelas no banco de dados"""
        try:
            Base.metadata.create_all(self.engine)
            print("✅ Tabelas criadas/verificadas com sucesso")
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            raise
    
    def ensure_clean_transaction(self):
        """Garante que não há transações em estado de erro"""
        try:
            if self.session.in_transaction():
                self.session.rollback()
        except Exception:
            # Se houver erro, fechar e recriar sessão
            try:
                self.session.close()
            except:
                pass
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
    
    def safe_query(self, query_func):
        """Executa query com tratamento seguro de transações"""
        try:
            self.ensure_clean_transaction()
            return query_func()
        except Exception as e:
            self.ensure_clean_transaction()
            raise e
    
    def save_raw_entry(self, agente_id: str, texto: str, message_id: int = None, lat: float = None, lon: float = None):
        """Salva uma entrada bruta no banco"""
        def _save():
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
        
        return self.safe_query(_save)
    
    def get_unprocessed_entries(self):
        """Retorna entradas que ainda não foram processadas"""
        def _query():
            return self.session.query(RawEntry).filter(RawEntry.processado == False).all()
        
        return self.safe_query(_query)
    
    def mark_as_processed(self, raw_id: int):
        """Marca uma entrada como processada"""
        def _update():
            entry = self.session.query(RawEntry).filter(RawEntry.id == raw_id).first()
            if entry:
                entry.processado = True
                self.session.commit()
                return True
            return False
        
        return self.safe_query(_update)
    
    def save_structured_entry(self, structured_data: dict):
        """Salva dados estruturados extraídos"""
        def _save():
            entry = StructuredEntry(**structured_data)
            self.session.add(entry)
            self.session.commit()
            return entry.id
        
        return self.safe_query(_save)
    
    def get_entries_for_review(self, confidence_threshold: float = 0.75):
        """Retorna entradas que precisam de revisão manual"""
        def _query():
            return self.session.query(StructuredEntry).filter(
                StructuredEntry.confianca_global < confidence_threshold,
                StructuredEntry.revisado == False
            ).all()
        
        return self.safe_query(_query)
    
    def get_stats(self):
        """Retorna estatísticas do banco de dados"""
        def _query():
            total_raw = self.session.query(RawEntry).count()
            total_structured = self.session.query(StructuredEntry).count()
            unprocessed = self.session.query(RawEntry).filter(RawEntry.processado == False).count()
            
            return {
                'total_raw': total_raw,
                'total_structured': total_structured,
                'unprocessed': unprocessed,
                'coverage': round((total_structured / total_raw * 100) if total_raw > 0 else 0, 1)
            }
        
        return self.safe_query(_query)
    
    def close(self):
        """Fecha a conexão com o banco"""
        try:
            self.session.close()
        except:
            pass

# Instância global - será inicializada pela aplicação
db_manager = None

def init_db(database_url=None):
    """Inicializa o gerenciador de banco de dados"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    return db_manager

def get_db():
    """Retorna a instância do gerenciador de banco"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

# Para compatibilidade com código existente
class LegacyDatabase:
    """Wrapper para manter compatibilidade com código existente"""
    
    def __init__(self):
        self.manager = get_db()
        self.session = self.manager.session
    
    def ensure_transaction_rollback(self):
        return self.manager.ensure_clean_transaction()

# Instância para compatibilidade
db = LegacyDatabase()