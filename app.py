# app.py - Sistema com controle de Admin e Ownership
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
import os
import secrets
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Mude para uma chave segura
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['METADATA_FILE'] = 'file_metadata.json'  # Arquivo para guardar info dos uploads
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# Configurações do Admin
ADMIN_USERNAME = "everton"       # Mude aqui
ADMIN_PASSWORD = "12122323"    # Mude para uma senha forte

# Criar pasta uploads se não existir
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# ---------------------------
# Funções auxiliares
# ---------------------------

def load_file_metadata():
    try:
        if os.path.exists(app.config['METADATA_FILE']):
            with open(app.config['METADATA_FILE'], 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_file_metadata(metadata):
    with open(app.config['METADATA_FILE'], 'w') as f:
        json.dump(metadata, f, indent=2)

users_online = 0

def is_admin():
    return session.get('is_admin', False)

def get_current_user():
    if is_admin():
        return session.get('username', ADMIN_USERNAME)
    return session.get('user_id', f"user_{secrets.token_hex(4)}")

def can_delete_file(filename):
    if is_admin():
        return True
    
    metadata = load_file_metadata()
    file_info = metadata.get(filename, {})
    file_owner = file_info.get('uploader', '')
    current_user = get_current_user()

    if file_info.get('is_admin_upload', False):
        return False
    
    return file_owner == current_user

# ---------------------------
# Rotas Flask
# ---------------------------

@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    metadata = load_file_metadata()
    current_user = get_current_user()

    files_info = []
    for filename in files:
        file_info = metadata.get(filename, {})
        files_info.append({
            'name': filename,
            'uploader': file_info.get('uploader', 'Desconhecido'),
            'upload_time': file_info.get('upload_time', ''),
            'is_admin_upload': file_info.get('is_admin_upload', False),
            'can_delete': can_delete_file(filename),
            'size': os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        })

    return render_template('index1.html', 
                       files_info=files_info,   # <<< passa infos completas
                       is_admin=is_admin(),
                       current_user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            return jsonify({
                'success': True, 
                'message': f'Login realizado com sucesso! Bem-vindo, {username}',
                'is_admin': True
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Credenciais inválidas'
            }), 401
    
    return render_template('admin_login_page.html')   # <<< corrigido

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logout realizado com sucesso'})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'Nenhum arquivo selecionado', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'Nenhum arquivo selecionado', 400
    
    if file:
        if not is_admin() and 'user_id' not in session:
            session['user_id'] = f"user_{secrets.token_hex(4)}"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        metadata = load_file_metadata()
        current_user = get_current_user()
        
        metadata[filename] = {
            'uploader': current_user,
            'upload_time': datetime.now().isoformat(),
            'is_admin_upload': is_admin(),
            'original_name': file.filename,
            'file_size': os.path.getsize(filepath)
        }
        
        save_file_metadata(metadata)
        
        user_type = "👑 ADMIN" if is_admin() else "👤 USER"
        print(f"📤 Upload: {filename} por {current_user} ({user_type})")
        
        return f'Arquivo {filename} enviado com sucesso!'

@app.route('/downloads/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return 'Arquivo não encontrado', 404

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    if not can_delete_file(filename):
        return jsonify({
            'status': 'error', 
            'message': '❌ Você não tem permissão para deletar este arquivo!'
        }), 403
    
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            
            metadata = load_file_metadata()
            if filename in metadata:
                del metadata[filename]
                save_file_metadata(metadata)
            
            current_user = get_current_user()
            user_type = "👑 ADMIN" if is_admin() else "👤 USER"
            print(f"🗑️ Delete: {filename} por {current_user} ({user_type})")
            
            return jsonify({
                'status': 'ok', 
                'message': f'✅ Arquivo {filename} deletado com sucesso!'
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': 'Arquivo não encontrado'
            }), 404
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': f'Erro ao deletar: {str(e)}'
        }), 500

@app.route('/admin/status')
def admin_status():
    return jsonify({
        'is_admin': is_admin(),
        'username': session.get('username', ''),
        'login_time': session.get('login_time', '')
    })

@app.route('/chat')
def chat():
    return render_template('chat.html')

# ---------------------------
# Eventos Socket.IO
# ---------------------------

@socketio.on('connect')
def handle_connect():
    global users_online
    users_online += 1
    emit('user_count', users_online, broadcast=True)
    print(f"👤 Usuário conectado. Online: {users_online}")

@socketio.on('disconnect')
def handle_disconnect():
    global users_online
    users_online = max(0, users_online - 1)
    emit('user_count', users_online, broadcast=True)
    print(f"👤 Usuário desconectado. Online: {users_online}")

@socketio.on('message')
def handle_message(data):
    global users_online
    text = data.get('text', '')
    
    # Tratamento de comandos
    if text.startswith('/'):
        if text == '/clear':
            emit('clear_chat', broadcast=True)
        elif text == '/time':
            emit('system_message', {
                'user': 'SYSTEM',
                'text': f'Hora atual: {datetime.now().strftime("%H:%M:%S")}'
            }, broadcast=True)
        elif text == '/help':
            emit('system_message', {
                'user': 'SYSTEM',
                'text': 'Comandos disponíveis: /clear /time /help /status'
            }, broadcast=True)
        elif text == '/status':
            emit('system_message', {
                'user': 'SYSTEM',
                'text': f'Usuários online: {users_online}'
            }, broadcast=True)
        return
    
    # Mensagens normais
    data['time'] = datetime.now().strftime('%H:%M:%S')
    emit('user_message', data, broadcast=True)

@socketio.on('get_user_count')
def handle_get_user_count():
    emit('user_count', users_online)

# ---------------------------
# Main
# ---------------------------

if __name__ == '__main__':
    print("🚀 CodeShare Server Starting...")
    print(f"👑 Admin: {ADMIN_USERNAME}")
    print("🔒 Apenas admin pode deletar arquivos!")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
