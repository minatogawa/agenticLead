"""
Configurações do sistema AgenticLead
"""
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Token do Bot Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Configurações do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///agenticlead.db")

# Configurações da API OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Configurações de confiança
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

# Tipos de demanda válidos
TIPOS_DEMANDA = [
    "ARVORE",
    "BUEIRO", 
    "GRAMA",
    "ILUMINACAO",
    "LIMPEZA",
    "SEGURANCA",
    "OUTRO"
]

# Prioridades válidas
PRIORIDADES = ["ALTA", "MEDIA", "BAIXA"]

# Configurações de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "agenticlead.log"