from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'asistenciaATO2026'
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE_URL = os.environ.get("DATABASE_URL")

EMPLEADOS_DEFAULT = [
    {"nombre":"EMPLEADO 1","tel":"","jornada":48,"sueldo":1500},
]

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS empleados (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            tel TEXT DEFAULT '',
            jornada FLOAT DEFAULT 48,
            sueldo FLOAT DEFAULT 0,
            pago_hora FLOAT DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id SERIAL PRIMARY KEY,
            fecha TEXT NOT NULL,
            idx TEXT NOT NULL,
            entrada TEXT,
            salida TEXT,
            horas FLOAT,
            uniforme BOOLEAN DEFAULT TRUE,
            UNIQUE(fecha, idx)
        )
    """)
    cur.execute("SELECT COUNT(*) as cnt FROM empleados")
    cnt = cur.fetchone()["cnt"]
    if cnt == 0:
        for e in EMPLEADOS_DEFAULT:
            ph = round(e["sueldo"]/e["jornada"], 2) if e["jornada"] > 0 else 0
            cur.execute("INSERT INTO empleados (nombre, tel, jornada, sueldo, pago_hora) VALUES (%s,%s,%s,%s,%s)",
                       (e["nombre"], e["tel"], e["jornada"], e["sueldo"], ph))
    conn.commit()
    cur.close(); conn.close()
    print("DB Asistencia OK")

def get_empleados_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT nombre, tel, jornada, sueldo, pago_hora FROM empleados ORDER BY id")
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [{"nombre":r["nombre"],"tel":r["tel"] or "","jornada":float(r["jornada"] or 48),
                 "sueldo":float(r["sueldo"] or 0),"pago_hora":float(r["pago_hora"] or 0)} for r in rows]
    except Exception as e:
        print(f"Error get_empleados: {e}")
        return EMPLEADOS_DEFAULT

def save_empleados_db(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM empleados")
    for e in data:
        j = float(e.get("jornada", 48) or 48)
        s = float(e.get("sueldo", 0) or 0)
        ph = round(s/j, 2) if j > 0 else 0
        cur.execute("INSERT INTO empleados (nombre, tel, jornada, sueldo, pago_hora) VALUES (%s,%s,%s,%s,%s)",
                   (e.get("nombre",""), e.get("tel",""), j, s, ph))
    conn.commit()
    cur.close(); conn.close()

def get_registros_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT fecha, idx, entrada, salida, horas, uniforme FROM registros")
        rows = cur.fetchall()
        cur.close(); conn.close()
        result = {}
        for r in rows:
            f, i = str(r["fecha"]), str(r["idx"])
            if f not in result: result[f] = {}
            result[f][i] = {
                "entrada": r["entrada"] or None,
                "salida": r["salida"] or None,
                "horas": float(r["horas"]) if r["horas"] is not None else None,
                "uniforme": bool(r["uniforme"])
            }
        return result
    except Exception as e:
        print(f"Error get_registros: {e}")
        return {}

def upsert_registro(fecha, idx, entrada, salida, horas, uniforme):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO registros (fecha, idx, entrada, salida, horas, uniforme)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (fecha, idx) DO UPDATE SET
            entrada=EXCLUDED.entrada, salida=EXCLUDED.salida,
            horas=EXCLUDED.horas, uniforme=EXCLUDED.uniforme
    """, (str(fecha), str(idx), entrada or None, salida or None, horas, uniforme))
    conn.commit()
    cur.close(); conn.close()

def delete_registro(fecha, idx):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM registros WHERE fecha=%s AND idx=%s", (str(fecha), str(idx)))
    conn.commit()
    cur.close(); conn.close()

def hoy(): return datetime.now().strftime("%Y-%m-%d")
def sumar(h, mins):
    hh, mm = map(int, h.split(":"))
    return (datetime(2000,1,1,hh,mm)+timedelta(minutes=mins)).strftime("%H:%M")

try: init_db()
except Exception as e: print(f"Error init_db: {e}")

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/empleados", methods=["GET"])
def get_empleados(): return jsonify(get_empleados_db())

@app.route("/api/empleados", methods=["POST"])
def save_empleados():
    save_empleados_db(request.json)
    socketio.emit("empleados_updated", {})
    return jsonify({"ok": True})

@app.route("/api/registros/todos", methods=["GET"])
def get_todos(): return jsonify(get_registros_db())

@app.route("/api/checkin", methods=["POST"])
def checkin():
    d = request.json
    idx = str(d["idx"]); hora = d["hora"]
    fecha = d.get("fecha", hoy())
    uniforme = d.get("uniforme", True)
    upsert_registro(fecha, idx, hora, None, None, uniforme)
    socketio.emit("checkin_nuevo", {"idx": idx, "fecha": fecha})
    return jsonify({"ok": True})

@app.route("/api/checkout", methods=["POST"])
def checkout():
    d = request.json
    idx = str(d["idx"]); fecha = d.get("fecha", hoy())
    reg = get_registros_db()
    entrada = (reg.get(fecha, {}).get(idx, {}) or {}).get("entrada", "")
    uniforme = (reg.get(fecha, {}).get(idx, {}) or {}).get("uniforme", True)
    upsert_registro(fecha, idx, entrada, d["salida"], d["horas"], uniforme)
    socketio.emit("checkout_nuevo", {"idx": idx, "fecha": fecha})
    return jsonify({"ok": True})

@app.route("/api/checkin/<idx>", methods=["DELETE"])
def del_checkin(idx):
    fecha = request.args.get("fecha", hoy())
    delete_registro(fecha, idx)
    socketio.emit("checkin_borrado", {"idx": idx})
    return jsonify({"ok": True})

@app.route("/api/editar", methods=["POST"])
def editar():
    d = request.json
    idx = str(d["idx"]); fo = d["fecha_orig"]; fn = d["fecha_nueva"]
    entrada = d["entrada"]; salida = d.get("salida", "")
    horas = None
    reg = get_registros_db()
    uniforme = (reg.get(fo, {}).get(idx, {}) or {}).get("uniforme", True)
    if salida and entrada:
        try:
            hh1,mm1 = map(int, entrada.split(":")); hh2,mm2 = map(int, salida.split(":"))
            mins = (hh2*60+mm2)-(hh1*60+mm1); horas = round(mins/60, 2)
        except: pass
    delete_registro(fo, idx)
    upsert_registro(fn, idx, entrada, salida or None, horas, uniforme)
    socketio.emit("registro_editado", {})
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
