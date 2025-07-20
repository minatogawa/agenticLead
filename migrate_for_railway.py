#!/usr/bin/env python3
"""
Script para migrar dados do CSV diretamente para PostgreSQL no Railway
Este script será executado no Railway onde o PostgreSQL é acessível
"""
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import Base, RawEntry, StructuredEntry
from datetime import datetime

def migrate_from_csv():
    """Migra dados do CSV para PostgreSQL"""
    
    # URL do PostgreSQL (será automática no Railway)
    postgres_url = os.getenv("DATABASE_URL")
    
    if not postgres_url:
        print("❌ DATABASE_URL não configurada!")
        return False
    
    # Ajustar URL se necessário
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)
    
    print(f"🔄 Migrando dados do CSV para PostgreSQL...")
    print(f"PostgreSQL: {postgres_url[:50]}...")
    
    try:
        # Conectar ao PostgreSQL
        engine = create_engine(postgres_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Forçar a recriação da tabela para garantir o esquema mais recente
        print("💣 Excluindo tabela structured_entries para garantir atualização do esquema...")
        StructuredEntry.__table__.drop(engine, checkfirst=True)

        # Criar tabelas
        print("📋 Criando tabelas no PostgreSQL (com esquema atualizado)...")
        Base.metadata.create_all(engine)
        
        # Limpar tabelas existentes (redundante se a tabela foi dropada, mas seguro)
        print("🧹 Limpando dados existentes...")
        session.execute(text("DELETE FROM structured_entries"))
        session.execute(text("DELETE FROM raw_entries"))
        session.commit()
        
        # Verificar se existe arquivo CSV
        csv_file = "agenticlead_dados.csv"
        if not os.path.exists(csv_file):
            print(f"❌ Arquivo {csv_file} não encontrado!")
            return False
        
        # Carregar dados do CSV
        print(f"📦 Carregando dados do {csv_file}...")
        df = pd.read_csv(csv_file)
        
        print(f"📊 Encontradas {len(df)} entradas no CSV")
        
        # Migrar dados para raw_entries primeiro
        for idx, row in df.iterrows():
            # Criar entrada bruta
            raw_entry = RawEntry(
                id=idx + 1,
                timestamp_captura=datetime.now(),
                agente_id=str(row.get('agente_id', 'unknown')),
                texto_original=str(row.get('texto_original', '')),
                processado=True,
                telegram_message_id=row.get('telegram_message_id', None)
            )
            session.add(raw_entry)
            
            # Criar entrada estruturada
            structured_entry = StructuredEntry(
                id=idx + 1,
                raw_text_id=idx + 1,
                data_contato=row.get('data_contato', None),
                hora_contato=row.get('hora_contato', None),
                nome=row.get('nome', None),
                telefone=row.get('telefone', None),
                bairro=row.get('bairro', None),
                referencia_local=row.get('referencia_local', None),
                tipo_demanda=row.get('tipo_demanda', None),
                descricao_curta=row.get('descricao_curta', None),
                prioridade_percebida=row.get('prioridade_percebida', None),
                consentimento_comunicacao=row.get('consentimento_comunicacao', None),
                fonte=row.get('fonte', 'csv_import'),
                confianca_global=row.get('confianca_global', 0.8),
                extraction_status='completed',
                timestamp_processamento=datetime.now()
            )
            session.add(structured_entry)
        
        session.commit()
        
        # Verificar dados migrados
        print("\n📊 Verificando migração...")
        raw_count = session.query(RawEntry).count()
        structured_count = session.query(StructuredEntry).count()
        
        print(f"PostgreSQL - Raw entries: {raw_count}")
        print(f"PostgreSQL - Structured entries: {structured_count}")
        
        session.close()
        
        print("\n🎉 Migração concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Iniciando migração CSV → PostgreSQL (Railway)")
    print("=" * 50)
    
    if migrate_from_csv():
        print("\n✅ Migração concluída!")
    else:
        print("\n❌ Migração falhou!")
        sys.exit(1)