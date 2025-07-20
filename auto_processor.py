"""
Processador automático: Raw → Structured → LLM → Export
Executa todo o pipeline automaticamente quando chamado
"""
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
from database import db
from processor import DataProcessor
from llm_processor import LLMProcessor
from exporter import DataExporter

logger = logging.getLogger(__name__)

class AutoProcessor:
    """Processador automático completo"""
    
    def __init__(self):
        self.basic_processor = DataProcessor()
        self.llm_processor = LLMProcessor()
        self.exporter = DataExporter()
    
    async def process_new_entries(self) -> Dict[str, Any]:
        """
        Pipeline completo:
        1. Cria placeholders para raw entries não processadas
        2. Processa com LLM
        3. Exporta para Excel/CSV (substitui arquivos)
        """
        start_time = datetime.now()
        results = {
            "success": True,
            "steps": {
                "placeholders": {"processed": 0, "errors": 0},
                "llm_extraction": {"processed": 0, "errors": 0},
                "export": {"xlsx": False, "csv": False}
            },
            "total_time": 0,
            "message": ""
        }
        
        try:
            # Passo 1: Criar placeholders para novas raw entries
            logger.info("Iniciando processamento automático...")
            
            placeholder_results = self.basic_processor.process_unprocessed_entries()
            results["steps"]["placeholders"] = {
                "processed": placeholder_results["processed"],
                "errors": placeholder_results["errors"]
            }
            
            if placeholder_results["processed"] > 0:
                logger.info(f"Criados {placeholder_results['processed']} placeholders")
            
            # Passo 2: Processar com LLM (apenas se há novas entradas OU pendentes)
            llm_results = await self.llm_processor.process_batch_async(
                batch_size=10, 
                max_concurrent=3
            )
            
            results["steps"]["llm_extraction"] = {
                "processed": llm_results["processed"],
                "errors": llm_results["errors"]
            }
            
            if llm_results["processed"] > 0:
                logger.info(f"LLM processou {llm_results['processed']} entradas")
            
            # Passo 3: Exportar sempre (substitui arquivos anteriores)
            try:
                xlsx_file = self.exporter.export_to_xlsx()  # Nome fixo
                results["steps"]["export"]["xlsx"] = True
                logger.info(f"Excel exportado: {xlsx_file}")
            except Exception as e:
                logger.error(f"Erro no export XLSX: {e}")
            
            try:
                csv_file = self.exporter.export_to_csv()  # Nome fixo
                results["steps"]["export"]["csv"] = True
                logger.info(f"CSV exportado: {csv_file}")
            except Exception as e:
                logger.error(f"Erro no export CSV: {e}")
            
            # Calcular tempo total
            total_time = (datetime.now() - start_time).total_seconds()
            results["total_time"] = round(total_time, 2)
            
            # Mensagem de resumo
            if placeholder_results["processed"] > 0 or llm_results["processed"] > 0:
                results["message"] = f"Processadas {placeholder_results['processed']} novas + {llm_results['processed']} com LLM em {total_time:.2f}s"
            else:
                results["message"] = f"Nenhuma entrada nova. Arquivos atualizados em {total_time:.2f}s"
            
            logger.info(f"Processamento automático concluído: {results['message']}")
            return results
            
        except Exception as e:
            logger.error(f"Erro no processamento automático: {e}")
            results["success"] = False
            results["message"] = f"Erro: {str(e)}"
            results["total_time"] = (datetime.now() - start_time).total_seconds()
            return results
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas resumidas do sistema"""
        try:
            # Stats básicas
            dashboard = self.llm_processor.get_processing_dashboard()
            
            # Stats do exporter
            export_stats = self.exporter.get_export_stats()
            
            return {
                "entries": {
                    "total_raw": dashboard.get("total_raw_entries", 0),
                    "total_structured": dashboard.get("total_structured_entries", 0),
                    "coverage": dashboard.get("processing_coverage", 0)
                },
                "processing": {
                    "status_counts": dashboard.get("status_counts", {}),
                    "avg_confidence": dashboard.get("average_confidence", 0)
                },
                "export": {
                    "total_registros": export_stats.get("total_registros", 0),
                    "por_tipo_demanda": export_stats.get("por_tipo_demanda", {})
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return {"error": str(e)}

async def run_auto_processor():
    """Função principal para executar processamento automático"""
    print("AgenticLead - Processador Automatico")
    print("=" * 40)
    
    processor = AutoProcessor()
    
    # Mostrar stats antes
    print("ANTES do processamento:")
    stats_before = processor.get_summary_stats()
    if "error" not in stats_before:
        print(f"   Raw entries: {stats_before['entries']['total_raw']}")
        print(f"   Structured entries: {stats_before['entries']['total_structured']}")
        print(f"   Coverage: {stats_before['entries']['coverage']}%")
        
        status_counts = stats_before['processing']['status_counts']
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
    
    # Executar processamento
    print("\nExecutando pipeline automatico...")
    results = await processor.process_new_entries()
    
    # Mostrar resultados
    print(f"\nResultados: {results['message']}")
    print(f"Tempo total: {results['total_time']}s")
    
    steps = results['steps']
    print(f"  Placeholders: {steps['placeholders']['processed']} criados")
    print(f"  LLM: {steps['llm_extraction']['processed']} processadas")
    print(f"  Export XLSX: {'OK' if steps['export']['xlsx'] else 'ERRO'}")
    print(f"  Export CSV: {'OK' if steps['export']['csv'] else 'ERRO'}")
    
    # Stats depois
    print("\nDEPOIS do processamento:")
    stats_after = processor.get_summary_stats()
    if "error" not in stats_after:
        print(f"   Raw entries: {stats_after['entries']['total_raw']}")
        print(f"   Structured entries: {stats_after['entries']['total_structured']}")
        print(f"   Coverage: {stats_after['entries']['coverage']}%")
        
        tipos = stats_after['export']['por_tipo_demanda']
        if tipos:
            print("   Tipos de demanda:")
            for tipo, count in tipos.items():
                print(f"     {tipo}: {count}")

def main():
    """Execução síncrona para linha de comando"""
    asyncio.run(run_auto_processor())

if __name__ == "__main__":
    main()