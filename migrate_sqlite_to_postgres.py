#!/usr/bin/env python3
"""
Script para migrar dados do SQLite para PostgreSQL
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import Base, RawEntry, StructuredEntry
from config import DATABASE_URL

def migrate_data():
    """Migra dados do SQLite para PostgreSQL"""
    
    # URLs dos bancos
    sqlite_url = "sqlite:///agenticlead.db"
    
    # Usar PostgreSQL URL do ambiente ou Railway
    postgres_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    
    if not postgres_url or postgres_url.startswith("sqlite"):
        print("❌ URL do PostgreSQL não configurada!")
        print("Configure a variável POSTGRES_URL ou DATABASE_URL com a URL do PostgreSQL")
        print("Exemplo: postgresql://user:pass@host:port/dbname")
        return False
    
    # Ajustar URL se necessário
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)
    
    print(f"🔄 Migrando de SQLite para PostgreSQL...")
    print(f"SQLite: {sqlite_url}")
    print(f"PostgreSQL: {postgres_url[:50]}...")
    
    try:
        # Conectar ao SQLite (origem)
        sqlite_engine = create_engine(sqlite_url)
        SqliteSession = sessionmaker(bind=sqlite_engine)
        sqlite_session = SqliteSession()
        
        # Conectar ao PostgreSQL (destino)
        postgres_engine = create_engine(postgres_url)
        PostgresSession = sessionmaker(bind=postgres_engine)
        postgres_session = PostgresSession()
        
        # Criar tabelas no PostgreSQL
        print("📋 Criando tabelas no PostgreSQL...")
        Base.metadata.create_all(postgres_engine)
        
        # Limpar tabelas existentes no PostgreSQL (se existirem)
        print("🧹 Limpando dados existentes no PostgreSQL...")
        postgres_session.execute(text("DELETE FROM structured_entries"))
        postgres_session.execute(text("DELETE FROM raw_entries"))
        postgres_session.commit()
        
        # Migrar raw_entries
        print("📦 Migrando raw_entries...")
        raw_entries = sqlite_session.query(RawEntry).all()
        
        for entry in raw_entries:
            new_entry = RawEntry(
                id=entry.id,
                timestamp_captura=entry.timestamp_captura,
                agente_id=entry.agente_id,
                texto_original=entry.texto_original,
                latitude=entry.latitude,
                longitude=entry.longitude,
                processado=entry.processado,
                telegram_message_id=entry.telegram_message_id
            )
            postgres_session.add(new_entry)
        
        postgres_session.commit()
        print(f"✅ Migradas {len(raw_entries)} entradas brutas")
        
        # Migrar structured_entries
        print("📊 Migrando structured_entries...")
        structured_entries = sqlite_session.query(StructuredEntry).all()
        
        for entry in structured_entries:
            new_entry = StructuredEntry(
                id=entry.id,
                raw_text_id=entry.raw_text_id,
                data_contato=entry.data_contato,
                hora_contato=entry.hora_contato,
                nome=entry.nome,
                telefone=entry.telefone,
                bairro=entry.bairro,
                referencia_local=entry.referencia_local,
                tipo_demanda=entry.tipo_demanda,
                descricao_curta=entry.descricao_curta,
                prioridade_percebida=entry.prioridade_percebida,
                consentimento_comunicacao=entry.consentimento_comunicacao,
                fonte=entry.fonte,
                confianca_global=entry.confianca_global,
                flags=entry.flags,
                confianca_campos=entry.confianca_campos,
                timestamp_processamento=entry.timestamp_processamento,
                revisado=entry.revisado,
                extraction_status=entry.extraction_status,
                error_msg=entry.error_msg,
                llm_metadata=entry.llm_metadata,
                processing_attempts=entry.processing_attempts,
                last_processed_at=entry.last_processed_at
            )
            postgres_session.add(new_entry)
        
        postgres_session.commit()
        print(f"✅ Migradas {len(structured_entries)} entradas estruturadas")
        
        # Verificar dados migrados
        print("\n📊 Verificando migração...")
        pg_raw_count = postgres_session.query(RawEntry).count()
        pg_structured_count = postgres_session.query(StructuredEntry).count()
        
        print(f"PostgreSQL - Raw entries: {pg_raw_count}")
        print(f"PostgreSQL - Structured entries: {pg_structured_count}")
        
        # Fechar sessões
        sqlite_session.close()
        postgres_session.close()
        
        print("\n🎉 Migração concluída com sucesso!")
        print("\n⚙️  Próximos passos:")
        print("1. Atualize o arquivo .env com a URL do PostgreSQL")
        print("2. Teste a aplicação")
        print("3. Faça backup do SQLite antes de deletá-lo")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Iniciando migração SQLite → PostgreSQL")
    print("=" * 50)
    
    if migrate_data():
        print("\n✅ Migração concluída!")
    else:
        print("\n❌ Migração falhou!")
        sys.exit(1)