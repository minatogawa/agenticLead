#!/usr/bin/env python3
"""
Criar tabela raw_entries no PostgreSQL
"""
import pandas as pd
from sqlalchemy import create_engine, text

# URL direta do PostgreSQL
DATABASE_URL = "postgresql://postgres:HMjrapQYaqXpKVYwrHbNtzRHHIdQhmJZ@shinkansen.proxy.rlwy.net:15314/railway"

def create_raw_entries():
    """Cria tabela raw_entries no PostgreSQL"""
    print("Criando tabela raw_entries...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Ler dados do CSV
        df = pd.read_csv("agenticlead_dados.csv")
        print(f"Processando {len(df)} registros...")
        
        # Criar dados para raw_entries baseado no CSV
        raw_data = []
        
        for _, row in df.iterrows():
            raw_data.append({
                'id': row['raw_text_id'],
                'timestamp_captura': row['timestamp_captura'],
                'agente_id': row.get('agente_id', ''),
                'texto_original': row.get('texto_original', ''),
                'latitude': None,
                'longitude': None,
                'processado': True,
                'telegram_message_id': None
            })
        
        df_raw = pd.DataFrame(raw_data)
        
        # Remover duplicatas por ID
        df_raw = df_raw.drop_duplicates(subset=['id'])
        
        print(f"Criando {len(df_raw)} registros em raw_entries...")
        
        # Inserir no PostgreSQL
        df_raw.to_sql(
            'raw_entries',
            engine,
            if_exists='replace',
            index=False,
            method='multi'
        )
        
        print(f"Tabela raw_entries criada com {len(df_raw)} registros!")
        return True
        
    except Exception as e:
        print(f"Erro: {e}")
        return False

if __name__ == "__main__":
    success = create_raw_entries()
    if success:
        print("Tabela raw_entries criada com sucesso!")
    else:
        print("Falha ao criar tabela raw_entries!")