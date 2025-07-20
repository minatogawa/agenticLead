"""
Processador de dados - Job de associação raw→structured
"""
from database import db, RawEntry, StructuredEntry
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    """Classe responsável por processar entradas raw e criar structured"""
    
    def __init__(self):
        self.db = db
    
    def create_placeholder_entry(self, raw_entry: RawEntry) -> int:
        """
        Cria uma entrada estruturada vazia (placeholder) para uma raw_entry
        Conforme especificação E2-S2: "Registra linha estrut. vazia para cada raw"
        """
        try:
            structured_data = {
                'raw_text_id': raw_entry.id,
                'data_contato': None,
                'hora_contato': None,
                'nome': None,
                'telefone': None,
                'bairro': None,
                'referencia_local': None,
                'tipo_demanda': None,
                'descricao_curta': None,
                'prioridade_percebida': None,
                'consentimento_comunicacao': None,
                'fonte': 'texto_digitado',
                'confianca_global': 0.0,
                'flags': [],
                'confianca_campos': {},
                'timestamp_processamento': datetime.utcnow(),
                'revisado': False
            }
            
            structured_id = self.db.save_structured_entry(structured_data)
            logger.info(f"Placeholder criado: raw_id={raw_entry.id} -> structured_id={structured_id}")
            
            return structured_id
            
        except Exception as e:
            logger.error(f"Erro ao criar placeholder para raw_id={raw_entry.id}: {e}")
            raise
    
    def process_unprocessed_entries(self) -> dict:
        """
        Processa todas as entradas raw não processadas
        Cria placeholders para garantir 100% de cobertura
        """
        results = {
            'processed': 0,
            'errors': 0,
            'created_ids': []
        }
        
        try:
            # Buscar entradas não processadas
            unprocessed = self.db.get_unprocessed_entries()
            
            logger.info(f"Processando {len(unprocessed)} entradas não processadas")
            
            for raw_entry in unprocessed:
                try:
                    # Verificar se já existe structured_entry para esta raw
                    existing = self.db.session.query(StructuredEntry).filter(
                        StructuredEntry.raw_text_id == raw_entry.id
                    ).first()
                    
                    if existing:
                        logger.info(f"Structured entry já existe para raw_id={raw_entry.id}")
                        # Marcar como processada
                        self.db.mark_as_processed(raw_entry.id)
                        continue
                    
                    # Criar placeholder
                    structured_id = self.create_placeholder_entry(raw_entry)
                    results['created_ids'].append(structured_id)
                    
                    # Marcar raw_entry como processada
                    self.db.mark_as_processed(raw_entry.id)
                    
                    results['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao processar raw_id={raw_entry.id}: {e}")
                    results['errors'] += 1
            
            logger.info(f"Processamento concluído: {results['processed']} criadas, {results['errors']} erros")
            return results
            
        except Exception as e:
            logger.error(f"Erro no processamento batch: {e}")
            raise
    
    def get_processing_stats(self) -> dict:
        """Retorna estatísticas do processamento"""
        try:
            total_raw = self.db.session.query(RawEntry).count()
            total_structured = self.db.session.query(StructuredEntry).count()
            unprocessed = self.db.session.query(RawEntry).filter(RawEntry.processado == False).count()
            
            # Verificar cobertura (raw entries que têm structured correspondente)
            raw_with_structured = self.db.session.query(RawEntry).join(
                StructuredEntry, RawEntry.id == StructuredEntry.raw_text_id
            ).count()
            
            coverage_percent = (raw_with_structured / total_raw * 100) if total_raw > 0 else 0
            
            return {
                'total_raw': total_raw,
                'total_structured': total_structured,
                'unprocessed': unprocessed,
                'raw_with_structured': raw_with_structured,
                'coverage_percent': round(coverage_percent, 2)
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return {}

def run_processor():
    """Função principal para executar o processamento"""
    print("AgenticLead - Processador de Dados")
    print("=" * 40)
    
    processor = DataProcessor()
    
    # Mostrar estatísticas antes
    print("ANTES do processamento:")
    stats_before = processor.get_processing_stats()
    for key, value in stats_before.items():
        print(f"   {key}: {value}")
    
    # Executar processamento
    print("\nExecutando processamento...")
    results = processor.process_unprocessed_entries()
    
    print(f"Resultados:")
    print(f"   Processadas: {results['processed']}")
    print(f"   Erros: {results['errors']}")
    print(f"   IDs criados: {results['created_ids']}")
    
    # Mostrar estatísticas depois
    print("\nDEPOIS do processamento:")
    stats_after = processor.get_processing_stats()
    for key, value in stats_after.items():
        print(f"   {key}: {value}")
    
    # Verificar se atingiu 100% de cobertura
    if stats_after.get('coverage_percent', 0) == 100:
        print("\n[OK] 100% das raw entries tem structured correspondente!")
    else:
        print(f"\n[AVISO] Cobertura: {stats_after.get('coverage_percent', 0)}%")

if __name__ == "__main__":
    run_processor()