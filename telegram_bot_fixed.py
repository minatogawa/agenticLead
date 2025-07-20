"""
Bot do Telegram com processamento automático MELHORADO
Versão com melhor tratamento de erros e logs detalhados
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import db
from config import TELEGRAM_BOT_TOKEN
import asyncio
import traceback
from datetime import datetime

# Configurar logging detalhado
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgenticLeadBotFixed:
    """Bot do Telegram com processamento automático melhorado"""
    
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Configura os handlers do bot"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CommandHandler("process", self.manual_process))  # Comando manual
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.LOCATION, self.handle_location))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /start"""
        welcome_message = """
🤖 **Bem-vindo ao AgenticLead v2.0!**

Sou um assistente para captura de demandas públicas com IA.

📝 **Como usar:**
- Digite suas observações em texto livre
- Processamento automático com IA
- Export automático para Excel/CSV

📋 **Comandos:**
/help - Ajuda detalhada
/stats - Suas estatísticas
/process - Forçar processamento manual

**Exemplo:**
"Hoje falei com João na Praça Central, bueiro entupido, telefone 11 99999-8888, urgente"

✨ **NOVO**: Processamento automático ativado!
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /help"""
        help_message = """
📚 **Ajuda - AgenticLead v2.0**

**Fluxo automático:**
1. Digite sua mensagem
2. IA extrai dados automaticamente
3. Excel/CSV atualizados na pasta

**Formato sugerido:**
• Data e hora do contato
• Nome do cidadão 
• Telefone de contato
• Local (bairro, referência)
• Tipo de problema
• Descrição e urgência

**Tipos detectados automaticamente:**
🌳 ARVORE/PODA - Árvores
🚰 BUEIRO - Problemas de drenagem
🌱 GRAMA - Manutenção
💡 ILUMINACAO - Postes, lâmpadas
🧹 LIMPEZA - Coleta, varrição
🛡️ SEGURANCA - Problemas de segurança
❓ OUTRO - Outros tipos

**Comandos especiais:**
/process - Força processamento manual
/stats - Ver suas estatísticas
        """
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /stats"""
        try:
            user_id = str(update.effective_user.id)
            
            # Stats do usuário
            raw_count = len(db.session.query(db.RawEntry).filter(
                db.RawEntry.agente_id == user_id
            ).all())
            
            unprocessed_count = len(db.session.query(db.RawEntry).filter(
                db.RawEntry.agente_id == user_id,
                db.RawEntry.processado == False
            ).all())
            
            # Stats globais
            from auto_processor import AutoProcessor
            processor = AutoProcessor()
            global_stats = processor.get_summary_stats()
            
            stats_message = f"""
📊 **Suas Estatísticas**

👤 **Seus dados:**
📝 Total de registros: {raw_count}
⏳ Pendentes: {unprocessed_count}
✅ Processados: {raw_count - unprocessed_count}

🌍 **Sistema global:**
📊 Total no sistema: {global_stats.get('entries', {}).get('total_raw', 0)}
🎯 Cobertura: {global_stats.get('entries', {}).get('coverage', 0)}%

🤖 Sistema funcionando normalmente!
            """
            await update.message.reply_text(stats_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            await update.message.reply_text("❌ Erro ao buscar estatísticas.")
    
    async def manual_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para forçar processamento manual"""
        try:
            await update.message.reply_text("🔄 Executando processamento manual...")
            
            from auto_processor import AutoProcessor
            processor = AutoProcessor()
            results = await processor.process_new_entries()
            
            if results["success"]:
                await update.message.reply_text(
                    f"✅ Processamento manual concluído!\n"
                    f"📊 {results['message']}\n"
                    f"⏱️ Tempo: {results['total_time']}s"
                )
            else:
                await update.message.reply_text(
                    f"❌ Erro no processamento: {results['message']}"
                )
                
        except Exception as e:
            logger.error(f"Erro no processamento manual: {e}")
            await update.message.reply_text("❌ Erro no processamento manual.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler principal para mensagens de texto - VERSÃO MELHORADA"""
        processing_start = datetime.now()
        
        try:
            user_id = str(update.effective_user.id)
            username = update.effective_user.username or "N/A"
            message_text = update.message.text
            message_id = update.message.message_id
            
            logger.info(f"INICIO - Mensagem de {username} ({user_id}): {message_text[:50]}...")
            
            # Passo 1: Salvar no banco
            logger.info("PASSO 1: Salvando no banco...")
            raw_id = db.save_raw_entry(
                agente_id=user_id,
                texto=message_text,
                message_id=message_id
            )
            logger.info(f"PASSO 1: Raw entry {raw_id} salva com sucesso")
            
            # Passo 2: Confirmar recebimento
            await update.message.reply_text(
                f"✅ Registro #{raw_id} salvo!\n"
                f"🤖 Processando com IA...\n"
                f"⏳ Aguarde..."
            )
            
            # Passo 3: Processamento automático COM LOGS DETALHADOS
            logger.info("PASSO 2: Iniciando processamento automático...")
            
            try:
                from auto_processor import AutoProcessor
                processor = AutoProcessor()
                
                logger.info("PASSO 2a: AutoProcessor criado")
                
                # Executar pipeline completo
                logger.info("PASSO 2b: Executando process_new_entries...")
                results = await processor.process_new_entries()
                logger.info(f"PASSO 2c: Processamento concluído: {results}")
                
                processing_time = (datetime.now() - processing_start).total_seconds()
                
                if results["success"]:
                    # Notificar sucesso
                    success_msg = (
                        f"🎉 Processamento concluído!\n"
                        f"📊 {results['message']}\n"
                        f"📁 Arquivos: agenticlead_dados.xlsx/.csv\n"
                        f"⏱️ Tempo total: {processing_time:.2f}s"
                    )
                    await update.message.reply_text(success_msg)
                    logger.info(f"SUCESSO - {results['message']} em {processing_time:.2f}s")
                else:
                    # Notificar erro
                    error_msg = (
                        f"⚠️ Erro no processamento automático.\n"
                        f"📝 Dados salvos (ID #{raw_id})\n"
                        f"🔧 Use /process para tentar novamente"
                    )
                    await update.message.reply_text(error_msg)
                    logger.error(f"ERRO no processamento: {results['message']}")
                
            except Exception as proc_error:
                processing_time = (datetime.now() - processing_start).total_seconds()
                logger.error(f"ERRO CRÍTICO no processamento: {proc_error}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                error_msg = (
                    f"⚠️ Erro no processamento automático.\n"
                    f"📝 Dados salvos (ID #{raw_id})\n"
                    f"🔧 Use /process para processar manualmente\n"
                    f"⏱️ Falhou em {processing_time:.2f}s"
                )
                await update.message.reply_text(error_msg)
            
        except Exception as e:
            logger.error(f"ERRO TOTAL na mensagem: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await update.message.reply_text(
                f"❌ Erro crítico ao processar mensagem.\n"
                f"🔧 Use /process para tentar processamento manual."
            )
    
    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para localização compartilhada"""
        try:
            location = update.message.location
            user_id = str(update.effective_user.id)
            
            location_text = f"LOCALIZAÇÃO: Latitude {location.latitude}, Longitude {location.longitude}"
            
            raw_id = db.save_raw_entry(
                agente_id=user_id,
                texto=location_text,
                message_id=update.message.message_id,
                lat=location.latitude,
                lon=location.longitude
            )
            
            await update.message.reply_text(
                f"📍 Localização #{raw_id} recebida!\n"
                f"🗺️ Lat: {location.latitude:.6f}, Lon: {location.longitude:.6f}\n"
                f"💬 Envie agora a descrição do problema."
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar localização: {e}")
            await update.message.reply_text("❌ Erro ao processar localização.")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler global para erros"""
        logger.error(f"ERRO GLOBAL: {context.error}")
        logger.error(f"Update: {update}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    def run(self):
        """Inicia o bot"""
        logger.info("🤖 Iniciando AgenticLead Bot v2.0 (FIXED)...")
        self.application.add_error_handler(self.error_handler)
        self.application.run_polling()

if __name__ == "__main__":
    bot = AgenticLeadBotFixed()
    bot.run()