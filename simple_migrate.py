#!/usr/bin/env python3
"""
Script simples para migrar apenas dados estruturados para PostgreSQL
"""
import pandas as pd
from sqlalchemy import create_engine, text
from config import DATABASE_URL
import os

def simple_migrate():
    """Migra apenas dados estruturados do CSV para PostgreSQL"""
    print("Iniciando migracao simples para PostgreSQL...")
    
    try:
        # Conectar ao PostgreSQL
        engine = create_engine(DATABASE_URL)
        
        # Ler dados do CSV local
        print("Lendo dados do arquivo CSV local...")
        csv_file = "agenticlead_dados.csv"
        
        if not os.path.exists(csv_file):
            print(f"Arquivo {csv_file} nao encontrado")
            return False
        
        df = pd.read_csv(csv_file)
        print(f"Encontrados {len(df)} registros no CSV")
        
        # Migrar apenas structured_entries
        print("Inserindo dados estruturados no PostgreSQL...")
        
        # Usar pandas para inserir direto - usar apenas colunas que existem
        df_clean = df[[
            'id_registro', 'raw_text_id', 'data_contato', 'hora_contato', 
            'nome', 'telefone', 'bairro', 'referencia_local', 
            'tipo_demanda', 'descricao_curta', 'prioridade_percebida',
            'consentimento_comunicacao', 'fonte', 'confianca_global', 
            'timestamp_processamento', 'revisado'
        ]].copy()
        
        # Renomear colunas para match com DB
        df_clean = df_clean.rename(columns={
            'id_registro': 'id',
            'consentimento_comunicacao': 'urgente_reportado',
            'fonte': 'origem_dados'
        })
        
        # Adicionar campos padrão
        df_clean['extraction_status'] = 'completed'
        df_clean['processing_attempts'] = 0
        
        # Inserir no PostgreSQL
        df_clean.to_sql(
            'structured_entries', 
            engine, 
            if_exists='replace',  # Substitui tabela existente
            index=False,
            method='multi'
        )
        
        print(f"Migracao concluida! {len(df_clean)} registros migrados")
        return True
        
    except Exception as e:
        print(f"Erro durante migracao: {e}")
        return False

if __name__ == "__main__":
    success = simple_migrate()
    if success:
        print("Migracao simples bem-sucedida!")
    else:
        print("Migracao simples falhou!")