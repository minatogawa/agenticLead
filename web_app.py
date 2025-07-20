"""
Interface Web para AgenticLead
Dashboard simples com Bootstrap
"""
from flask import Flask, render_template, jsonify, request
from database import db, StructuredEntry, RawEntry
from auto_processor import AutoProcessor
from sqlalchemy import func, desc
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Página principal com dashboard"""
    try:
        # Estatísticas gerais
        total_raw = db.session.query(RawEntry).count()
        total_structured = db.session.query(StructuredEntry).count()
        unprocessed = db.session.query(RawEntry).filter(RawEntry.processado == False).count()
        
        # Status de extração
        status_counts = {}
        try:
            status_query = db.session.query(
                StructuredEntry.extraction_status,
                func.count(StructuredEntry.id).label('count')
            ).group_by(StructuredEntry.extraction_status).all()
            
            for status, count in status_query:
                status_counts[status or 'pending'] = count
        except:
            status_counts = {'unknown': total_structured}
        
        # Tipos de demanda
        tipos_demanda = {}
        try:
            tipos_query = db.session.query(
                StructuredEntry.tipo_demanda,
                func.count(StructuredEntry.id).label('count')
            ).group_by(StructuredEntry.tipo_demanda).all()
            
            for tipo, count in tipos_query:
                tipos_demanda[tipo or 'Não classificado'] = count
        except:
            tipos_demanda = {}
        
        # Confiança média
        try:
            avg_confidence = db.session.query(
                func.avg(StructuredEntry.confianca_global)
            ).filter(StructuredEntry.confianca_global.isnot(None)).scalar() or 0
        except:
            avg_confidence = 0
        
        # Últimas entradas
        latest_entries = []
        try:
            latest = db.session.query(StructuredEntry, RawEntry).join(
                RawEntry, StructuredEntry.raw_text_id == RawEntry.id
            ).order_by(desc(StructuredEntry.id)).limit(5).all()
            
            for structured, raw in latest:
                latest_entries.append({
                    'id': structured.id,
                    'nome': structured.nome or 'N/A',
                    'tipo_demanda': structured.tipo_demanda or 'N/A',
                    'bairro': structured.bairro or 'N/A',
                    'timestamp': raw.timestamp_captura.strftime('%d/%m %H:%M'),
                    'status': structured.extraction_status or 'pending'
                })
        except Exception as e:
            print(f"Erro ao buscar últimas entradas: {e}")
        
        coverage = round((total_structured / total_raw * 100) if total_raw > 0 else 0, 1)
        
        stats = {
            'total_raw': total_raw,
            'total_structured': total_structured,
            'unprocessed': unprocessed,
            'coverage': coverage,
            'status_counts': status_counts,
            'tipos_demanda': tipos_demanda,
            'avg_confidence': round(avg_confidence, 3),
            'latest_entries': latest_entries
        }
        
        return render_template('dashboard.html', stats=stats)
        
    except Exception as e:
        return f"Erro ao carregar dashboard: {e}", 500

@app.route('/entradas')
def entradas():
    """Página com listagem de todas as entradas"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Query com paginação
        query = db.session.query(StructuredEntry, RawEntry).join(
            RawEntry, StructuredEntry.raw_text_id == RawEntry.id
        ).order_by(desc(StructuredEntry.id))
        
        # Filtros opcionais
        status_filter = request.args.get('status')
        tipo_filter = request.args.get('tipo')
        
        if status_filter and status_filter != 'all':
            query = query.filter(StructuredEntry.extraction_status == status_filter)
        
        if tipo_filter and tipo_filter != 'all':
            query = query.filter(StructuredEntry.tipo_demanda == tipo_filter)
        
        # Paginação
        offset = (page - 1) * per_page
        total = query.count()
        results = query.offset(offset).limit(per_page).all()
        
        # Preparar dados
        entradas_list = []
        for structured, raw in results:
            entradas_list.append({
                'id': structured.id,
                'nome': structured.nome or 'N/A',
                'telefone': structured.telefone or 'N/A',
                'bairro': structured.bairro or 'N/A',
                'tipo_demanda': structured.tipo_demanda or 'N/A',
                'descricao_curta': structured.descricao_curta or 'N/A',
                'prioridade_percebida': structured.prioridade_percebida or 'N/A',
                'confianca_global': round(structured.confianca_global or 0, 2),
                'extraction_status': structured.extraction_status or 'pending',
                'timestamp_captura': raw.timestamp_captura.strftime('%d/%m/%Y %H:%M'),
                'agente_id': raw.agente_id
            })
        
        # Dados para filtros
        status_options = db.session.query(StructuredEntry.extraction_status).distinct().all()
        tipos_options = db.session.query(StructuredEntry.tipo_demanda).distinct().all()
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page * per_page < total
        }
        
        return render_template('entradas.html', 
                             entradas=entradas_list, 
                             pagination=pagination,
                             status_options=[s[0] for s in status_options if s[0]],
                             tipos_options=[t[0] for t in tipos_options if t[0]],
                             current_status=status_filter,
                             current_tipo=tipo_filter)
        
    except Exception as e:
        return f"Erro ao carregar entradas: {e}", 500

@app.route('/entrada/<int:entry_id>')
def entrada_detalhe(entry_id):
    """Página de detalhes de uma entrada específica"""
    try:
        result = db.session.query(StructuredEntry, RawEntry).join(
            RawEntry, StructuredEntry.raw_text_id == RawEntry.id
        ).filter(StructuredEntry.id == entry_id).first()
        
        if not result:
            return "Entrada não encontrada", 404
        
        structured, raw = result
        
        # Preparar dados completos
        entrada = {
            'id': structured.id,
            'raw_text_id': structured.raw_text_id,
            
            # Dados extraídos
            'nome': structured.nome,
            'telefone': structured.telefone,
            'bairro': structured.bairro,
            'referencia_local': structured.referencia_local,
            'tipo_demanda': structured.tipo_demanda,
            'descricao_curta': structured.descricao_curta,
            'prioridade_percebida': structured.prioridade_percebida,
            'consentimento_comunicacao': structured.consentimento_comunicacao,
            'data_contato': structured.data_contato,
            'hora_contato': structured.hora_contato,
            
            # Metadados
            'confianca_global': structured.confianca_global,
            'confianca_campos': structured.confianca_campos,
            'extraction_status': structured.extraction_status,
            'flags': structured.flags,
            'error_msg': structured.error_msg,
            'revisado': structured.revisado,
            'timestamp_processamento': structured.timestamp_processamento,
            
            # Dados originais
            'texto_original': raw.texto_original,
            'timestamp_captura': raw.timestamp_captura,
            'agente_id': raw.agente_id,
            'latitude': raw.latitude,
            'longitude': raw.longitude,
            'telegram_message_id': raw.telegram_message_id
        }
        
        return render_template('entrada_detalhe.html', entrada=entrada)
        
    except Exception as e:
        return f"Erro ao carregar entrada: {e}", 500

@app.route('/api/stats')
def api_stats():
    """API endpoint para estatísticas (para AJAX)"""
    try:
        processor = AutoProcessor()
        stats = processor.get_summary_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def api_process():
    """API endpoint para processar entradas pendentes"""
    try:
        import asyncio
        processor = AutoProcessor()
        
        # Executar processamento
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(processor.process_new_entries())
        loop.close()
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)