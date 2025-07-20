"""
API REST para AgenticLead
E2-S4: Endpoint GET /structured/{id}
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from database import db, StructuredEntry, RawEntry
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgenticLead API",
    description="API para sistema de captura e normalização de demandas públicas",
    version="1.0.0"
)

# Modelos Pydantic para resposta
class StructuredEntryResponse(BaseModel):
    id: int
    raw_text_id: int
    data_contato: Optional[str]
    hora_contato: Optional[str]
    nome: Optional[str]
    telefone: Optional[str]
    bairro: Optional[str]
    referencia_local: Optional[str]
    tipo_demanda: Optional[str]
    descricao_curta: Optional[str]
    prioridade_percebida: Optional[str]
    consentimento_comunicacao: Optional[bool]
    fonte: Optional[str]
    confianca_global: Optional[float]
    flags: Optional[List[str]]
    confianca_campos: Optional[Dict[str, Any]]
    timestamp_processamento: datetime
    revisado: bool
    
    class Config:
        from_attributes = True

class RawEntryInfo(BaseModel):
    id: int
    timestamp_captura: datetime
    agente_id: str
    texto_original: str
    latitude: Optional[float]
    longitude: Optional[float]
    processado: bool
    telegram_message_id: Optional[int]
    
    class Config:
        from_attributes = True

class StructuredEntryDetailResponse(StructuredEntryResponse):
    raw_entry: RawEntryInfo

@app.get("/")
async def root():
    """Endpoint raiz da API"""
    return {
        "message": "AgenticLead API",
        "version": "1.0.0",
        "endpoints": {
            "/structured/{id}": "Buscar entrada estruturada por ID",
            "/structured": "Listar entradas estruturadas",
            "/stats": "Estatísticas do sistema"
        }
    }

@app.get("/structured/{entry_id}", response_model=StructuredEntryDetailResponse)
async def get_structured_entry(entry_id: int):
    """
    E2-S4: Endpoint GET /structured/{id}
    Retorna JSON por id_registro com dados da raw_entry associada
    """
    try:
        # Buscar entrada estruturada com raw_entry associada
        query_result = db.session.query(StructuredEntry, RawEntry).join(
            RawEntry, StructuredEntry.raw_text_id == RawEntry.id
        ).filter(StructuredEntry.id == entry_id).first()
        
        if not query_result:
            raise HTTPException(
                status_code=404, 
                detail=f"Entrada estruturada com ID {entry_id} não encontrada"
            )
        
        structured_entry, raw_entry = query_result
        
        # Converter flags de JSON para lista se necessário
        flags = structured_entry.flags if structured_entry.flags else []
        if isinstance(flags, str):
            import json
            try:
                flags = json.loads(flags)
            except:
                flags = []
        
        # Montar resposta
        response_data = {
            "id": structured_entry.id,
            "raw_text_id": structured_entry.raw_text_id,
            "data_contato": structured_entry.data_contato,
            "hora_contato": structured_entry.hora_contato,
            "nome": structured_entry.nome,
            "telefone": structured_entry.telefone,
            "bairro": structured_entry.bairro,
            "referencia_local": structured_entry.referencia_local,
            "tipo_demanda": structured_entry.tipo_demanda,
            "descricao_curta": structured_entry.descricao_curta,
            "prioridade_percebida": structured_entry.prioridade_percebida,
            "consentimento_comunicacao": structured_entry.consentimento_comunicacao,
            "fonte": structured_entry.fonte,
            "confianca_global": structured_entry.confianca_global,
            "flags": flags,
            "confianca_campos": structured_entry.confianca_campos or {},
            "timestamp_processamento": structured_entry.timestamp_processamento,
            "revisado": structured_entry.revisado,
            "raw_entry": {
                "id": raw_entry.id,
                "timestamp_captura": raw_entry.timestamp_captura,
                "agente_id": raw_entry.agente_id,
                "texto_original": raw_entry.texto_original,
                "latitude": raw_entry.latitude,
                "longitude": raw_entry.longitude,
                "processado": raw_entry.processado,
                "telegram_message_id": raw_entry.telegram_message_id
            }
        }
        
        logger.info(f"Entrada estruturada {entry_id} consultada via API")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar entrada estruturada {entry_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.get("/structured", response_model=List[StructuredEntryResponse])
async def list_structured_entries(
    limit: int = 100,
    offset: int = 0,
    revisado: Optional[bool] = None
):
    """Lista entradas estruturadas com paginação e filtros"""
    try:
        query = db.session.query(StructuredEntry)
        
        if revisado is not None:
            query = query.filter(StructuredEntry.revisado == revisado)
        
        entries = query.offset(offset).limit(limit).all()
        
        result = []
        for entry in entries:
            flags = entry.flags if entry.flags else []
            if isinstance(flags, str):
                import json
                try:
                    flags = json.loads(flags)
                except:
                    flags = []
            
            result.append({
                "id": entry.id,
                "raw_text_id": entry.raw_text_id,
                "data_contato": entry.data_contato,
                "hora_contato": entry.hora_contato,
                "nome": entry.nome,
                "telefone": entry.telefone,
                "bairro": entry.bairro,
                "referencia_local": entry.referencia_local,
                "tipo_demanda": entry.tipo_demanda,
                "descricao_curta": entry.descricao_curta,
                "prioridade_percebida": entry.prioridade_percebida,
                "consentimento_comunicacao": entry.consentimento_comunicacao,
                "fonte": entry.fonte,
                "confianca_global": entry.confianca_global,
                "flags": flags,
                "confianca_campos": entry.confianca_campos or {},
                "timestamp_processamento": entry.timestamp_processamento,
                "revisado": entry.revisado
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao listar entradas estruturadas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.get("/stats")
async def get_stats():
    """Retorna estatísticas do sistema"""
    try:
        total_raw = db.session.query(RawEntry).count()
        total_structured = db.session.query(StructuredEntry).count()
        unprocessed = db.session.query(RawEntry).filter(RawEntry.processado == False).count()
        revisados = db.session.query(StructuredEntry).filter(StructuredEntry.revisado == True).count()
        
        return {
            "total_raw_entries": total_raw,
            "total_structured_entries": total_structured,
            "unprocessed_entries": unprocessed,
            "reviewed_entries": revisados,
            "coverage_percent": round((total_structured / total_raw * 100) if total_raw > 0 else 0, 2)
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)