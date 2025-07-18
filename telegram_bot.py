"""
Bot do Telegram para captura de demandas públicas
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import db
from config import TELEGRAM_BOT_TOKEN
import asyncio

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AgenticLeadBot:
    """Classe principal do bot do Telegram"""
    
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Configura os handlers do bot"""
        # Comando /start
        self.application.add_handler(CommandHandler("start", self.start))
        
        # Comando /help
        self.application.add_handler(CommandHandler("help", self.help))
        
        # Comando /stats
        self.application.add_handler(CommandHandler("stats", self.stats))
        
        # Handler para mensagens de texto
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Handler para localização
        self.application.add_handler(MessageHandler(filters.LOCATION, self.handle_location))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /start"""
        welcome_message = """
🤖 **Bem-vindo ao AgenticLead!**

Sou um assistente para captura de demandas públicas.

📝 **Como usar:**
- Digite suas observações em texto livre
- Inclua informações como: data, nome do cidadão, telefone, local, tipo de problema
- Posso processar localização se você enviar

📋 **Comandos disponíveis:**
/help - Ajuda
/stats - Estatísticas

**Exemplo:**
"Hoje 18/07 falei com Maria Silva na Praça Central, bueiro entupido na esquina da Rua A com Rua B, telefone 11 99999-8888, urgente porque tem crianças passando"
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /help"""
        help_message = """
📚 **Ajuda - AgenticLead**

**Formato sugerido para relatos:**
• Data e hora do contato
• Nome do cidadão 
• Telefone de contato
• Local (bairro, referência)
• Tipo de problema
• Descrição do problema
• Nível de urgência

**Tipos de demanda aceitos:**
🌳 ARVORE - Poda, corte, plantio
🚰 BUEIRO - Entupimento, limpeza
🌱 GRAMA - Corte, manutenção
💡 ILUMINACAO - Postes, lâmpadas
🧹 LIMPEZA - Coleta, varrição
🛡️ SEGURANCA - Problemas de segurança
❓ OUTRO - Outros tipos

**Dicas:**
• Seja específico com localizações
• Inclua telefone sempre que possível
• Mencione urgência quando relevante
        """
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /stats"""
        try:
            # Contar entradas por usuário
            raw_count = len(db.session.query(db.RawEntry).filter(
                db.RawEntry.agente_id == str(update.effective_user.id)
            ).all())
            
            unprocessed_count = len(db.session.query(db.RawEntry).filter(
                db.RawEntry.agente_id == str(update.effective_user.id),
                db.RawEntry.processado == False
            ).all())
            
            stats_message = f"""
📊 **Suas Estatísticas**

📝 Total de registros: {raw_count}
⏳ Aguardando processamento: {unprocessed_count}
✅ Processados: {raw_count - unprocessed_count}

🤖 Sistema funcionando normalmente!
            """
            await update.message.reply_text(stats_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            await update.message.reply_text("❌ Erro ao buscar estatísticas.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler principal para mensagens de texto"""
        try:
            user_id = str(update.effective_user.id)
            username = update.effective_user.username or "N/A"
            message_text = update.message.text
            message_id = update.message.message_id
            
            logger.info(f"Mensagem recebida de {username} ({user_id}): {message_text[:50]}...")
            
            # Salvar no banco de dados
            raw_id = db.save_raw_entry(
                agente_id=user_id,
                texto=message_text,
                message_id=message_id
            )
            
            # Confirmar recebimento
            await update.message.reply_text(
                f"✅ Registro #{raw_id} salvo com sucesso!\n"
                f"📝 Texto capturado e será processado em breve.\n"
                f"🔄 Use /stats para acompanhar o processamento."
            )
            
            # TODO: Aqui chamaremos o pipeline de processamento
            logger.info(f"Raw entry {raw_id} salva para processamento posterior")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            await update.message.reply_text(
                "❌ Erro ao processar sua mensagem. Tente novamente."
            )
    
    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para localização compartilhada"""
        try:
            location = update.message.location
            user_id = str(update.effective_user.id)
            
            # Salvar localização como texto especial
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
                f"💬 Envie agora a descrição do problema neste local."
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar localização: {e}")
            await update.message.reply_text("❌ Erro ao processar localização.")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para erros"""
        logger.error(f"Erro: {context.error}")
    
    def run(self):
        """Inicia o bot"""
        logger.info("🤖 Iniciando AgenticLead Bot...")
        self.application.add_error_handler(self.error_handler)
        self.application.run_polling()

if __name__ == "__main__":
    bot = AgenticLeadBot()
    bot.run()