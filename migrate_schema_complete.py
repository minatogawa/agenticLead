#!/usr/bin/env python3
"""
Script para migração completa do schema PostgreSQL
Remove inconsistências e recria tudo do zero
"""
import os
import sys
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime

# Importar novo schema
from database_postgres import Base, RawEntry, StructuredEntry

def drop_all_tables(engine):
    """Remove todas as tabelas existentes"""
    print("🗑️  Removendo todas as tabelas existentes...")
    
    try:
        # Conectar e remover tudo
        with engine.connect() as conn:
            # Desabilitar checagem de foreign keys temporariamente
            conn.execute(text("SET session_replication_role = replica;"))
            
            # Obter todas as tabelas
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT LIKE 'pg_%'
                AND tablename NOT LIKE 'sql_%'
            """))
            
            tables = [row[0] for row in result]
            
            # Remover cada tabela
            for table in tables:
                print(f"  🗑️  Removendo tabela: {table}")
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
            
            # Reabilitar checagem de foreign keys
            conn.execute(text("SET session_replication_role = DEFAULT;"))
            conn.commit()
            
        print("✅ Todas as tabelas removidas com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao remover tabelas: {e}")
        return False

def create_fresh_schema(engine):
    """Cria schema fresco com novo modelo"""
    print("📋 Criando novo schema PostgreSQL...")
    
    try:
        # Criar todas as tabelas
        Base.metadata.create_all(engine)
        print("✅ Novo schema criado com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar schema: {e}")
        return False

def migrate_data_from_csv(engine):
    """Migra dados do CSV para o novo schema"""
    print("📦 Migrando dados do CSV...")
    
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Verificar se existe arquivo CSV
        csv_file = "agenticlead_dados.csv"
        if not os.path.exists(csv_file):
            print(f"⚠️  Arquivo {csv_file} não encontrado, criando dados de exemplo...")
            create_sample_data(session)
            session.close()
            return True
        
        # Carregar dados do CSV
        df = pd.read_csv(csv_file)
        print(f"📊 Encontradas {len(df)} entradas no CSV")
        
        # Migrar dados
        for idx, row in df.iterrows():
            # Criar entrada bruta
            raw_entry = RawEntry(
                timestamp_captura=datetime.now(),
                agente_id=str(row.get('agente_id', f'user_{idx}')),
                texto_original=str(row.get('texto_original', row.get('nome', f'Entrada {idx}'))),
                processado=True,
                telegram_message_id=row.get('telegram_message_id', None),
                latitude=row.get('latitude', None),
                longitude=row.get('longitude', None)
            )
            session.add(raw_entry)
            session.flush()  # Para obter o ID
            
            # Criar entrada estruturada
            structured_entry = StructuredEntry(
                raw_text_id=raw_entry.id,
                data_contato=row.get('data_contato', None),
                hora_contato=row.get('hora_contato', None),
                nome=row.get('nome', None),
                telefone=row.get('telefone', None),
                bairro=row.get('bairro', None),
                referencia_local=row.get('referencia_local', None),
                tipo_demanda=row.get('tipo_demanda', None),
                descricao_curta=row.get('descricao_curta', None),
                prioridade_percebida=row.get('prioridade_percebida', None),
                fonte=row.get('fonte', 'csv_import'),
                confianca_global=float(row.get('confianca_global', 0.8)),
                extraction_status='completed',
                timestamp_processamento=datetime.now()
            )
            session.add(structured_entry)
        
        session.commit()
        
        # Verificar migração
        raw_count = session.query(RawEntry).count()
        structured_count = session.query(StructuredEntry).count()
        
        print(f"✅ Migração concluída:")
        print(f"   - Raw entries: {raw_count}")
        print(f"   - Structured entries: {structured_count}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração de dados: {e}")
        try:
            session.rollback()
            session.close()
        except:
            pass
        return False

def create_sample_data(session):
    """Cria dados de exemplo se não houver CSV"""
    print("📝 Criando dados de exemplo...")
    
    sample_data = [
        {
            'agente_id': 'user_1',
            'texto': 'Olá, meu nome é João Silva, telefone 11999887766. Moro no Jardim Europa e preciso de poda de árvore na Rua das Flores, 123.',
            'nome': 'João Silva',
            'telefone': '11999887766',
            'bairro': 'Jardim Europa',
            'tipo_demanda': 'ARVORE',
            'descricao': 'Poda de árvore necessária'
        },
        {
            'agente_id': 'user_2', 
            'texto': 'Maria Santos aqui, 11888776655. Bueiro entupido na Vila Nova, Rua São João próximo ao número 456.',
            'nome': 'Maria Santos',
            'telefone': '11888776655', 
            'bairro': 'Vila Nova',
            'tipo_demanda': 'BUEIRO',
            'descricao': 'Bueiro entupido'
        },
        {
            'agente_id': 'user_3',
            'texto': 'Carlos Oliveira, tel 11777665544. Limpeza urgente no Centro, muito lixo acumulado na Praça Central.',
            'nome': 'Carlos Oliveira',
            'telefone': '11777665544',
            'bairro': 'Centro', 
            'tipo_demanda': 'LIMPEZA',
            'descricao': 'Limpeza de praça necessária'
        }
    ]
    
    for i, data in enumerate(sample_data):
        # Criar entrada bruta
        raw_entry = RawEntry(
            timestamp_captura=datetime.now(),
            agente_id=data['agente_id'],
            texto_original=data['texto'],
            processado=True
        )
        session.add(raw_entry)
        session.flush()
        
        # Criar entrada estruturada
        structured_entry = StructuredEntry(
            raw_text_id=raw_entry.id,
            nome=data['nome'],
            telefone=data['telefone'],
            bairro=data['bairro'],
            tipo_demanda=data['tipo_demanda'],
            descricao_curta=data['descricao'],
            prioridade_percebida='MEDIA',
            fonte='sample_data',
            confianca_global=0.9,
            extraction_status='completed',
            timestamp_processamento=datetime.now()
        )
        session.add(structured_entry)
    
    session.commit()
    print("✅ Dados de exemplo criados")

def main():
    """Função principal de migração"""
    print("🔄 Iniciando migração completa do schema PostgreSQL")
    print("=" * 60)
    
    # Obter URL do PostgreSQL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL não configurada!")
        return False
    
    # Ajustar URL se necessário
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print(f"🔌 Conectando ao PostgreSQL: {database_url[:50]}...")
    
    try:
        # Criar engine
        engine = create_engine(database_url)
        
        # Testar conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Conexão PostgreSQL estabelecida")
        
        # Passo 1: Remover tabelas existentes
        if not drop_all_tables(engine):
            return False
        
        # Passo 2: Criar schema fresco
        if not create_fresh_schema(engine):
            return False
        
        # Passo 3: Migrar dados
        if not migrate_data_from_csv(engine):
            return False
        
        print("\n🎉 Migração completa realizada com sucesso!")
        print("\n📋 Próximos passos:")
        print("1. Substituir database.py por database_postgres.py")
        print("2. Atualizar web_app.py para usar novo schema")
        print("3. Testar aplicação")
        print("4. Fazer deploy")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante migração: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)