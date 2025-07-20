"""
Script de migração e verificação do banco de dados
"""
from database import Base, RawEntry, StructuredEntry, Database
from config import DATABASE_URL
from sqlalchemy import create_engine, inspect

def verify_schema():
    """Verifica se o esquema do banco está correto"""
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    print("Verificando esquema do banco...")
    
    # Verificar tabelas existentes
    tables = inspector.get_table_names()
    expected_tables = ['raw_entries', 'structured_entries']
    
    for table in expected_tables:
        if table in tables:
            print(f"[OK] Tabela '{table}' encontrada")
            
            # Verificar colunas
            columns = inspector.get_columns(table)
            column_names = [col['name'] for col in columns]
            print(f"   Colunas: {', '.join(column_names)}")
        else:
            print(f"[ERRO] Tabela '{table}' nao encontrada")
    
    return len([t for t in expected_tables if t in tables]) == len(expected_tables)

def create_schema():
    """Cria o esquema do banco de dados"""
    print("Criando esquema do banco...")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    print("[OK] Esquema criado com sucesso!")

def get_stats():
    """Mostra estatísticas do banco"""
    db = Database()
    
    try:
        raw_count = db.session.query(RawEntry).count()
        structured_count = db.session.query(StructuredEntry).count()
        unprocessed_count = db.session.query(RawEntry).filter(RawEntry.processado == False).count()
        
        print(f"\nEstatisticas do banco:")
        print(f"   Raw entries: {raw_count}")
        print(f"   Structured entries: {structured_count}")
        print(f"   Nao processadas: {unprocessed_count}")
        
        return {
            'raw_count': raw_count,
            'structured_count': structured_count,
            'unprocessed_count': unprocessed_count
        }
    finally:
        db.close()

if __name__ == "__main__":
    print("AgenticLead - Migracao do Banco de Dados")
    print("=" * 50)
    
    # Criar esquema se necessário
    create_schema()
    
    # Verificar esquema
    if verify_schema():
        print("[OK] Esquema do banco verificado com sucesso!")
    else:
        print("[ERRO] Problemas encontrados no esquema do banco")
    
    # Mostrar estatísticas
    get_stats()
    
    print("\nMigracao concluida!")