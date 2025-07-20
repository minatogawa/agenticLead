#!/usr/bin/env python3
"""
Recriar tabela PostgreSQL com schema correto
"""
import pandas as pd
from sqlalchemy import create_engine, text

# URL direta do PostgreSQL
DATABASE_URL = "postgresql://postgres:HMjrapQYaqXpKVYwrHbNtzRHHIdQhmJZ@shinkansen.proxy.rlwy.net:15314/railway"

def recreate_postgres():
    """Recria tabela PostgreSQL com schema correto"""
    print("Recriando tabela PostgreSQL com schema correto...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Ler dados do CSV
        df = pd.read_csv("agenticlead_dados.csv")
        print(f"Lendo {len(df)} registros do CSV...")
        
        # Preparar dados para corresponder ao schema do código
        df_clean = df.copy()
        
        # Renomear/mapear colunas para o schema correto
        column_mapping = {
            'id_registro': 'id',
            'consentimento_comunicacao': 'urgente_reportado', 
            'fonte': 'origem_dados'
        }
        
        df_clean = df_clean.rename(columns=column_mapping)
        
        # Adicionar colunas que faltam com valores padrão
        df_clean['extraction_status'] = 'completed'
        df_clean['processing_attempts'] = 0
        df_clean['error_msg'] = None
        df_clean['llm_metadata'] = None
        df_clean['last_processed_at'] = None
        df_clean['flags'] = None
        df_clean['confianca_campos'] = None
        
        # Selecionar apenas colunas que existem no schema
        final_columns = [
            'id', 'raw_text_id', 'data_contato', 'hora_contato', 'nome', 
            'telefone', 'bairro', 'referencia_local', 'tipo_demanda', 
            'descricao_curta', 'prioridade_percebida', 'urgente_reportado',
            'origem_dados', 'confianca_global', 'flags', 'confianca_campos',
            'timestamp_processamento', 'revisado', 'extraction_status',
            'error_msg', 'llm_metadata', 'processing_attempts', 'last_processed_at'
        ]
        
        # Filtrar apenas colunas que existem
        available_columns = [col for col in final_columns if col in df_clean.columns]
        df_final = df_clean[available_columns].copy()
        
        print(f"Colunas preparadas: {available_columns}")
        
        # Inserir no PostgreSQL (substituir tabela existente)
        with engine.connect() as conn:
            # Dropar tabela existente
            conn.execute(text("DROP TABLE IF EXISTS structured_entries"))
            conn.commit()
            
        # Inserir dados (pandas vai criar a tabela)
        df_final.to_sql(
            'structured_entries',
            engine,
            if_exists='replace',
            index=False,
            method='multi'
        )
        
        print(f"Tabela recreada com {len(df_final)} registros!")
        return True
        
    except Exception as e:
        print(f"Erro: {e}")
        return False

if __name__ == "__main__":
    success = recreate_postgres()
    if success:
        print("Tabela PostgreSQL recreada com sucesso!")
    else:
        print("Falha ao recriar tabela!")