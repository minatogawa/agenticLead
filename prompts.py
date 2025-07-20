"""
Prompts para extração LLM - Versão 1.0
E3-S1: Definir prompt v1 (single) com instruções & few-shots
"""
from datetime import datetime
from typing import Dict, Any

# Versão do prompt para controle
PROMPT_VERSION = "v1.0"

# Prompt do sistema
SYSTEM_PROMPT = """Você é um extrator de dados especializado em demandas públicas. 

Recebe texto livre descrevendo contatos entre agentes públicos e cidadãos. 
Extraia os campos solicitados e responda EXCLUSIVAMENTE com JSON válido UTF-8, sem comentários ou explicações.

IMPORTANTE: Se um campo não tiver evidência explícita no texto, use null."""

def build_extraction_prompt(raw_text: str, capture_timestamp: str = None) -> str:
    """
    Constrói o prompt de extração com o texto bruto
    """
    if not capture_timestamp:
        capture_timestamp = datetime.utcnow().isoformat()
    
    return f"""Texto bruto:
\"\"\"
{raw_text}
\"\"\"

REGRAS DE EXTRAÇÃO:
1. Se não houver evidência explícita de um campo, use null
2. Data/hora: Se mencionada ("hoje", "agora", "ontem") use referência {capture_timestamp}
3. tipo_demanda: ARVORE, BUEIRO, GRAMA, ILUMINACAO, LIMPEZA, SEGURANCA, OUTRO
4. Telefone: extrair dígitos; se brasileiro sem DDI, prefixar +55
5. consentimento_comunicacao: true SOMENTE se texto indicar ("quer receber", "pode avisar")
6. prioridade_percebida: "ALTA" se urgência/risco, "MEDIA" se moderado, "BAIXA" caso contrário
7. descricao_curta: resumo objetivo máximo 120 caracteres

FORMATO DE SAÍDA JSON:
{{
  "data_contato": "YYYY-MM-DD",
  "hora_contato": "HH:MM", 
  "nome": "...",
  "telefone": "...",
  "bairro": "...",
  "referencia_local": "...",
  "tipo_demanda": "...",
  "descricao_curta": "...",
  "prioridade_percebida": "...",
  "consentimento_comunicacao": true/false,
  "confianca_campos": {{
     "nome": 0.95,
     "telefone": 0.90,
     "bairro": 0.85,
     "tipo_demanda": 0.98
  }}
}}"""

# Few-shot examples para melhorar a performance
FEW_SHOT_EXAMPLES = [
    {
        "input": "Falei hoje 18/07 tarde com o Sr João na esquina da Rua A com B no bairro Centro, bueiro entupido saindo água, deu telefone 11988887777 e pediu pra avisar quando resolver.",
        "output": {
            "data_contato": "2025-07-18",
            "hora_contato": "15:30",
            "nome": "João",
            "telefone": "+5511988887777", 
            "bairro": "Centro",
            "referencia_local": "Esquina Rua A com Rua B",
            "tipo_demanda": "BUEIRO",
            "descricao_curta": "Bueiro entupido escoando água na esquina Rua A x Rua B",
            "prioridade_percebida": "ALTA",
            "consentimento_comunicacao": True,
            "confianca_campos": {
                "nome": 0.9,
                "telefone": 0.95,
                "bairro": 0.85,
                "tipo_demanda": 0.98
            }
        }
    },
    {
        "input": "Ontem à noite falei com Paulo perto do campo do bairro Jardim Azul, poste de luz apagado, não deixou telefone, só disse que mora ali perto.",
        "output": {
            "data_contato": "2025-07-17",
            "hora_contato": "20:00",
            "nome": "Paulo",
            "telefone": None,
            "bairro": "Jardim Azul", 
            "referencia_local": "Campo do bairro Jardim Azul",
            "tipo_demanda": "ILUMINACAO",
            "descricao_curta": "Poste de luz apagado no campo do Jardim Azul",
            "prioridade_percebida": "MEDIA",
            "consentimento_comunicacao": False,
            "confianca_campos": {
                "nome": 0.8,
                "telefone": 0.0,
                "bairro": 0.9,
                "tipo_demanda": 0.95
            }
        }
    },
    {
        "input": "Dona Maria ligou reclamando da grama alta na praça, disse que é urgente pois tem crianças brincando, mora na Rua das Flores 123, telefone 21 99888-6677.",
        "output": {
            "data_contato": None,
            "hora_contato": None,
            "nome": "Maria",
            "telefone": "+5521998886677",
            "bairro": None,
            "referencia_local": "Praça próxima à Rua das Flores 123", 
            "tipo_demanda": "GRAMA",
            "descricao_curta": "Grama alta na praça com risco para crianças",
            "prioridade_percebida": "ALTA",
            "consentimento_comunicacao": False,
            "confianca_campos": {
                "nome": 0.85,
                "telefone": 0.95,
                "bairro": 0.0,
                "tipo_demanda": 0.98
            }
        }
    }
]

def build_few_shot_prompt(raw_text: str, capture_timestamp: str = None) -> str:
    """
    Constrói prompt com few-shot examples
    """
    if not capture_timestamp:
        capture_timestamp = datetime.utcnow().isoformat()
    
    # Construir examples
    examples_text = ""
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_text += f"\nEXEMPLO {i}:\n"
        examples_text += f"Entrada: \"{example['input']}\"\n"
        examples_text += f"Saída: {example['output']}\n"
    
    return f"""Você deve extrair dados estruturados de relatos de demandas públicas.

{examples_text}

AGORA EXTRAIA DOS DADOS ABAIXO:

Texto bruto:
\"\"\"
{raw_text}
\"\"\"

Referência temporal: {capture_timestamp}

Responda APENAS com JSON válido seguindo o mesmo formato dos exemplos:"""

# Prompt para correção de JSON inválido
REFORMAT_PROMPT = """O JSON anterior está inválido. Corrija e retorne SOMENTE o JSON válido, sem explicações:

Texto original: {raw_text}

Resposta anterior com erro: {invalid_json}

JSON corrigido:"""

def get_prompt_metadata() -> Dict[str, Any]:
    """Retorna metadados da versão do prompt"""
    return {
        "version": PROMPT_VERSION,
        "created_at": "2025-07-18",
        "description": "Prompt v1 para extração de demandas públicas",
        "few_shot_examples": len(FEW_SHOT_EXAMPLES),
        "supported_types": ["ARVORE", "BUEIRO", "GRAMA", "ILUMINACAO", "LIMPEZA", "SEGURANCA", "OUTRO"],
        "supported_priorities": ["ALTA", "MEDIA", "BAIXA"]
    }

# Validação de campos extraídos
REQUIRED_FIELDS = [
    "data_contato", "hora_contato", "nome", "telefone", "bairro",
    "referencia_local", "tipo_demanda", "descricao_curta", 
    "prioridade_percebida", "consentimento_comunicacao", "confianca_campos"
]

VALID_TIPOS_DEMANDA = ["ARVORE", "BUEIRO", "GRAMA", "ILUMINACAO", "LIMPEZA", "SEGURANCA", "OUTRO"]
VALID_PRIORIDADES = ["ALTA", "MEDIA", "BAIXA"]

def validate_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida dados extraídos e retorna informações sobre qualidade
    """
    issues = []
    
    # Verificar campos obrigatórios
    for field in REQUIRED_FIELDS:
        if field not in data:
            issues.append(f"Campo '{field}' ausente")
    
    # Validar tipo_demanda
    if data.get("tipo_demanda") and data["tipo_demanda"] not in VALID_TIPOS_DEMANDA:
        issues.append(f"tipo_demanda inválido: {data['tipo_demanda']}")
    
    # Validar prioridade
    if data.get("prioridade_percebida") and data["prioridade_percebida"] not in VALID_PRIORIDADES:
        issues.append(f"prioridade_percebida inválida: {data['prioridade_percebida']}")
    
    # Calcular confiança global
    confianca_campos = data.get("confianca_campos", {})
    if confianca_campos:
        confianca_global = sum(confianca_campos.values()) / len(confianca_campos)
    else:
        confianca_global = 0.5  # Default médio
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confianca_global": round(confianca_global, 3),
        "campos_preenchidos": len([v for v in data.values() if v is not None]),
        "total_campos": len(REQUIRED_FIELDS)
    }