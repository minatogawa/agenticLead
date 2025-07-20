"""
Migração para adicionar campos LLM na tabela structured_entries
E3-S5: Campos de status de processamento
"""
from database import db, StructuredEntry
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def add_llm_status_fields():
    """Adiciona campos de controle de extração LLM"""
    print("Adicionando campos de status LLM...")
    
    fields_to_add = [
        ("extraction_status", "VARCHAR(20) DEFAULT 'pending'"),
        ("error_msg", "TEXT"),
        ("llm_metadata", "TEXT"),
        ("processing_attempts", "INTEGER DEFAULT 0"),
        ("last_processed_at", "DATETIME")
    ]
    
    for field_name, field_definition in fields_to_add:
        try:
            query = f"ALTER TABLE structured_entries ADD COLUMN {field_name} {field_definition}"
            db.session.execute(text(query))
            db.session.commit()
            print(f"  [OK] Campo '{field_name}' adicionado")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print(f"  [SKIP] Campo '{field_name}' já existe")
            else:
                print(f"  [ERRO] Falha ao adicionar '{field_name}': {e}")

def update_existing_entries():
    """Atualiza entradas existentes com status inicial"""
    print("\nAtualizando entradas existentes...")
    
    try:
        # Marcar placeholders vazios como pending
        result = db.session.execute(text("""
            UPDATE structured_entries 
            SET extraction_status = 'pending'
            WHERE extraction_status IS NULL
            AND (nome IS NULL AND telefone IS NULL AND tipo_demanda IS NULL)
        """))
        
        # Marcar entradas que já têm dados como completed
        result2 = db.session.execute(text("""
            UPDATE structured_entries 
            SET extraction_status = 'completed'
            WHERE extraction_status IS NULL
            AND (nome IS NOT NULL OR telefone IS NOT NULL OR tipo_demanda IS NOT NULL)
        """))
        
        db.session.commit()
        
        print(f"  [OK] {result.rowcount} entradas marcadas como 'pending'")
        print(f"  [OK] {result2.rowcount} entradas marcadas como 'completed'")
        
    except Exception as e:
        print(f"  [ERRO] Falha ao atualizar entradas: {e}")

def show_migration_status():
    """Mostra status após migração"""
    print("\nStatus após migração:")
    
    try:
        # Contar por status
        result = db.session.execute(text("""
            SELECT extraction_status, COUNT(*) as count
            FROM structured_entries 
            GROUP BY extraction_status
        """)).fetchall()
        
        for row in result:
            status = row[0] or 'NULL'
            count = row[1]
            print(f"  {status}: {count} entradas")
            
    except Exception as e:
        print(f"  [ERRO] Não foi possível mostrar status: {e}")

def main():
    print("AgenticLead - Migração LLM")
    print("=" * 30)
    
    # Adicionar campos
    add_llm_status_fields()
    
    # Atualizar entradas existentes
    update_existing_entries()
    
    # Mostrar status final
    show_migration_status()
    
    print("\nMigração concluída!")

if __name__ == "__main__":
    main()