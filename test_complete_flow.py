"""
Teste completo do fluxo AgenticLead
"""
import requests
from api import app
from fastapi.testclient import TestClient

def test_complete_flow():
    """Testa o fluxo completo após processamento LLM"""
    print("=== TESTE COMPLETO DO FLUXO AGENTICLEAD ===")
    
    client = TestClient(app)
    
    # 1. Verificar estatísticas gerais
    print("\n1. ESTATISTICAS GERAIS:")
    response = client.get("/stats")
    stats = response.json()
    
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 2. Listar todas as entradas estruturadas
    print("\n2. ENTRADAS ESTRUTURADAS:")
    response = client.get("/structured")
    entries = response.json()
    
    print(f"   Total encontradas: {len(entries)}")
    
    for entry in entries[:3]:  # Mostrar apenas 3 primeiras
        print(f"\n   ID {entry['id']}:")
        print(f"     Nome: {entry['nome']}")
        print(f"     Telefone: {entry['telefone']}")
        print(f"     Tipo: {entry['tipo_demanda']}")
        print(f"     Prioridade: {entry['prioridade_percebida']}")
        print(f"     Confiança: {entry['confianca_global']}")
    
    # 3. Buscar uma entrada específica com dados da raw
    if len(entries) > 0:
        entry_id = entries[0]['id']
        print(f"\n3. DETALHES DA ENTRADA {entry_id}:")
        
        response = client.get(f"/structured/{entry_id}")
        detail = response.json()
        
        print(f"   Dados estruturados:")
        print(f"     Nome: {detail['nome']}")
        print(f"     Telefone: {detail['telefone']}")
        print(f"     Local: {detail['referencia_local']}")
        print(f"     Descrição: {detail['descricao_curta']}")
        
        print(f"   Dados originais:")
        print(f"     Agente: {detail['raw_entry']['agente_id']}")
        print(f"     Timestamp: {detail['raw_entry']['timestamp_captura']}")
        print(f"     Texto original: {detail['raw_entry']['texto_original'][:100]}...")
    
    # 4. Verificar entradas por status
    print("\n4. ENTRADAS POR STATUS:")
    
    completed = client.get("/structured?revisado=false").json()
    print(f"   Não revisadas: {len(completed)}")
    
    print("\n=== TESTE CONCLUIDO COM SUCESSO! ===")

if __name__ == "__main__":
    test_complete_flow()