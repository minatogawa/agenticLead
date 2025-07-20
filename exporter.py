"""
Módulo de exportação para planilhas
E2-S3: Export planilha consolidada (Google Sheets / XLSX)
"""
import pandas as pd
from database import db, StructuredEntry, RawEntry
from datetime import datetime
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class DataExporter:
    """Classe responsável por exportar dados estruturados"""
    
    def __init__(self):
        self.db = db
    
    def get_structured_data(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Busca dados estruturados com informações da raw entry associada
        """
        try:
            query = self.db.session.query(StructuredEntry, RawEntry).join(
                RawEntry, StructuredEntry.raw_text_id == RawEntry.id
            )
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            
            data = []
            for structured, raw in results:
                row = {
                    # Identificadores
                    'id_registro': structured.id,
                    'raw_text_id': structured.raw_text_id,
                    
                    # Dados do contato
                    'data_contato': structured.data_contato,
                    'hora_contato': structured.hora_contato,
                    'nome': structured.nome,
                    'telefone': structured.telefone,
                    'bairro': structured.bairro,
                    'referencia_local': structured.referencia_local,
                    'tipo_demanda': structured.tipo_demanda,
                    'descricao_curta': structured.descricao_curta,
                    'prioridade_percebida': structured.prioridade_percebida,
                    'consentimento_comunicacao': structured.consentimento_comunicacao,
                    'fonte': structured.fonte,
                    
                    # Metadados de qualidade
                    'confianca_global': structured.confianca_global,
                    'flags': str(structured.flags) if structured.flags else '',
                    'revisado': structured.revisado,
                    
                    # Dados do processamento
                    'timestamp_processamento': structured.timestamp_processamento,
                    'timestamp_captura': raw.timestamp_captura,
                    'agente_id': raw.agente_id,
                    'texto_original': raw.texto_original,
                    
                    # Localização (se disponível)
                    'latitude': raw.latitude,
                    'longitude': raw.longitude
                }
                data.append(row)
            
            logger.info(f"Extraídos {len(data)} registros para exportação")
            return data
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados estruturados: {e}")
            raise
    
    def export_to_xlsx(self, filename: Optional[str] = None, limit: Optional[int] = None) -> str:
        """
        Exporta dados estruturados para arquivo XLSX
        Retorna o caminho do arquivo gerado
        """
        try:
            # Buscar dados
            data = self.get_structured_data(limit=limit)
            
            if not data:
                raise ValueError("Nenhum dado encontrado para exportação")
            
            # Criar DataFrame
            df = pd.DataFrame(data)
            
            # Definir nome do arquivo se não fornecido (nome fixo para substituir)
            if not filename:
                filename = "agenticlead_dados.xlsx"
            
            # Garantir extensão .xlsx
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            
            # Exportar para Excel
            df.to_excel(filename, index=False, engine='openpyxl')
            
            logger.info(f"Dados exportados para {filename} ({len(data)} registros)")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao exportar para XLSX: {e}")
            raise
    
    def export_to_csv(self, filename: Optional[str] = None, limit: Optional[int] = None) -> str:
        """
        Exporta dados estruturados para arquivo CSV
        Retorna o caminho do arquivo gerado
        """
        try:
            # Buscar dados
            data = self.get_structured_data(limit=limit)
            
            if not data:
                raise ValueError("Nenhum dado encontrado para exportação")
            
            # Criar DataFrame
            df = pd.DataFrame(data)
            
            # Definir nome do arquivo se não fornecido (nome fixo para substituir)
            if not filename:
                filename = "agenticlead_dados.csv"
            
            # Garantir extensão .csv
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            # Exportar para CSV
            df.to_csv(filename, index=False, encoding='utf-8')
            
            logger.info(f"Dados exportados para {filename} ({len(data)} registros)")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao exportar para CSV: {e}")
            raise
    
    def get_export_stats(self) -> Dict:
        """Retorna estatísticas dos dados disponíveis para export"""
        try:
            total_structured = self.db.session.query(StructuredEntry).count()
            revisados = self.db.session.query(StructuredEntry).filter(StructuredEntry.revisado == True).count()
            
            # Contar por tipo de demanda
            from sqlalchemy import func
            demandas = self.db.session.query(
                StructuredEntry.tipo_demanda,
                func.count(StructuredEntry.id).label('count')
            ).group_by(StructuredEntry.tipo_demanda).all()
            
            demandas_count = {d.tipo_demanda or 'NULL': d.count for d in demandas}
            
            return {
                'total_registros': total_structured,
                'revisados': revisados,
                'nao_revisados': total_structured - revisados,
                'por_tipo_demanda': demandas_count
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas de export: {e}")
            return {}

def main():
    """Função principal para teste do exportador"""
    print("AgenticLead - Exportador de Dados")
    print("=" * 40)
    
    exporter = DataExporter()
    
    # Mostrar estatísticas
    print("Estatísticas dos dados:")
    stats = exporter.get_export_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    if stats.get('total_registros', 0) == 0:
        print("\nNenhum dado encontrado para exportação!")
        return
    
    # Exportar para XLSX
    print("\nExportando para XLSX...")
    try:
        xlsx_file = exporter.export_to_xlsx()
        print(f"[OK] Arquivo criado: {xlsx_file}")
    except Exception as e:
        print(f"[ERRO] Falha no export XLSX: {e}")
    
    # Exportar para CSV
    print("\nExportando para CSV...")
    try:
        csv_file = exporter.export_to_csv()
        print(f"[OK] Arquivo criado: {csv_file}")
    except Exception as e:
        print(f"[ERRO] Falha no export CSV: {e}")

if __name__ == "__main__":
    main()