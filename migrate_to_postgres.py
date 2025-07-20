#!/usr/bin/env python3
"""
Script para migrar dados do SQLite local para PostgreSQL no Railway
"""
import pandas as pd
from sqlalchemy import create_engine, text
from database import Base, RawEntry, StructuredEntry
from config import DATABASE_URL
import os
from datetime import datetime

def migrate_data():
    """Migra dados do CSV local para PostgreSQL"""
    print("Iniciando migracao para PostgreSQL...")
    
    # Verificar se temos a DATABASE_URL do PostgreSQL
    if not DATABASE_URL.startswith("postgresql://"):
        print("DATABASE_URL deve ser PostgreSQL para migracao")
        print(f"URL atual: {DATABASE_URL}")
        return False
    
    try:
        # Conectar ao PostgreSQL
        engine = create_engine(DATABASE_URL)
        
        # Criar todas as tabelas
        print("Criando tabelas no PostgreSQL...")
        Base.metadata.create_all(engine)
        
        # Ler dados do CSV local
        print("Lendo dados do arquivo CSV local...")
        csv_file = "agenticlead_dados.csv"
        
        if not os.path.exists(csv_file):
            print(f"Arquivo {csv_file} nao encontrado")
            return False
        
        df = pd.read_csv(csv_file)
        print(f"Encontrados {len(df)} registros no CSV")
        
        # Migrar dados para PostgreSQL
        with engine.connect() as conn:
            # Limpar tabelas existentes
            print("Limpando tabelas existentes...")
            conn.execute(text("DELETE FROM structured_entries"))
            conn.execute(text("DELETE FROM raw_entries"))
            conn.commit()
            
            # Inserir dados
            print("Inserindo dados no PostgreSQL...")
            migrated = 0
            
            for _, row in df.iterrows():
                try:
                    # Inserir na tabela raw_entries (dados originais)
                    raw_query = text("""
                        INSERT INTO raw_entries (id, texto_original, timestamp_captura, user_id)
                        VALUES (:id, :texto, :timestamp, :user_id)
                        ON CONFLICT (id) DO NOTHING
                    """)
                    
                    conn.execute(raw_query, {
                        'id': row['raw_text_id'],
                        'texto': row.get('texto_original', ''),
                        'timestamp': row.get('timestamp_captura', datetime.now()),
                        'user_id': row.get('user_id', '')
                    })
                    
                    # Inserir na tabela structured_entries (dados processados)
                    struct_query = text("""
                        INSERT INTO structured_entries (
                            id, raw_text_id, data_contato, hora_contato, nome, telefone,
                            bairro, referencia_local, tipo_demanda, descricao_curta,
                            prioridade_percebida, urgente_reportado, origem_dados,
                            confianca_global, timestamp_processamento, revisado,
                            extraction_status
                        ) VALUES (
                            :id, :raw_id, :data, :hora, :nome, :telefone,
                            :bairro, :referencia, :tipo, :descricao,
                            :prioridade, :urgente, :origem, :confianca,
                            :timestamp, :revisado, :status
                        ) ON CONFLICT (id) DO NOTHING
                    """)
                    
                    conn.execute(struct_query, {
                        'id': row['id_registro'],
                        'raw_id': row['raw_text_id'],
                        'data': row.get('data_contato'),
                        'hora': row.get('hora_contato'),
                        'nome': row.get('nome', ''),
                        'telefone': row.get('telefone', ''),
                        'bairro': row.get('bairro', ''),
                        'referencia': row.get('referencia_local', ''),
                        'tipo': row.get('tipo_demanda', ''),
                        'descricao': row.get('descricao_curta', ''),
                        'prioridade': row.get('prioridade_percebida', ''),
                        'urgente': row.get('urgente_reportado', False),
                        'origem': row.get('origem_dados', 'migração'),
                        'confianca': row.get('confianca_global', 0.0),
                        'timestamp': row.get('timestamp_processamento', datetime.now()),
                        'revisado': row.get('revisado', False),
                        'status': 'completed'
                    })
                    
                    migrated += 1
                    
                except Exception as e:
                    print(f"Erro ao migrar registro {row.get('id_registro', 'N/A')}: {e}")
                    continue
            
            conn.commit()
            
        print(f"Migracao concluida! {migrated} registros migrados para PostgreSQL")
        return True
        
    except Exception as e:
        print(f"Erro durante migracao: {e}")
        return False

if __name__ == "__main__":
    success = migrate_data()
    if success:
        print("Migracao bem-sucedida!")
    else:
        print("Migracao falhou!")