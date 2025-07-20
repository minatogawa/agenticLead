"""
Teste do fluxo automático completo
Simula recebimento de mensagem + processamento automático
"""
import asyncio
from database import db
from auto_processor import AutoProcessor
import os

def simulate_new_message():
    """Simula recebimento de nova mensagem via Telegram"""
    
    # Adicionar nova raw entry
    test_message = "Ontem à noite falei com Sr. Carlos no bairro Vila Nova, lâmpada queimada na Rua das Palmeiras 123, telefone 21 98765-4321, ele disse que é urgente pois tem crianças estudando à noite"
    
    raw_id = db.save_raw_entry(
        agente_id="test_user_123",
        texto=test_message,
        message_id=999
    )
    
    print(f"Mensagem teste criada: raw_id {raw_id}")
    print(f"Texto: {test_message[:80]}...")
    
    return raw_id

async def test_automatic_flow():
    """Testa o fluxo automático completo"""
    print("=== TESTE DO FLUXO AUTOMATICO ===")
    
    # Verificar arquivos antes
    xlsx_exists_before = os.path.exists("agenticlead_dados.xlsx")
    csv_exists_before = os.path.exists("agenticlead_dados.csv")
    
    print(f"\nArquivos antes:")
    print(f"  agenticlead_dados.xlsx: {'EXISTS' if xlsx_exists_before else 'NOT FOUND'}")
    print(f"  agenticlead_dados.csv: {'EXISTS' if csv_exists_before else 'NOT FOUND'}")
    
    # Simular nova mensagem
    print(f"\n1. Simulando nova mensagem no Telegram...")
    raw_id = simulate_new_message()
    
    # Executar processamento automático
    print(f"\n2. Executando processamento automatico...")
    processor = AutoProcessor()
    
    results = await processor.process_new_entries()
    
    # Mostrar resultados
    print(f"\n3. Resultados:")
    print(f"   Success: {results['success']}")
    print(f"   Message: {results['message']}")
    print(f"   Tempo: {results['total_time']}s")
    
    steps = results['steps']
    print(f"   Placeholders criados: {steps['placeholders']['processed']}")
    print(f"   LLM processadas: {steps['llm_extraction']['processed']}")
    print(f"   Export XLSX: {'OK' if steps['export']['xlsx'] else 'ERRO'}")
    print(f"   Export CSV: {'OK' if steps['export']['csv'] else 'ERRO'}")
    
    # Verificar arquivos depois
    xlsx_exists_after = os.path.exists("agenticlead_dados.xlsx")
    csv_exists_after = os.path.exists("agenticlead_dados.csv")
    
    print(f"\nArquivos depois:")
    print(f"  agenticlead_dados.xlsx: {'EXISTS' if xlsx_exists_after else 'NOT FOUND'}")
    print(f"  agenticlead_dados.csv: {'EXISTS' if csv_exists_after else 'NOT FOUND'}")
    
    # Verificar tamanhos dos arquivos (se foram atualizados)
    if xlsx_exists_after:
        xlsx_size = os.path.getsize("agenticlead_dados.xlsx")
        print(f"  Tamanho XLSX: {xlsx_size} bytes")
    
    if csv_exists_after:
        csv_size = os.path.getsize("agenticlead_dados.csv")
        print(f"  Tamanho CSV: {csv_size} bytes")
    
    # Mostrar estatísticas finais
    print(f"\n4. Estatisticas finais:")
    stats = processor.get_summary_stats()
    
    if "error" not in stats:
        print(f"   Total raw entries: {stats['entries']['total_raw']}")
        print(f"   Total structured: {stats['entries']['total_structured']}")
        print(f"   Coverage: {stats['entries']['coverage']}%")
        
        tipos = stats['export']['por_tipo_demanda']
        if tipos:
            print("   Tipos encontrados:")
            for tipo, count in tipos.items():
                print(f"     {tipo}: {count}")
    
    print(f"\n=== TESTE CONCLUIDO ===")

def main():
    """Executa teste"""
    asyncio.run(test_automatic_flow())

if __name__ == "__main__":
    main()