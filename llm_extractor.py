"""
Extrator LLM usando OpenAI API
E3-S2: Implementar chamada LLM simples extract_from_text(raw_text)
"""
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY
from prompts import (
    SYSTEM_PROMPT, 
    build_extraction_prompt, 
    build_few_shot_prompt,
    REFORMAT_PROMPT,
    validate_extracted_data,
    get_prompt_metadata
)

logger = logging.getLogger(__name__)

class LLMExtractor:
    """Classe para extração de dados usando LLM"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        """
        Inicializa o extrator LLM
        
        Args:
            api_key: Chave da API OpenAI (usa config se None)
            model: Modelo a usar (default: gpt-3.5-turbo)
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model
        self.client = None
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não configurada. Adicione no arquivo .env")
        
        # Configurar cliente OpenAI
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"LLMExtractor inicializado com modelo {model}")
    
    def _call_openai(self, messages: list, temperature: float = 0) -> str:
        """
        Chama a API OpenAI e retorna o conteúdo da resposta
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=1000,
                timeout=30
            )
            
            content = response.choices[0].message.content.strip()
            
            # Log da resposta (sem dados sensíveis)
            logger.debug(f"OpenAI response length: {len(content)} chars")
            
            return content
            
        except Exception as e:
            logger.error(f"Erro na chamada OpenAI: {e}")
            raise
    
    def extract_from_text(self, raw_text: str, use_few_shot: bool = True, 
                         capture_timestamp: str = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        E3-S2: Função principal de extração
        
        Args:
            raw_text: Texto bruto para extrair dados
            use_few_shot: Se deve usar few-shot examples
            capture_timestamp: Timestamp de captura (opcional)
        
        Returns:
            Tuple[extracted_data, metadata]
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Texto vazio não pode ser processado")
        
        start_time = datetime.now()
        
        try:
            # Construir prompt
            if use_few_shot:
                user_prompt = build_few_shot_prompt(raw_text, capture_timestamp)
            else:
                user_prompt = build_extraction_prompt(raw_text, capture_timestamp)
            
            # Preparar mensagens
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
            
            # Chamar OpenAI
            logger.info(f"Extraindo dados de texto ({len(raw_text)} chars)")
            response_text = self._call_openai(messages)
            
            # Tentar parsear JSON
            try:
                extracted_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON inválido na primeira tentativa: {e}")
                # Tentar uma segunda vez com prompt de correção
                extracted_data = self._retry_with_reformat(raw_text, response_text)
            
            # Validar dados extraídos
            validation = validate_extracted_data(extracted_data)
            
            # Calcular tempo de processamento
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Montar metadata
            metadata = {
                "extraction_status": "success" if validation["valid"] else "validation_failed",
                "processing_time_seconds": round(processing_time, 2),
                "model_used": self.model,
                "prompt_version": get_prompt_metadata()["version"],
                "use_few_shot": use_few_shot,
                "validation": validation,
                "raw_text_length": len(raw_text),
                "response_length": len(response_text),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Extração concluída em {processing_time:.2f}s - Status: {metadata['extraction_status']}")
            
            return extracted_data, metadata
            
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
            
            # Metadata de erro
            error_metadata = {
                "extraction_status": "error",
                "error_message": str(e),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                "model_used": self.model,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return {}, error_metadata
    
    def _retry_with_reformat(self, raw_text: str, invalid_json: str) -> Dict[str, Any]:
        """
        E3-S3: Tenta corrigir JSON inválido com prompt de reformatação
        """
        logger.info("Tentando corrigir JSON inválido...")
        
        reformat_prompt = REFORMAT_PROMPT.format(
            raw_text=raw_text,
            invalid_json=invalid_json
        )
        
        messages = [
            {"role": "system", "content": "Você corrige JSON inválido. Responda APENAS com JSON válido."},
            {"role": "user", "content": reformat_prompt}
        ]
        
        try:
            response_text = self._call_openai(messages)
            extracted_data = json.loads(response_text)
            logger.info("JSON corrigido com sucesso na segunda tentativa")
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Falha ao corrigir JSON: {e}")
            # Retornar estrutura vazia mas válida
            return {
                "data_contato": None,
                "hora_contato": None,
                "nome": None,
                "telefone": None,
                "bairro": None,
                "referencia_local": None,
                "tipo_demanda": None,
                "descricao_curta": None,
                "prioridade_percebida": None,
                "consentimento_comunicacao": None,
                "confianca_campos": {}
            }
    
    def test_extraction(self, test_text: str = None) -> Dict[str, Any]:
        """
        Testa a extração com texto de exemplo
        """
        if not test_text:
            test_text = "Hoje 18/07 falei com Maria Silva na Praça Central, bueiro entupido na esquina da Rua A com Rua B, telefone 11 99999-8888, urgente porque tem água suja."
        
        print("Testando extração LLM...")
        print(f"Texto de entrada: {test_text}")
        print("=" * 50)
        
        try:
            extracted_data, metadata = self.extract_from_text(test_text)
            
            print("DADOS EXTRAÍDOS:")
            for key, value in extracted_data.items():
                print(f"  {key}: {value}")
            
            print("\nMETADATA:")
            for key, value in metadata.items():
                if key != "validation":
                    print(f"  {key}: {value}")
            
            print(f"\nVALIDACOES:")
            validation = metadata.get("validation", {})
            print(f"  Valido: {validation.get('valid', False)}")
            print(f"  Confianca global: {validation.get('confianca_global', 0)}")
            print(f"  Campos preenchidos: {validation.get('campos_preenchidos', 0)}/{validation.get('total_campos', 0)}")
            
            if validation.get("issues"):
                print(f"  Problemas: {validation['issues']}")
            
            return {
                "success": metadata["extraction_status"] == "success",
                "data": extracted_data,
                "metadata": metadata
            }
            
        except Exception as e:
            print(f"ERRO no teste: {e}")
            return {"success": False, "error": str(e)}

def main():
    """Função para teste direto do extrator"""
    try:
        # Verificar se API key está configurada
        if not OPENAI_API_KEY:
            print("ERRO: OPENAI_API_KEY não configurada!")
            print("Adicione sua chave no arquivo .env:")
            print("OPENAI_API_KEY=sk-...")
            return
        
        # Criar extrator e testar
        extractor = LLMExtractor()
        result = extractor.test_extraction()
        
        if result["success"]:
            print("\n[OK] Teste concluido com sucesso!")
        else:
            print(f"\n[ERRO] Teste falhou: {result.get('error', 'Erro desconhecido')}")
        
    except Exception as e:
        print(f"[ERRO] Erro no teste: {e}")

if __name__ == "__main__":
    main()