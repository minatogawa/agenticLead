#!/usr/bin/env python3
"""
Corrigir schema do PostgreSQL para corresponder ao código
"""
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def fix_schema():
    """Corrige schema do PostgreSQL"""
    print("Corrigindo schema do PostgreSQL...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Adicionar colunas que faltam na tabela structured_entries
            print("Adicionando colunas faltantes...")
            
            # Lista de colunas para adicionar
            alter_queries = [
                "ALTER TABLE structured_entries ADD COLUMN IF NOT EXISTS urgente_reportado BOOLEAN DEFAULT FALSE",
                "ALTER TABLE structured_entries ADD COLUMN IF NOT EXISTS origem_dados VARCHAR(50) DEFAULT 'migração'",
                "ALTER TABLE structured_entries ADD COLUMN IF NOT EXISTS flags TEXT",
                "ALTER TABLE structured_entries ADD COLUMN IF NOT EXISTS confianca_campos TEXT",
                "ALTER TABLE structured_entries ADD COLUMN IF NOT EXISTS error_msg TEXT",
                "ALTER TABLE structured_entries ADD COLUMN IF NOT EXISTS llm_metadata TEXT",
                "ALTER TABLE structured_entries ADD COLUMN IF NOT EXISTS last_processed_at TIMESTAMP"
            ]
            
            for query in alter_queries:
                try:
                    conn.execute(text(query))
                    print(f"✓ {query}")
                except Exception as e:
                    print(f"! {query} - {e}")
            
            # Atualizar dados existentes
            print("Atualizando dados existentes...")
            
            # Atualizar colunas renomeadas
            update_queries = [
                "UPDATE structured_entries SET urgente_reportado = COALESCE(consentimento_comunicacao, FALSE) WHERE urgente_reportado IS NULL",
                "UPDATE structured_entries SET origem_dados = COALESCE(fonte, 'migração') WHERE origem_dados IS NULL"
            ]
            
            for query in update_queries:
                try:
                    conn.execute(text(query))
                    print(f"✓ {query}")
                except Exception as e:
                    print(f"! {query} - {e}")
            
            conn.commit()
            
        print("Schema corrigido com sucesso!")
        return True
        
    except Exception as e:
        print(f"Erro ao corrigir schema: {e}")
        return False

if __name__ == "__main__":
    # Temporariamente usar PostgreSQL
    import os
    os.environ['DATABASE_URL'] = 'postgresql://postgres:HMjrapQYaqXpKVYwrHbNtzRHHIdQhmJZ@shinkansen.proxy.rlwy.net:15314/railway'
    
    success = fix_schema()
    if success:
        print("✅ Schema PostgreSQL corrigido!")
    else:
        print("❌ Falha ao corrigir schema!")