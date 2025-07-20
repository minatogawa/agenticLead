"""
Processador LLM integrado - Worker assíncrono
E3-S4: Worker assíncrono (fila) + E3-S5: Status de processamento
"""
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
from database import db, RawEntry, StructuredEntry
from llm_extractor import LLMExtractor
from sqlalchemy import Column, String, Text, DateTime, update

logger = logging.getLogger(__name__)

class LLMProcessor:
    """Processador que integra LLM com banco de dados"""
    
    def __init__(self):
        self.db = db
        self.extractor = LLMExtractor()
        
        # Adicionar campos de status se não existirem
        self._ensure_status_fields()
    
    def _ensure_status_fields(self):
        """
        E3-S5: Garante que os campos de status existem na tabela
        """
        try:
            # Verificar se colunas existem e criar se necessário
            from sqlalchemy import text
            
            # Adicionar campos de controle de extração
            try:
                self.db.session.execute(text("""
                    ALTER TABLE structured_entries 
                    ADD COLUMN extraction_status VARCHAR(20) DEFAULT 'pending'
                """))
                self.db.session.commit()
                logger.info("Campo extraction_status adicionado")
            except:
                pass  # Campo já existe
            
            try:
                self.db.session.execute(text("""
                    ALTER TABLE structured_entries 
                    ADD COLUMN error_msg TEXT
                """))
                self.db.session.commit()
                logger.info("Campo error_msg adicionado")
            except:
                pass  # Campo já existe
            
            try:
                self.db.session.execute(text("""
                    ALTER TABLE structured_entries 
                    ADD COLUMN llm_metadata TEXT
                """))
                self.db.session.commit()
                logger.info("Campo llm_metadata adicionado")
            except:
                pass  # Campo já existe
                
        except Exception as e:
            logger.warning(f"Erro ao verificar campos de status: {e}")
    
    def process_single_entry(self, raw_entry: RawEntry) -> Dict[str, Any]:
        """
        Processa uma única entrada raw com LLM
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processando raw_entry {raw_entry.id} com LLM...")
            
            # Extrair dados com LLM
            extracted_data, metadata = self.extractor.extract_from_text(
                raw_entry.texto_original,
                capture_timestamp=raw_entry.timestamp_captura.isoformat()
            )
            
            # Buscar structured_entry existente
            structured_entry = self.db.session.query(StructuredEntry).filter(
                StructuredEntry.raw_text_id == raw_entry.id
            ).first()
            
            if not structured_entry:
                logger.error(f"Structured entry não encontrada para raw_id {raw_entry.id}")
                return {"success": False, "error": "Structured entry não encontrada"}
            
            # Atualizar campos extraídos
            structured_entry.data_contato = extracted_data.get("data_contato")
            structured_entry.hora_contato = extracted_data.get("hora_contato")
            structured_entry.nome = extracted_data.get("nome")
            structured_entry.telefone = extracted_data.get("telefone")
            structured_entry.bairro = extracted_data.get("bairro")
            structured_entry.referencia_local = extracted_data.get("referencia_local")
            structured_entry.tipo_demanda = extracted_data.get("tipo_demanda")
            structured_entry.descricao_curta = extracted_data.get("descricao_curta")
            structured_entry.prioridade_percebida = extracted_data.get("prioridade_percebida")
            structured_entry.consentimento_comunicacao = extracted_data.get("consentimento_comunicacao")
            structured_entry.confianca_global = metadata.get("validation", {}).get("confianca_global", 0)
            structured_entry.confianca_campos = extracted_data.get("confianca_campos", {})
            
            # E3-S5: Campos de status
            extraction_status = metadata.get("extraction_status", "unknown")
            if extraction_status == "success":
                if metadata.get("validation", {}).get("valid", False):
                    structured_entry.extraction_status = "completed"
                else:
                    structured_entry.extraction_status = "validation_failed"
            else:
                structured_entry.extraction_status = "error"
            
            structured_entry.error_msg = metadata.get("error_message")
            structured_entry.llm_metadata = str(metadata)
            
            # Salvar no banco
            self.db.session.commit()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": True,
                "raw_id": raw_entry.id,
                "structured_id": structured_entry.id,
                "extraction_status": structured_entry.extraction_status,
                "processing_time": processing_time,
                "confidence": structured_entry.confianca_global
            }
            
            logger.info(f"Raw {raw_entry.id} processada em {processing_time:.2f}s - Status: {structured_entry.extraction_status}")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar raw_entry {raw_entry.id}: {e}")
            
            # Marcar como erro no banco se possível
            try:
                structured_entry = self.db.session.query(StructuredEntry).filter(
                    StructuredEntry.raw_text_id == raw_entry.id
                ).first()
                
                if structured_entry:
                    structured_entry.extraction_status = "error"
                    structured_entry.error_msg = str(e)
                    self.db.session.commit()
            except:
                pass
            
            return {
                "success": False,
                "raw_id": raw_entry.id,
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def process_batch_async(self, batch_size: int = 5, max_concurrent: int = 3) -> Dict[str, Any]:
        """
        E3-S4: Worker assíncrono para processar lote
        Processa entradas em lotes com controle de concorrência
        """
        start_time = datetime.now()
        
        # Buscar entradas que precisam de processamento LLM
        # (structured entries com status pending ou que são placeholders vazios)
        pending_entries = self.db.session.query(StructuredEntry, RawEntry).join(
            RawEntry, StructuredEntry.raw_text_id == RawEntry.id
        ).filter(
            (StructuredEntry.extraction_status.is_(None)) |
            (StructuredEntry.extraction_status == 'pending') |
            ((StructuredEntry.nome.is_(None)) & (StructuredEntry.telefone.is_(None)))
        ).limit(batch_size).all()
        
        if not pending_entries:
            return {
                "success": True,
                "message": "Nenhuma entrada pendente para processamento",
                "processed": 0,
                "errors": 0,
                "total_time": 0
            }
        
        logger.info(f"Processando {len(pending_entries)} entradas com LLM...")
        
        results = {
            "processed": 0,
            "errors": 0,
            "details": [],
            "avg_time_per_entry": 0,
            "total_time": 0
        }
        
        # Processar em batches para controlar concorrência
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(structured_entry, raw_entry):
            async with semaphore:
                # Executar em thread separada pois OpenAI API é síncrona
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.process_single_entry, raw_entry)
        
        # Processar todas as entradas de forma assíncrona
        tasks = []
        for structured_entry, raw_entry in pending_entries:
            task = process_with_semaphore(structured_entry, raw_entry)
            tasks.append(task)
        
        # Aguardar conclusão de todas as tarefas
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compilar resultados
        for result in task_results:
            if isinstance(result, Exception):
                results["errors"] += 1
                results["details"].append({"error": str(result)})
            elif result["success"]:
                results["processed"] += 1
                results["details"].append(result)
            else:
                results["errors"] += 1
                results["details"].append(result)
        
        # Calcular estatísticas
        total_time = (datetime.now() - start_time).total_seconds()
        results["total_time"] = total_time
        
        if results["processed"] > 0:
            avg_time = sum(d.get("processing_time", 0) for d in results["details"] if "processing_time" in d)
            results["avg_time_per_entry"] = round(avg_time / results["processed"], 2)
        
        logger.info(f"Batch concluído: {results['processed']} processadas, {results['errors']} erros em {total_time:.2f}s")
        
        return results
    
    def get_processing_dashboard(self) -> Dict[str, Any]:
        """
        E3-S5: Painel mostra contagem por status
        """
        try:
            # Contar por status de extração
            from sqlalchemy import func, text
            
            status_counts = {}
            try:
                # Tentar query com novo campo
                status_query = self.db.session.query(
                    StructuredEntry.extraction_status,
                    func.count(StructuredEntry.id).label('count')
                ).group_by(StructuredEntry.extraction_status).all()
                
                for status, count in status_query:
                    status_counts[status or 'pending'] = count
                    
            except:
                # Fallback se campo não existe
                total = self.db.session.query(StructuredEntry).count()
                filled = self.db.session.query(StructuredEntry).filter(
                    (StructuredEntry.nome.isnot(None)) | 
                    (StructuredEntry.telefone.isnot(None))
                ).count()
                
                status_counts = {
                    'pending': total - filled,
                    'completed': filled
                }
            
            # Estatísticas gerais
            total_raw = self.db.session.query(RawEntry).count()
            total_structured = self.db.session.query(StructuredEntry).count()
            
            # Confiança média das processadas
            try:
                avg_confidence = self.db.session.query(
                    func.avg(StructuredEntry.confianca_global)
                ).filter(StructuredEntry.confianca_global.isnot(None)).scalar() or 0
            except:
                avg_confidence = 0
            
            return {
                "status_counts": status_counts,
                "total_raw_entries": total_raw,
                "total_structured_entries": total_structured,
                "average_confidence": round(avg_confidence, 3),
                "processing_coverage": round((total_structured / total_raw * 100) if total_raw > 0 else 0, 1)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar dashboard: {e}")
            return {"error": str(e)}

def run_llm_processor():
    """Função principal para executar processamento LLM"""
    print("AgenticLead - Processador LLM")
    print("=" * 35)
    
    processor = LLMProcessor()
    
    # Mostrar dashboard antes
    print("DASHBOARD ANTES:")
    dashboard = processor.get_processing_dashboard()
    for key, value in dashboard.items():
        print(f"   {key}: {value}")
    
    # Verificar se há algo para processar
    pending_count = dashboard.get("status_counts", {}).get("pending", 0)
    if pending_count == 0:
        print("\nNenhuma entrada pendente para processamento LLM.")
        return
    
    print(f"\nProcessando {min(pending_count, 5)} entradas...")
    
    # Executar processamento assíncrono
    async def run_async():
        return await processor.process_batch_async(batch_size=5, max_concurrent=2)
    
    results = asyncio.run(run_async())
    
    # Mostrar resultados
    print("\nRESULTADOS:")
    print(f"   Processadas: {results['processed']}")
    print(f"   Erros: {results['errors']}")
    print(f"   Tempo total: {results['total_time']:.2f}s")
    
    if results['processed'] > 0:
        print(f"   Tempo médio por entrada: {results['avg_time_per_entry']:.2f}s")
    
    # Dashboard depois
    print("\nDASHBOARD DEPOIS:")
    dashboard_after = processor.get_processing_dashboard()
    for key, value in dashboard_after.items():
        print(f"   {key}: {value}")

if __name__ == "__main__":
    run_llm_processor()