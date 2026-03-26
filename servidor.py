# servidor.py - VERSIÓN CORREGIDA PARA RENDER Y LOCAL
import os
import sys
import socket
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from io import BytesIO

# Importar pandas de forma segura (para evitar errores si no está instalado)
try:
    import pandas as pd
    PANDAS_DISPONIBLE = True
except ImportError:
    PANDAS_DISPONIBLE = False
    print("⚠️ ADVERTENCIA: pandas no está instalado")

# ========== CONFIGURACIÓN PARA RENDER (NUBE) VS LOCAL ==========
# Detectar si estamos en Render (nube)
ES_RENDER = os.environ.get('RENDER') or os.environ.get('DATABASE_URL')

# Crear la aplicación Flask
app = Flask(__name__)

# Configuración de la base de datos - DETECCIÓN AUTOMÁTICA
if ES_RENDER:
    # En Render: usar /tmp (carpeta temporal pero persistente mientras corre)
    RUTA_FIJA_DB = '/tmp/base_vasconia.db'
    base_dir = '/tmp'
    print("🚀 EJECUTANDO EN RENDER (NUBE)")
    print(f"📁 Base de datos en: {RUTA_FIJA_DB}")
else:
    # En local: usar la carpeta del proyecto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    RUTA_FIJA_DB = os.path.join(base_dir, 'base_vasconia.db')
    print("💻 EJECUTANDO EN LOCAL")
    print(f"📁 Base de datos en: {RUTA_FIJA_DB}")

# Configurar la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{RUTA_FIJA_DB}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Crear carpetas necesarias (solo si es necesario, con try/except para evitar errores en Render)
try:
    os.makedirs(os.path.join(base_dir, 'templates'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'static', 'logos'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'static', 'img'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'fotos'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'backups'), exist_ok=True)
except Exception as e:
    print(f"⚠️ No se pudieron crear algunas carpetas: {e}")

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# ==================== MODELO PARA CONTRASEÑA ====================
class Configuracion(db.Model):
    __tablename__ = 'configuracion'
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(200), nullable=False)

# ==================== MODELOS PRINCIPALES ====================
class Personal(db.Model):
    __tablename__ = 'personal'
    id = db.Column(db.Integer, primary_key=True)
    documento = db.Column(db.String(20), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(200))
    empresa = db.Column(db.String(100))
    cargo = db.Column(db.String(100))
    sexo = db.Column(db.String(20))
    telefono = db.Column(db.String(50))
    telefono_emergencia = db.Column(db.String(50))
    nombre_emergencia = db.Column(db.String(200))
    equipo_emergencia = db.Column(db.String(200))
    inicio_vigencia = db.Column(db.String(20))
    fin_vigencia = db.Column(db.String(20))
    rh = db.Column(db.String(10))
    estado = db.Column(db.String(50))
    dias_disponibles = db.Column(db.String(50))
    fecha_registro = db.Column(db.String(50))
    ultima_actualizacion = db.Column(db.String(50))

class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(20), unique=True, nullable=False)
    tipo_vehiculo = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    ingreso = db.Column(db.String(50))
    inicio_vigencia = db.Column(db.String(20))
    fin_vigencia = db.Column(db.String(20))
    empresa = db.Column(db.String(100))
    observaciones = db.Column(db.String(500))
    estado = db.Column(db.String(50))
    dias_disponibles = db.Column(db.String(50))
    fecha_registro = db.Column(db.String(50))
    ultima_actualizacion = db.Column(db.String(50))

class MovimientoPersonal(db.Model):
    __tablename__ = 'movimientos_personal'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.String(20))
    hora = db.Column(db.String(20))
    movimiento = db.Column(db.String(20))
    usuario = db.Column(db.String(50))
    documento = db.Column(db.String(20))
    nombre_completo = db.Column(db.String(200))
    empresa = db.Column(db.String(100))
    cargo = db.Column(db.String(100))
    timestamp = db.Column(db.Float)

class MovimientoVehiculo(db.Model):
    __tablename__ = 'movimientos_vehiculos'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.String(20))
    hora = db.Column(db.String(20))
    movimiento = db.Column(db.String(20))
    usuario = db.Column(db.String(50))
    placa = db.Column(db.String(20))
    tipo_vehiculo = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    empresa = db.Column(db.String(100))
    timestamp = db.Column(db.Float)

class MovimientoMaterial(db.Model):
    __tablename__ = 'movimientos_materiales'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.String(20))
    hora = db.Column(db.String(20))
    movimiento = db.Column(db.String(20))
    usuario = db.Column(db.String(50))
    descripcion = db.Column(db.String(200))
    cantidad = db.Column(db.Float)
    unidad = db.Column(db.String(20))
    destino = db.Column(db.String(200))
    timestamp = db.Column(db.Float)

# Crear tablas y contraseña por defecto (esto debe ejecutarse dentro del contexto de la app)
with app.app_context():
    try:
        db.create_all()
        pwd = Configuracion.query.filter_by(clave='password').first()
        if not pwd:
            pwd = Configuracion(clave='password', valor='vasconia2026')
            db.session.add(pwd)
            db.session.commit()
        print("✅ Base de datos creada/verificada")
        print(f"📁 Base de datos: {RUTA_FIJA_DB}")
    except Exception as e:
        print(f"❌ Error al crear la base de datos: {e}")

# ==================== FUNCIONES AUXILIARES ====================
def calcular_estado_y_dias(fin_vigencia):
    try:
        if not fin_vigencia:
            return "Vigencia No Definida", "-"
        fin = datetime.strptime(fin_vigencia, '%Y-%m-%d').date()
        hoy = date.today()
        dias = (fin - hoy).days
        if dias > 2000:
            estado = "CORREGIR FECHA"
        elif dias >= 30:
            estado = "VIGENTE"
        elif dias >= 2:
            estado = "POR VENCER"
        elif dias == 1:
            estado = "VENCE MAÑANA"
        elif dias == 0:
            estado = "VENCE HOY"
        else:
            estado = "VENCIDO"
        if dias < 0:
            dias_str = f"VENCIDO HACE {abs(dias)} DÍAS"
        elif dias == 0:
            dias_str = "HOY"
        elif dias == 1:
            dias_str = "1 DÍA"
        else:
            dias_str = f"{dias} DÍAS"
        return estado, dias_str
    except Exception as e:
        return "Error", "-"

# ==================== LOGIN ====================
@app.route('/login')
def login():
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>INGRESOS VASCONIA - LOGIN</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI';}
            body{background:url('/static/img/fondo.png') no-repeat center center fixed;background-size:cover;height:100vh;display:flex;justify-content:center;align-items:center;}
            .login-container{background:white;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,0.3);width:400px;padding:40px;text-align:center;}
            .logos{display:flex;justify-content:center;gap:15px;margin-bottom:30px;}
            .logo-img{height:50px;width:150px;background:white;padding:8px 15px;border-radius:8px;box-shadow:0 4px 8px rgba(0,0,0,0.1);object-fit:contain;border:1px solid #e0e0e0;}
            h2{color:#2c3e50;font-size:28px;margin-bottom:10px;}
            .subtitle{color:#7f8c8d;margin-bottom:30px;font-size:14px;}
            .input-group{margin-bottom:20px;text-align:left;}
            .input-group label{display:block;margin-bottom:8px;color:#34495e;font-weight:500;font-size:14px;}
            .input-group input{width:100%;padding:12px 15px;border:2px solid #e0e0e0;border-radius:8px;font-size:14px;}
            .input-group input:focus{border-color:#3498db;outline:none;}
            button{width:100%;padding:12px;background:#3498db;color:white;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;margin-top:10px;}
            button:hover{background:#2980b9;}
            .forgot-password{margin-top:20px;}
            .forgot-password a{color:#3498db;text-decoration:none;font-size:14px;}
            .message{padding:12px;border-radius:8px;margin-top:20px;display:none;}
            .success{background:#d4edda;color:#155724;}
            .error{background:#f8d7da;color:#721c24;}
            .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);justify-content:center;align-items:center;}
            .modal-content{background:white;padding:30px;border-radius:15px;width:350px;}
            .btn-secondary{background:#95a5a6;}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logos">
                <img src="/static/logos/cenit.png" class="logo-img" alt="CENIT">
                <img src="/static/logos/odc.png" class="logo-img" alt="ODC">
                <img src="/static/logos/ocensa.png" class="logo-img" alt="OCENSA">
            </div>
            <h2>INGRESOS VASCONIA</h2>
            <div class="subtitle">Sistema de Control de Acceso</div>
            <form method="POST" action="/login">
                <div class="input-group"><label>Usuario</label><input type="text" name="usuario" value="admin" required></div>
                <div class="input-group"><label>Contraseña</label><input type="password" name="password" required></div>
                <button type="submit">Ingresar</button>
            </form>
            <div class="forgot-password"><a href="#" onclick="mostrarRecuperacion()">¿Olvidó su contraseña?</a></div>
            <div id="message" class="message"></div>
        </div>
        <div id="recoveryModal" class="modal">
            <div class="modal-content">
                <h3>Cambiar Contraseña</h3>
                <div class="input-group"><label>Nueva contraseña</label><input type="password" id="newPassword"></div>
                <div class="input-group"><label>Confirmar</label><input type="password" id="confirmPassword"></div>
                <div class="modal-buttons">
                    <button onclick="cambiarPassword()">Cambiar</button>
                    <button onclick="cerrarModal()" class="btn-secondary">Cancelar</button>
                </div>
            </div>
        </div>
        <script>
            function mostrarRecuperacion(){document.getElementById('recoveryModal').style.display='flex';}
            function cerrarModal(){document.getElementById('recoveryModal').style.display='none';}
            function cambiarPassword(){
                var n=document.getElementById('newPassword').value;
                var c=document.getElementById('confirmPassword').value;
                if(!n||!c){mostrarMensaje('Complete todos','error');return;}
                if(n!==c){mostrarMensaje('No coinciden','error');return;}
                if(n.length<6){mostrarMensaje('Mínimo 6 caracteres','error');return;}
                fetch('/cambiar_password',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({password:n})
                }).then(r=>r.json()).then(r=>{
                    if(r.exito){mostrarMensaje('✅ Contraseña cambiada','success');setTimeout(()=>cerrarModal(),1500);}
                    else{mostrarMensaje('❌ Error','error');}
                });
            }
            function mostrarMensaje(t,tipo){
                var m=document.getElementById('message');
                m.className='message '+tipo;
                m.innerHTML=t;
                m.style.display='block';
                setTimeout(()=>m.style.display='none',3000);
            }
        </script>
    </body>
    </html>
    '''

@app.route('/login', methods=['POST'])
def do_login():
    usuario = request.form.get('usuario')
    password = request.form.get('password')
    pwd = Configuracion.query.filter_by(clave='password').first()
    pass_actual = pwd.valor if pwd else 'vasconia2026'
    if usuario == "admin" and password == pass_actual:
        resp = redirect(url_for('index'))
        resp.set_cookie('auth', 'true')
        return resp
    else:
        return '''
        <!DOCTYPE html>
        <html>
        <head><style>body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);height:100vh;display:flex;justify-content:center;align-items:center;}.error-box{background:white;padding:40px;border-radius:20px;text-align:center;width:400px;}h2{color:#e74c3c;}</style></head>
        <body><div class="error-box"><h2>❌ Usuario o contraseña incorrectos</h2><a href="/login">Volver a intentar</a></div></body>
        </html>
        '''

@app.route('/cambiar_password', methods=['POST'])
def cambiar_password():
    data = request.json
    nueva = data.get('password')
    if not nueva or len(nueva) < 6:
        return jsonify({'exito': False, 'error': 'Contraseña muy corta'})
    pwd = Configuracion.query.filter_by(clave='password').first()
    if pwd:
        pwd.valor = nueva
    else:
        pwd = Configuracion(clave='password', valor=nueva)
        db.session.add(pwd)
    db.session.commit()
    return jsonify({'exito': True})

@app.route('/logout')
def logout():
    resp = redirect(url_for('login'))
    resp.set_cookie('auth', '', expires=0)
    return resp

def requiere_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.cookies.get('auth') != 'true':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requiere_login
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ==================== API PERSONAL ====================
@app.route('/api/buscar_personal', methods=['POST'])
def buscar_personal():
    data = request.json
    personal = Personal.query.filter_by(documento=data.get('documento')).first()
    if personal:
        estado, dias = calcular_estado_y_dias(personal.fin_vigencia)
        return jsonify({'encontrado': True, 'datos': {
            'documento': personal.documento,
            'nombre_completo': personal.nombre_completo,
            'empresa': personal.empresa,
            'cargo': personal.cargo,
            'sexo': personal.sexo,
            'telefono': personal.telefono,
            'telefono_emergencia': personal.telefono_emergencia,
            'nombre_emergencia': personal.nombre_emergencia,
            'equipo_emergencia': personal.equipo_emergencia,
            'inicio_vigencia': personal.inicio_vigencia,
            'fin_vigencia': personal.fin_vigencia,
            'rh': personal.rh,
            'estado': estado,
            'dias_disponibles': dias
        }})
    return jsonify({'encontrado': False})

@app.route('/api/guardar_personal', methods=['POST'])
def guardar_personal():
    data = request.json
    estado, dias = calcular_estado_y_dias(data.get('fin_vigencia'))
    personal = Personal.query.filter_by(documento=data.get('documento')).first()
    if personal:
        personal.nombre_completo = data.get('nombre_completo')
        personal.empresa = data.get('empresa')
        personal.cargo = data.get('cargo')
        personal.sexo = data.get('sexo')
        personal.telefono = data.get('telefono')
        personal.telefono_emergencia = data.get('telefono_emergencia')
        personal.nombre_emergencia = data.get('nombre_emergencia')
        personal.equipo_emergencia = data.get('equipo_emergencia')
        personal.inicio_vigencia = data.get('inicio_vigencia')
        personal.fin_vigencia = data.get('fin_vigencia')
        personal.rh = data.get('rh')
        personal.estado = estado
        personal.dias_disponibles = dias
        personal.ultima_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        personal = Personal(
            documento=data.get('documento'),
            nombre_completo=data.get('nombre_completo'),
            empresa=data.get('empresa'),
            cargo=data.get('cargo'),
            sexo=data.get('sexo'),
            telefono=data.get('telefono'),
            telefono_emergencia=data.get('telefono_emergencia'),
            nombre_emergencia=data.get('nombre_emergencia'),
            equipo_emergencia=data.get('equipo_emergencia'),
            inicio_vigencia=data.get('inicio_vigencia'),
            fin_vigencia=data.get('fin_vigencia'),
            rh=data.get('rh'),
            estado=estado,
            dias_disponibles=dias,
            fecha_registro=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ultima_actualizacion=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(personal)
    db.session.commit()
    return jsonify({'exito': True})

@app.route('/api/registrar_movimiento_personal', methods=['POST'])
def registrar_movimiento_personal():
    data = request.json
    mov = MovimientoPersonal(
        fecha=datetime.now().strftime('%Y-%m-%d'),
        hora=datetime.now().strftime('%H:%M:%S'),
        movimiento=data.get('movimiento'),
        usuario='VIGILANTE',
        documento=data.get('documento'),
        nombre_completo=data.get('nombre_completo'),
        empresa=data.get('empresa'),
        cargo=data.get('cargo'),
        timestamp=datetime.now().timestamp()
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify({'exito': True})

@app.route('/api/todos_movimientos_personal', methods=['GET'])
def todos_movimientos_personal():
    movs = MovimientoPersonal.query.order_by(MovimientoPersonal.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': m.id,
        'fecha': m.fecha,
        'hora': m.hora,
        'movimiento': m.movimiento,
        'documento': m.documento,
        'nombre_completo': m.nombre_completo,
        'empresa': m.empresa,
        'cargo': m.cargo
    } for m in movs])

@app.route('/api/eliminar_personal', methods=['POST'])
def eliminar_personal():
    personal = Personal.query.filter_by(documento=request.json.get('documento')).first()
    if personal:
        db.session.delete(personal)
        db.session.commit()
        return jsonify({'exito': True})
    return jsonify({'exito': False})

# ========== ENDPOINTS PARA EDICIÓN COMPLETA ==========
@app.route('/api/obtener_movimiento_personal/<int:id>', methods=['GET'])
def obtener_movimiento_personal(id):
    mov = MovimientoPersonal.query.get(id)
    if mov:
        return jsonify({
            'id': mov.id,
            'fecha': mov.fecha,
            'hora': mov.hora,
            'movimiento': mov.movimiento,
            'documento': mov.documento,
            'nombre_completo': mov.nombre_completo,
            'empresa': mov.empresa,
            'cargo': mov.cargo
        })
    return jsonify({'error': 'No encontrado'}), 404

@app.route('/api/actualizar_movimiento_personal', methods=['POST'])
def actualizar_movimiento_personal():
    data = request.json
    id_mov = data.get('id')
    mov = MovimientoPersonal.query.get(id_mov)
    if mov:
        mov.fecha = data.get('fecha', mov.fecha)
        mov.hora = data.get('hora', mov.hora)
        mov.movimiento = data.get('movimiento', mov.movimiento)
        mov.documento = data.get('documento', mov.documento)
        mov.nombre_completo = data.get('nombre_completo', mov.nombre_completo)
        mov.empresa = data.get('empresa', mov.empresa)
        mov.cargo = data.get('cargo', mov.cargo)
        db.session.commit()
        return jsonify({'exito': True})
    return jsonify({'exito': False})

@app.route('/api/eliminar_movimiento_personal', methods=['POST'])
def eliminar_movimiento_personal():
    data = request.json
    id_mov = data.get('id')
    mov = MovimientoPersonal.query.get(id_mov)
    if mov:
        db.session.delete(mov)
        db.session.commit()
        return jsonify({'exito': True})
    return jsonify({'exito': False})

@app.route('/api/todos_movimientos_personal_completo', methods=['GET'])
def todos_movimientos_personal_completo():
    movs = MovimientoPersonal.query.order_by(MovimientoPersonal.timestamp.desc()).limit(500).all()
    return jsonify([{
        'id': m.id,
        'fecha': m.fecha,
        'hora': m.hora,
        'movimiento': m.movimiento,
        'documento': m.documento,
        'nombre_completo': m.nombre_completo,
        'empresa': m.empresa,
        'cargo': m.cargo
    } for m in movs])

# ==================== API VEHÍCULOS ====================
@app.route('/api/buscar_vehiculo', methods=['POST'])
def buscar_vehiculo():
    data = request.json
    vehiculo = Vehiculo.query.filter_by(placa=data.get('placa', '').upper()).first()
    if vehiculo:
        estado, dias = calcular_estado_y_dias(vehiculo.fin_vigencia)
        return jsonify({'encontrado': True, 'datos': {
            'placa': vehiculo.placa,
            'tipo_vehiculo': vehiculo.tipo_vehiculo,
            'modelo': vehiculo.modelo,
            'ingreso': vehiculo.ingreso,
            'inicio_vigencia': vehiculo.inicio_vigencia,
            'fin_vigencia': vehiculo.fin_vigencia,
            'empresa': vehiculo.empresa,
            'observaciones': vehiculo.observaciones,
            'estado': estado,
            'dias_disponibles': dias
        }})
    return jsonify({'encontrado': False})

@app.route('/api/guardar_vehiculo', methods=['POST'])
def guardar_vehiculo():
    data = request.json
    estado, dias = calcular_estado_y_dias(data.get('fin_vigencia'))
    placa = data.get('placa', '').upper()
    vehiculo = Vehiculo.query.filter_by(placa=placa).first()
    if vehiculo:
        vehiculo.tipo_vehiculo = data.get('tipo_vehiculo')
        vehiculo.modelo = data.get('modelo')
        vehiculo.ingreso = data.get('ingreso')
        vehiculo.inicio_vigencia = data.get('inicio_vigencia')
        vehiculo.fin_vigencia = data.get('fin_vigencia')
        vehiculo.empresa = data.get('empresa')
        vehiculo.observaciones = data.get('observaciones')
        vehiculo.estado = estado
        vehiculo.dias_disponibles = dias
        vehiculo.ultima_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        vehiculo = Vehiculo(
            placa=placa,
            tipo_vehiculo=data.get('tipo_vehiculo'),
            modelo=data.get('modelo'),
            ingreso=data.get('ingreso'),
            inicio_vigencia=data.get('inicio_vigencia'),
            fin_vigencia=data.get('fin_vigencia'),
            empresa=data.get('empresa'),
            observaciones=data.get('observaciones'),
            estado=estado,
            dias_disponibles=dias,
            fecha_registro=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ultima_actualizacion=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(vehiculo)
    db.session.commit()
    return jsonify({'exito': True})

@app.route('/api/registrar_movimiento_vehiculo', methods=['POST'])
def registrar_movimiento_vehiculo():
    data = request.json
    mov = MovimientoVehiculo(
        fecha=datetime.now().strftime('%Y-%m-%d'),
        hora=datetime.now().strftime('%H:%M:%S'),
        movimiento=data.get('movimiento'),
        usuario='VIGILANTE',
        placa=data.get('placa'),
        tipo_vehiculo=data.get('tipo_vehiculo'),
        modelo=data.get('modelo'),
        empresa=data.get('empresa'),
        timestamp=datetime.now().timestamp()
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify({'exito': True})

@app.route('/api/movimientos_vehiculo', methods=['POST'])
def movimientos_vehiculo():
    data = request.json
    movs = MovimientoVehiculo.query.filter_by(placa=data.get('placa', '').upper())\
           .order_by(MovimientoVehiculo.timestamp.desc()).limit(50).all()
    return jsonify([{
        'id': m.id,
        'fecha': m.fecha,
        'hora': m.hora,
        'movimiento': m.movimiento,
        'placa': m.placa,
        'tipo_vehiculo': m.tipo_vehiculo,
        'modelo': m.modelo,
        'empresa': m.empresa
    } for m in movs])

@app.route('/api/todos_movimientos_vehiculo', methods=['GET'])
def todos_movimientos_vehiculo():
    movs = MovimientoVehiculo.query.order_by(MovimientoVehiculo.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': m.id,
        'fecha': m.fecha,
        'hora': m.hora,
        'movimiento': m.movimiento,
        'placa': m.placa,
        'tipo_vehiculo': m.tipo_vehiculo,
        'modelo': m.modelo,
        'empresa': m.empresa
    } for m in movs])

@app.route('/api/todos_movimientos_vehiculo_completo', methods=['GET'])
def todos_movimientos_vehiculo_completo():
    movs = MovimientoVehiculo.query.order_by(MovimientoVehiculo.timestamp.desc()).limit(500).all()
    return jsonify([{
        'id': m.id,
        'fecha': m.fecha,
        'hora': m.hora,
        'movimiento': m.movimiento,
        'placa': m.placa,
        'tipo_vehiculo': m.tipo_vehiculo,
        'modelo': m.modelo,
        'empresa': m.empresa
    } for m in movs])

@app.route('/api/eliminar_vehiculo', methods=['POST'])
def eliminar_vehiculo():
    v = Vehiculo.query.filter_by(placa=request.json.get('placa', '').upper()).first()
    if v:
        db.session.delete(v)
        db.session.commit()
        return jsonify({'exito': True})
    return jsonify({'exito': False})

# ========== ENDPOINTS PARA EDICIÓN COMPLETA DE VEHÍCULOS ==========
@app.route('/api/obtener_movimiento_vehiculo/<int:id>', methods=['GET'])
def obtener_movimiento_vehiculo(id):
    mov = MovimientoVehiculo.query.get(id)
    if mov:
        return jsonify({
            'id': mov.id,
            'fecha': mov.fecha,
            'hora': mov.hora,
            'movimiento': mov.movimiento,
            'placa': mov.placa,
            'tipo_vehiculo': mov.tipo_vehiculo,
            'modelo': mov.modelo,
            'empresa': mov.empresa
        })
    return jsonify({'error': 'No encontrado'}), 404

@app.route('/api/actualizar_movimiento_vehiculo', methods=['POST'])
def actualizar_movimiento_vehiculo():
    data = request.json
    id_mov = data.get('id')
    mov = MovimientoVehiculo.query.get(id_mov)
    if mov:
        mov.fecha = data.get('fecha', mov.fecha)
        mov.hora = data.get('hora', mov.hora)
        mov.movimiento = data.get('movimiento', mov.movimiento)
        mov.placa = data.get('placa', mov.placa)
        mov.tipo_vehiculo = data.get('tipo_vehiculo', mov.tipo_vehiculo)
        mov.modelo = data.get('modelo', mov.modelo)
        mov.empresa = data.get('empresa', mov.empresa)
        db.session.commit()
        return jsonify({'exito': True})
    return jsonify({'exito': False})

@app.route('/api/eliminar_movimiento_vehiculo', methods=['POST'])
def eliminar_movimiento_vehiculo():
    data = request.json
    id_mov = data.get('id')
    mov = MovimientoVehiculo.query.get(id_mov)
    if mov:
        db.session.delete(mov)
        db.session.commit()
        return jsonify({'exito': True})
    return jsonify({'exito': False})

# ==================== API MATERIALES ====================
@app.route('/api/registrar_movimiento_material', methods=['POST'])
def registrar_movimiento_material():
    data = request.json
    try:
        cantidad = float(data.get('cantidad', 0))
    except:
        cantidad = 0
    mov = MovimientoMaterial(
        fecha=datetime.now().strftime('%Y-%m-%d'),
        hora=datetime.now().strftime('%H:%M:%S'),
        movimiento=data.get('movimiento'),
        usuario='VIGILANTE',
        descripcion=data.get('descripcion'),
        cantidad=cantidad,
        unidad=data.get('unidad'),
        destino=data.get('destino'),
        timestamp=datetime.now().timestamp()
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify({'exito': True})

@app.route('/api/todos_movimientos_materiales', methods=['GET'])
def todos_movimientos_materiales():
    movs = MovimientoMaterial.query.order_by(MovimientoMaterial.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': m.id,
        'fecha': m.fecha,
        'hora': m.hora,
        'movimiento': m.movimiento,
        'descripcion': m.descripcion,
        'cantidad': m.cantidad,
        'unidad': m.unidad,
        'destino': m.destino
    } for m in movs])

# ========== ENDPOINTS PARA EDICIÓN COMPLETA DE MATERIALES ==========
@app.route('/api/obtener_movimiento_material/<int:id>', methods=['GET'])
def obtener_movimiento_material(id):
    mov = MovimientoMaterial.query.get(id)
    if mov:
        return jsonify({
            'id': mov.id,
            'fecha': mov.fecha,
            'hora': mov.hora,
            'movimiento': mov.movimiento,
            'descripcion': mov.descripcion,
            'cantidad': mov.cantidad,
            'unidad': mov.unidad,
            'destino': mov.destino
        })
    return jsonify({'error': 'No encontrado'}), 404

@app.route('/api/actualizar_movimiento_material', methods=['POST'])
def actualizar_movimiento_material():
    data = request.json
    id_mov = data.get('id')
    mov = MovimientoMaterial.query.get(id_mov)
    if mov:
        mov.fecha = data.get('fecha', mov.fecha)
        mov.hora = data.get('hora', mov.hora)
        mov.movimiento = data.get('movimiento', mov.movimiento)
        mov.descripcion = data.get('descripcion', mov.descripcion)
        try:
            mov.cantidad = float(data.get('cantidad', mov.cantidad))
        except:
            pass
        mov.unidad = data.get('unidad', mov.unidad)
        mov.destino = data.get('destino', mov.destino)
        db.session.commit()
        return jsonify({'exito': True})
    return jsonify({'exito': False})

@app.route('/api/eliminar_movimiento_material', methods=['POST'])
def eliminar_movimiento_material():
    data = request.json
    id_mov = data.get('id')
    mov = MovimientoMaterial.query.get(id_mov)
    if mov:
        db.session.delete(mov)
        db.session.commit()
        return jsonify({'exito': True})
    return jsonify({'exito': False})

# ==================== API EXPORTAR A EXCEL ====================
@app.route('/api/exportar_excel/<tipo>', methods=['GET'])
def exportar_excel(tipo):
    if not PANDAS_DISPONIBLE:
        return jsonify({'error': 'Pandas no disponible'}), 500
    
    output = BytesIO()
    if tipo == 'personal' or tipo == 'todos':
        personal_data = []
        for p in Personal.query.all():
            personal_data.append({
                'Documento': p.documento, 'Nombre': p.nombre_completo, 'Empresa': p.empresa,
                'Cargo': p.cargo, 'Sexo': p.sexo, 'Teléfono': p.telefono,
                'Tel. Emergencia': p.telefono_emergencia, 'Contacto Emergencia': p.nombre_emergencia,
                'Equipo Emergencia': p.equipo_emergencia, 'Inicio Vigencia': p.inicio_vigencia,
                'Fin Vigencia': p.fin_vigencia, 'RH': p.rh, 'Estado': p.estado, 'Días': p.dias_disponibles
            })
        df_personal = pd.DataFrame(personal_data)
    if tipo == 'vehiculos' or tipo == 'todos':
        vehiculos_data = []
        for v in Vehiculo.query.all():
            vehiculos_data.append({
                'Placa': v.placa, 'Tipo': v.tipo_vehiculo, 'Modelo': v.modelo,
                'Ingreso': v.ingreso, 'Inicio Vigencia': v.inicio_vigencia,
                'Fin Vigencia': v.fin_vigencia, 'Empresa': v.empresa,
                'Observaciones': v.observaciones, 'Estado': v.estado, 'Días': v.dias_disponibles
            })
        df_vehiculos = pd.DataFrame(vehiculos_data)
    if tipo == 'materiales' or tipo == 'todos':
        materiales_data = []
        for m in MovimientoMaterial.query.order_by(MovimientoMaterial.timestamp.desc()).limit(500).all():
            materiales_data.append({
                'Fecha': m.fecha, 'Hora': m.hora, 'Movimiento': m.movimiento,
                'Descripción': m.descripcion, 'Cantidad': m.cantidad,
                'Unidad': m.unidad, 'Destino': m.destino
            })
        df_materiales = pd.DataFrame(materiales_data)
    if tipo == 'todos':
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_personal.to_excel(writer, sheet_name='Personal', index=False)
            df_vehiculos.to_excel(writer, sheet_name='Vehículos', index=False)
            df_materiales.to_excel(writer, sheet_name='Materiales', index=False)
        filename = 'reporte_completo_vasconia.xlsx'
    elif tipo == 'personal':
        df_personal.to_excel(output, index=False, engine='openpyxl')
        filename = 'personal_vasconia.xlsx'
    elif tipo == 'vehiculos':
        df_vehiculos.to_excel(output, index=False, engine='openpyxl')
        filename = 'vehiculos_vasconia.xlsx'
    elif tipo == 'materiales':
        df_materiales.to_excel(output, index=False, engine='openpyxl')
        filename = 'materiales_vasconia.xlsx'
    else:
        return jsonify({'error': 'Tipo no válido'}), 400
    output.seek(0)
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ==================== API EXPORTAR MOVIMIENTOS ====================
@app.route('/api/exportar_movimientos/<tipo>', methods=['GET'])
def exportar_movimientos(tipo):
    if not PANDAS_DISPONIBLE:
        return jsonify({'error': 'Pandas no disponible'}), 500
    
    output = BytesIO()
    if tipo == 'personal':
        movs = MovimientoPersonal.query.order_by(MovimientoPersonal.timestamp.desc()).limit(1000).all()
        data = [{'Fecha': m.fecha, 'Hora': m.hora, 'Movimiento': m.movimiento,
                'Documento': m.documento, 'Nombre': m.nombre_completo,
                'Empresa': m.empresa, 'Cargo': m.cargo} for m in movs]
        df = pd.DataFrame(data)
        df.to_excel(output, index=False, engine='openpyxl')
        filename = 'movimientos_personal.xlsx'
    elif tipo == 'vehiculos':
        movs = MovimientoVehiculo.query.order_by(MovimientoVehiculo.timestamp.desc()).limit(1000).all()
        data = [{'Fecha': m.fecha, 'Hora': m.hora, 'Movimiento': m.movimiento,
                'Placa': m.placa, 'Tipo': m.tipo_vehiculo, 'Modelo': m.modelo,
                'Empresa': m.empresa} for m in movs]
        df = pd.DataFrame(data)
        df.to_excel(output, index=False, engine='openpyxl')
        filename = 'movimientos_vehiculos.xlsx'
    elif tipo == 'materiales':
        movs = MovimientoMaterial.query.order_by(MovimientoMaterial.timestamp.desc()).limit(1000).all()
        data = [{'Fecha': m.fecha, 'Hora': m.hora, 'Movimiento': m.movimiento,
                'Descripción': m.descripcion, 'Cantidad': m.cantidad,
                'Unidad': m.unidad, 'Destino': m.destino} for m in movs]
        df = pd.DataFrame(data)
        df.to_excel(output, index=False, engine='openpyxl')
        filename = 'movimientos_materiales.xlsx'
    else:
        return jsonify({'error': 'Tipo no válido'}), 400
    output.seek(0)
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ==================== API FOTOS ====================
@app.route('/api/subir_foto', methods=['POST'])
def subir_foto():
    if 'foto' not in request.files:
        return jsonify({'exito': False})
    foto = request.files['foto']
    doc = request.form.get('documento', '')
    if foto and doc:
        try:
            foto.save(os.path.join(base_dir, 'fotos', f"{doc}.jpg"))
            return jsonify({'exito': True})
        except:
            return jsonify({'exito': False})
    return jsonify({'exito': False})

@app.route('/api/ver_foto/<documento>')
def ver_foto(documento):
    path = os.path.join(base_dir, 'fotos', f"{documento}.jpg")
    if os.path.exists(path):
        return send_file(path)
    return '', 404

# ==================== API DASHBOARD ====================
@app.route('/api/dashboard_completo', methods=['GET'])
def dashboard_completo():
    hoy = datetime.now().strftime('%Y-%m-%d')
    fecha_actual = datetime.now()
    
    movimientos_hoy = MovimientoPersonal.query.filter_by(fecha=hoy).all()
    
    personas_con_movimientos_hoy = set()
    for mov in movimientos_hoy:
        personas_con_movimientos_hoy.add(mov.documento)
    personal_hoy = len(personas_con_movimientos_hoy)
    
    movimientos_vehiculos_hoy = MovimientoVehiculo.query.filter_by(fecha=hoy).all()
    vehiculos_con_movimientos_hoy = set()
    for mov in movimientos_vehiculos_hoy:
        vehiculos_con_movimientos_hoy.add(mov.placa)
    vehiculos_hoy = len(vehiculos_con_movimientos_hoy)
    
    materiales_hoy = MovimientoMaterial.query.filter_by(fecha=hoy).count()
    
    todas_las_personas = db.session.query(MovimientoPersonal.documento).distinct().all()
    personal_activo = 0
    for (doc,) in todas_las_personas:
        ultimo_mov = MovimientoPersonal.query.filter_by(documento=doc)\
                     .order_by(MovimientoPersonal.timestamp.desc()).first()
        if ultimo_mov and ultimo_mov.movimiento == 'INGRESO':
            personal_activo += 1
    
    todos_los_vehiculos = db.session.query(MovimientoVehiculo.placa).distinct().all()
    vehiculos_activo = 0
    for (placa,) in todos_los_vehiculos:
        ultimo_mov = MovimientoVehiculo.query.filter_by(placa=placa)\
                     .order_by(MovimientoVehiculo.timestamp.desc()).first()
        if ultimo_mov and ultimo_mov.movimiento == 'INGRESO':
            vehiculos_activo += 1
    
    empresas_dict = {}
    for mov in movimientos_hoy:
        if mov.empresa:
            empresas_dict[mov.empresa] = empresas_dict.get(mov.empresa, 0) + 1
        else:
            empresas_dict['SIN EMPRESA'] = empresas_dict.get('SIN EMPRESA', 0) + 1
    
    if not empresas_dict:
        empresas_dict = {'SIN MOVIMIENTOS HOY': 0}
    
    empresas_labels = list(empresas_dict.keys())
    empresas_datos = list(empresas_dict.values())
    
    movimientos_diarios = []
    fechas = []
    for i in range(6, -1, -1):
        dia = (fecha_actual - timedelta(days=i)).strftime('%Y-%m-%d')
        movs_dia = MovimientoPersonal.query.filter_by(fecha=dia).all()
        personas_dia = set()
        for mov in movs_dia:
            personas_dia.add(mov.documento)
        movimientos_diarios.append(len(personas_dia))
        fechas.append(dia)
    
    ingresos_hoy = 0
    salidas_hoy = 0
    personas_ingresaron = set()
    personas_salieron = set()
    
    for mov in movimientos_hoy:
        if mov.movimiento == 'INGRESO':
            if mov.documento not in personas_ingresaron:
                ingresos_hoy += 1
                personas_ingresaron.add(mov.documento)
        else:
            if mov.documento not in personas_salieron:
                salidas_hoy += 1
                personas_salieron.add(mov.documento)
    
    movimientos_hora = []
    horas = []
    for h in range(0, 24):
        hora_str = f"{h:02d}"
        movs_hora = MovimientoPersonal.query.filter(
            MovimientoPersonal.fecha == hoy,
            MovimientoPersonal.hora.like(f"{hora_str}%")
        ).all()
        personas_hora = set()
        for mov in movs_hora:
            personas_hora.add(mov.documento)
        movimientos_hora.append(len(personas_hora))
        horas.append(f"{hora_str}:00")
    
    return jsonify({
        'tarjetas': {
            'personal_hoy': personal_hoy,
            'vehiculos_hoy': vehiculos_hoy,
            'materiales_hoy': materiales_hoy,
            'personal_activo': personal_activo,
            'vehiculos_activo': vehiculos_activo
        },
        'graficos': {
            'personal_por_empresa': {
                'labels': empresas_labels,
                'datos': empresas_datos
            },
            'movimientos_semana': {
                'labels': fechas,
                'datos': movimientos_diarios
            },
            'ingresos_vs_salidas': {
                'labels': ['Ingresos', 'Salidas'],
                'datos': [ingresos_hoy, salidas_hoy]
            },
            'movimientos_hora': {
                'labels': horas,
                'datos': movimientos_hora
            }
        }
    })

@app.route('/api/equipos_emergencia_detalle', methods=['GET'])
def equipos_emergencia_detalle():
    personal = Personal.query.filter(
        Personal.equipo_emergencia.isnot(None),
        Personal.equipo_emergencia != ''
    ).all()
    return jsonify([{
        'documento': p.documento,
        'nombre': p.nombre_completo,
        'equipo': p.equipo_emergencia,
        'empresa': p.empresa
    } for p in personal])

# ==================== INICIAR ====================
if __name__ == '__main__':
    ip = socket.gethostbyname(socket.gethostname())
    print("="*60)
    print("🏭 SISTEMA DE CONTROL DE ACCESO")
    if ES_RENDER:
        print("🚀 Modo: NUBE (Render)")
    else:
        print("💻 Modo: LOCAL")
    print("="*60)
    print(f"📡 Servidor listo en:")
    print(f"   http://localhost:5001")
    if not ES_RENDER:
        print(f"   http://{ip}:5001")
    print("="*60)
    print(f"🔐 Usuario: admin")
    print(f"🔐 Contraseña: vasconia2026")
    print("="*60)
    
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)