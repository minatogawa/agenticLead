"""
Monitor automático - roda em background
Verifica novas entradas a cada 30 segundos e processa automaticamente
"""
import asyncio
import time
from datetime import datetime
from auto_processor import AutoProcessor
from database import db, RawEntry

class AutoMonitor:
    """Monitor que processa entradas automaticamente"""
    
    def __init__(self, check_interval=30):
        self.check_interval = check_interval
        self.processor = AutoProcessor()
        self.last_check = datetime.now()
        print(f"AutoMonitor iniciado - verificando a cada {check_interval}s")
    
    async def check_and_process(self):
        """Verifica e processa novas entradas"""
        try:
            # Verificar se há entradas não processadas
            unprocessed = db.session.query(RawEntry).filter(
                RawEntry.processado == False
            ).count()
            
            if unprocessed > 0:
                print(f"{datetime.now().strftime('%H:%M:%S')} - {unprocessed} entradas pendentes, processando...")
                
                results = await self.processor.process_new_entries()
                
                if results["success"]:
                    print(f"  ✅ {results['message']}")
                    print(f"  📁 Arquivos atualizados: agenticlead_dados.xlsx/.csv")
                else:
                    print(f"  ❌ Erro: {results['message']}")
            else:
                print(f"{datetime.now().strftime('%H:%M:%S')} - Sistema em dia, nenhuma entrada pendente")
                
        except Exception as e:
            print(f"❌ Erro no monitor: {e}")
    
    async def run_forever(self):
        """Executa monitoramento contínuo"""
        print("🔄 Monitor automático em execução...")
        print("📝 Envie mensagens no Telegram - serão processadas automaticamente!")
        print("🛑 Pressione Ctrl+C para parar\n")
        
        try:
            while True:
                await self.check_and_process()
                await asyncio.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitor interrompido pelo usuário")
        except Exception as e:
            print(f"❌ Erro fatal no monitor: {e}")

async def main():
    """Função principal"""
    monitor = AutoMonitor(check_interval=30)  # 30 segundos
    await monitor.run_forever()

if __name__ == "__main__":
    asyncio.run(main())