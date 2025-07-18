# Sistema de Captura e Normalização de Demandas Públicas

## 1. Visão Geral do Fluxo

### Captura Livre (Campo)
O agente fala ou digita texto corrido (ou áudio transcrito):

"18/07 fim da tarde falei com Maria (acho que Silva) perto da Praça Central, bueiro transbordando na esquina da Rua das Flores com Av. Brasil, deu telefone 11 98765‑4321, quer atualização, prioridade alta porque água suja."

### Pipeline de Processamento:
1. **Ingestão** (armazenar raw + metadados mínimos: timestamp, autor, latitude opcional)
2. **Pipeline de Normalização** acionado (batch ou near‑real‑time):
   - (a) Limpeza (remover ruído, OCR/transcrição se áudio)
   - (b) Chamada LLM para extrair slots conforme esquema alvo
   - (c) Validações / heurísticas / correções (regex telefone, normalização de categorias)
   - (d) Scoring de confiança + marcação de campos incertos
3. **Registro Estruturado** escrito em planilha / DB
4. **Fila de Revisão Opcional**: entradas com baixa confiança aguardam revisão manual (UI simples)
5. **Feedback Loop**: correções humanas armazenadas → dataset de fine‑tuning / few-shot melhorado

## 2. Esquema Alvo (Exemplo)

Campos (podem vir parcialmente preenchidos):

| Campo | Tipo | Observações |
|-------|------|-------------|
| data_contato | date | Inferir de texto ou usar timestamp de captura |
| hora_contato | time | Opcional (fallback = timestamp) |
| nome | text | Nome completo ou parcial |
| telefone | text | Normalizar p/ formato internacional |
| bairro | text | Resolver via lookup geográfico se logradouro encontrado |
| referencia_local | text | "Praça Central", cruzamento etc. |
| tipo_demanda | enum | ARVORE, BUEIRO, GRAMA, ILUMINACAO, LIMPEZA, SEGURANCA, OUTRO |
| descricao_curta | text | Resumo sintetizado (<=120 chars) |
| prioridade_percebida | enum | ALTA / MEDIA / BAIXA |
| consentimento_comunicacao | bool | Inferir só se explícito ("quer atualização", "pode mandar mensagem") |
| fonte | enum | (voz_transcrita / texto_digitado) |
| raw_text_id | fk | Referência ao texto original |
| confianca_global | float | 0–1 |
| flags | array | ex: ["telefone_duvidoso","nome_incompleto"] |

## 3. Estrutura de Armazenamento

### Tabela / Planilha raw_entries
- raw_text_id
- timestamp_captura
- agente_id
- texto_original
- latitude / longitude (opcional)
- processado (bool)

### Tabela / Planilha structured_entries
Campos do esquema + raw_text_id.

## 4. Prompt Engineering (Extração)

### 4.1. Prompt Base (Sistema)
Você é um extrator de dados. Recebe um texto livre descrevendo um contato entre agente público e cidadão. Extraia os campos solicitados e responda exclusivamente JSON válido UTF-8, sem comentários.

### 4.2. Prompt Usuário (Template)
```
Texto bruto:
"""
{{RAW_TEXT}}
"""

Regras:
1. Se não houver evidência explícita de um campo, use null.
2. Inferir data/hora: se mencionada ("hoje cedo", "agora à tarde") converter usando referência de captura {{CAPTURE_TIMESTAMP}} (UTC ISO).
3. `tipo_demanda`: classifique em {ARVORE, BUEIRO, GRAMA, ILUMINACAO, LIMPEZA, SEGURANCA, OUTRO}.
4. Telefone: extrair dígitos; se brasileiro e faltar DDI, prefixar +55.
5. `consentimento_comunicacao`: true somente se texto indicar consentimento (ex: "quer receber", "pode mandar"). Caso contrário false.
6. `prioridade_percebida`: "alta" se menções a risco, urgência, vazamento, "média" se inconveniente moderado, senão "baixa".
7. `descricao_curta`: resumo objetivo máximo 120 caracteres.

Saída JSON:

{
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
  "confianca_campos": {
     "nome": 0-1,
     "telefone": 0-1,
     ...
  }
}
```

### 4.3. Few-Shot Exemplo

**Exemplo 1 (Entrada)**
"Falei agora 18/07 tarde com o Sr João na esquina da Rua A com B no bairro Centro, bueiro entupido saindo água, deu telefone 11988887777 e pediu pra avisar quando resolver."

**Exemplo 1 (Saída)**
```json
{
 "data_contato":"2025-07-18",
 "hora_contato":"15:30",
 "nome":"João",
 "telefone":"+5511988887777",
 "bairro":"Centro",
 "referencia_local":"Esquina Rua A com Rua B",
 "tipo_demanda":"BUEIRO",
 "descricao_curta":"Bueiro entupido escoando água na esquina Rua A x Rua B",
 "prioridade_percebida":"ALTA",
 "consentimento_comunicacao": true,
 "confianca_campos": {
   "nome":0.9,"telefone":0.95,"bairro":0.85,"tipo_demanda":0.98
 }
}
```

## 5. Pós-Processamento Automático

| Campo | Validação | Ação |
|-------|-----------|------|
| telefone | Regex `^\+55\d{10,11}$` | Se falhar → flag telefone_duvidoso |
| tipo_demanda | Enum válido? | Se não, OUTRO + flag |
| data_contato/hora | Parsers; se null → usar timestamp captura | Marcar origem_data=estimada |
| prioridade | Se não em {ALTA/MEDIA/BAIXA} → BAIXA | flag |
| nome | Menos de 3 chars? | flag nome_incompleto |
| bairro | Fuzzy match vs lista oficial | Substituir se similaridade > threshold, senão flag |

## 6. Estratégias de Conversão de Linguagem Natural → Estrutura

1. **LLM principal** (ex: GPT-4o ou outro via API) para extração JSON.
2. **Verificador JSON**: parse; se erro → solicitar reformat only (segundo prompt: "Retorne somente JSON corrigido").
3. **Camada de Regras** (Python) corrige e adiciona flags.
4. **Cálculo de confiança global**: média ponderada das confianças de campos essenciais (nome, telefone, tipo_demanda, bairro).
5. **Threshold**: se <0.75 → entra na fila_revisao.

## 7. Interface de Captura Não Estruturada (Campo)

| Opção | Vantagem | Notas |
|-------|----------|-------|
| App simples (Flutter / React Native) textbox grande + botão "Salvar" | Mais controle offline | Salva raw_entries SQLite |
| Bot Telegram (mensagem livre) | Implementação rápida | Texto enviado já timestampado |
| Gravação de áudio + Transcrição local (Whisper small) | Captura muito rápida | Transcreve offline → texto bruto |

**Sugestão prática**: usar áudio + Whisper (modelo local ou API) → garante velocidade; agente fala naturalmente.

## 8. Pipeline (Pseudo Arquitetura)

```
[App/Telegram/Áudio]
     |
 [Raw Collector] -> raw_entries (DB/Sheet)
     |
 [Dispatcher] (fila)
     |
 [LLM Extractor Worker] --(API call)--> JSON
     |
 [Rule Validator + Normalizer]
     |
 [structured_entries]
     |
 [Review UI] (apenas itens low confidence)
```

**Ferramentas enxutas**: Python + FastAPI + SQLite/Postgres + Celery/RQ (fila) + OpenAI (ou outro provedor) + Streamlit (review UI).

## 9. Custos e Performance

| Fator | Estimativa (Exemplo) |
|-------|---------------------|
| Tokens por extração | ~1k (prompt + saída + few-shots) |
| 100 registros/dia | 100k tokens → custo baixo (dependendo do modelo) |
| Latência por chamada | 1–3s (rede) |
| Otimização | Agrupar 5–10 textos em batch numa única chamada (instruir para retornar lista JSON) |

**Batch Prompt**: enumerar blocos ### ENTRY 1, ### ENTRY 2 e solicitar array JSON ordenado.

## 10. Tratamento de Ambiguidade

Se LLM retornar baixa confiança para bairro ou telefone:
- Campo fica null + flag → UI de revisão mostra texto original e sugestão de edição manual rápida (auto-foco).

## 11. Feedback Loop

1. Revisões manuais armazenam ground_truth.
2. Periodicamente gerar dataset (raw_text + corrected JSON).
3. Re-treinar prompt (melhor few-shot) ou fine‑tune modelo menor (se custo for questão).

**Métricas monitoradas**:
- Accuracy campo crítico (telefone válido)
- F1 de tipo_demanda
- Taxa de revisão manual (queremos cair com o tempo)

## 12. Exemplo de Código (Esboço Python)

```python
import json, datetime, re
import openai

SCHEMA_FIELDS = ["data_contato","hora_contato","nome","telefone","bairro",
                 "referencia_local","tipo_demanda","descricao_curta",
                 "prioridade_percebida","consentimento_comunicacao","confianca_campos"]

def build_prompt(raw_text, capture_ts):
    return PROMPT_TEMPLATE.format(RAW_TEXT=raw_text, CAPTURE_TIMESTAMP=capture_ts)

def call_llm(prompt):
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
          {"role":"system","content":SYSTEM_PROMPT},
          {"role":"user","content":prompt}
        ],
        temperature=0
    )
    return resp.choices[0].message.content

def normalize_phone(phone):
    digits = re.sub(r'\D','', phone or '')
    if digits.startswith('55'):
        pass
    elif len(digits) in (10,11):
        digits = '55' + digits
    return '+'+digits if digits else None

def post_process(obj, capture_ts):
    # telefone
    obj["telefone"] = normalize_phone(obj.get("telefone"))
    # data/hora fallback
    if not obj.get("data_contato"):
        obj["data_contato"] = capture_ts[:10]
    # prioridade default
    if obj.get("prioridade_percebida") not in ("ALTA","MEDIA","BAIXA"):
        obj["prioridade_percebida"] = "BAIXA"
    return obj
```

## 13. Privacidade / Riscos

| Risco | Mitigação |
|-------|-----------|
| Enviar PII à API externa | Avaliar uso de modelo self‑host (Llama3 / Mistral + guardrails) se sensibilidade alta |
| Alucinação (inventar telefone) | Regra: telefone deve estar explicitamente no texto; se LLM extrair sem dígitos no raw → descartar |
| Erro de categoria | Regras complementares (keywords) + majority vote (LLM + regra) |
| Vazamento de dados (logs) | Remover PII de logs; armazenar somente IDs |

**Guardrails simples**: após extração, verificar se cada campo aparece (ou base para derivação) no texto bruto (string match). Se não, anular.

## 14. Alternativa Híbrida (LLM + Regex)

1. Primeiro rodar extratores determinísticos: telefone, datas, horas.
2. LLM só classifica e resume (reduz tokens).
3. Prompt menor → custo menor.

## 15. Estratégia de Implementação por Fases

| Fase | Objetivo | Critério de Pronto |
|------|----------|-------------------|
| 1 | Captura raw + Batch LLM + Planilha saída | 95% outputs JSON válidos |
| 2 | Flags + UI revisão | <30% registros requerem revisão |
| 3 | Batch e compressão prompt | Custo/token reduzido >40% |
| 4 | Fine-tune / modelo local | Latência média <1s por registro |
| 5 | Guardrails semânticos + auto-feedback | Revisão <10% |

## 16. Exemplo Raw → Estruturado

**Raw:**
"Ontem à noite falei com Paulo perto do campo do bairro Jardim Azul, poste de luz apagado, quer que avisem quando arrumarem, telefone 21 99888 6677 prioridade média."

*Assumindo captura hoje (2025-07-18) e "ontem à noite" → 2025-07-17 20:00 (heurística simples).*

**Estruturado:**
```json
{
 "data_contato":"2025-07-17",
 "hora_contato":"20:00",
 "nome":"Paulo",
 "telefone":"+5521998886677",
 "bairro":"Jardim Azul",
 "referencia_local":"Campo do bairro Jardim Azul",
 "tipo_demanda":"ILUMINACAO",
 "descricao_curta":"Poste de luz apagado no campo do Jardim Azul",
 "prioridade_percebida":"MEDIA",
 "consentimento_comunicacao": true
}
```