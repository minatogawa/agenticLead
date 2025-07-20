"""
Teste unitário para o endpoint GET /structured/{id}
E2-S4: Teste unidade
"""
import requests
import json
from api import app
from fastapi.testclient import TestClient

def test_api_endpoints():
    """Testa os endpoints da API"""
    print("Testando AgenticLead API")
    print("=" * 30)
    
    # Criar cliente de teste
    client = TestClient(app)
    
    # Teste 1: Endpoint raiz
    print("1. Testando endpoint raiz (/)...")
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Message: {data['message']}")
    print("   [OK]")
    
    # Teste 2: Estatísticas
    print("\n2. Testando endpoint /stats...")
    response = client.get("/stats")
    assert response.status_code == 200
    stats = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Total raw entries: {stats['total_raw_entries']}")
    print(f"   Total structured entries: {stats['total_structured_entries']}")
    print(f"   Coverage: {stats['coverage_percent']}%")
    print("   [OK]")
    
    # Teste 3: Listar estruturadas
    print("\n3. Testando endpoint /structured...")
    response = client.get("/structured")
    assert response.status_code == 200
    entries = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Entradas encontradas: {len(entries)}")
    print("   [OK]")
    
    # Teste 4: Buscar por ID específico (se existir)
    if stats['total_structured_entries'] > 0:
        print("\n4. Testando endpoint /structured/1...")
        response = client.get("/structured/1")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            entry = response.json()
            print(f"   ID: {entry['id']}")
            print(f"   Raw text ID: {entry['raw_text_id']}")
            print(f"   Fonte: {entry['fonte']}")
            print(f"   Revisado: {entry['revisado']}")
            print(f"   Texto original: {entry['raw_entry']['texto_original'][:50]}...")
            print("   [OK]")
        else:
            print(f"   Erro: {response.json()}")
    
    # Teste 5: ID inexistente (deve retornar 404)
    print("\n5. Testando ID inexistente /structured/999...")
    response = client.get("/structured/999")
    print(f"   Status: {response.status_code}")
    if response.status_code == 404:
        print("   [OK] - 404 esperado")
    else:
        print(f"   [ERRO] - Esperado 404, recebido {response.status_code}")
    
    print("\nTodos os testes concluídos!")

if __name__ == "__main__":
    test_api_endpoints()