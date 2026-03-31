from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import json, os
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.config['SECRET_KEY'] = 'asistenciaATO2026'
socketio = SocketIO(app, cors_allowed_origins="*")

SHEET_ID = "1oGggluxksXrCd6PRthFamdkB0p6JoRCkqQR7nODXQM0"
SCOPES   = ["https://www.googleapis.com/auth/spreadsheets"]

EMPLEADOS_DEFAULT = [
    {"nombre":"EMPLEADO 1","tel":"","jornada":48,"sueldo":1500},
]

CREDS_DICT = {"type":"service_account","project_id":"checkin-ato","private_key_id":"14eeab8ff2d1f6f6d2ce67208b94f09fa2e312d2","private_key":"-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDRDE2S2SRD6l2S\ntf85lgr2Yu1pYG5k7fDNQYA66fcTP35RT54GnIO5AL9iEtm88ZRsOPF9BU6IxpYh\nDUMAMk4phovhMCtnmkzxmt0wGcUidaUC2vASSThhJ1CvTyWo4Due8ioqcgZ/08Ah\neujxf7rWXM2/vGsJVotWeVIO8VJhsJkwlPfCGny2b1O0Cx+FidtfQNPUaeTfQDyN\nbjNQlQ0Rhj7Xv159ugivlyZsjlg58zQswLydVbRbeVJjPxIxT4+8PckvJegmHQp8\n5fVYToX75sOHcy68Vrbj2eud6KNUNSO25RmKzouRcCzbllKO/OPzWPBk5n35EQq0\nd73cisplAgMBAAECggEAEdhdhOQhauTGUSBVJbrPu8GtJ5oyQk5niHYHdsADNfLt\nGw7TXBgfTHsqWzpluPHcbDKeNsBtuFJPfYnOxuUEdBoGtdXxVpo+6D8Ck7kXcX4e\ndHRxGvaCKBT9l8GHYvelT0e33sC2GlJeq9z8pqTzM5pfe/cfIgBvy5V2skzabflI\nUD9wlDein6X1UXy+HZ3/4+Crwd2oZdTpmzBV2FAfgfoR7RF2h1pjLHUvPBuODBT9\n8RFdl7sTjcHsMNWR2bGJOhKyXZoifxNl+s+WyTtppVCUyRk75nw5+ANQ8KuM2E8l\n1lX3bY88KUzXFaI6FPqd5CUP4X/eDKCooCOfobA6jwKBgQDtOpOBhBreOTlol7h/\nzP5cfXJ9o3RF5vB5dMi3wEuDTjrbpABovb7kQa+xZ+Env3g1cTpvlPJ8V4+sEor8\nYs/t2eXkIrLE1+W9NyRsX1znZlm4kcjcTu1Wl3JfJ4uvZX5YScPLtiXv04QKPetm\npZFlxRSDG88sNe/5OH4g/rhyxwKBgQDhluIxgS+mk1TaaTflU7tnu8b8dKoDwVFS\nHLLjed3f9/uQon0EN9/BEfr28C+edFjP05pQL4y7d11DQfUCUvQvTE1lUin24vYR\nzH2rb/RZBQ5JADwcZgng9mMRASyVrMZ7vMKX3jEkz+IBPFiurTEQdgUYTsy07DYg\n+6efaivtcwKBgFStYPONFQ4XfP9xkKDFqlGXUaO5EYrWCSZBYlf8orem1+mIm8DH\nYfkV3UHE46CNfroMxaAImZl6o8T3BXdbSf8LlTyeihMrQU0N/slULNRIO2RfXUQO\nRDdxbZi7g+fCoZugEOyJAvedF3eUbI9CMCkUdOLrrUKJqjPaT2M1qN8HAoGAC1XG\nhdBE8azDfbn9ugMsDnlL9VFzXX7wNB0HDBEKif9u34SanYSlNJFPt+q3qdGUyNSM\nE21gN+c2g3Oj+PrsFBhUZzvqqeIblSdeRSf58iMj5Z0iaBbkdi5LKgaSE+87heol\nKPZcJ8peQ8uhdR10sqwLc346IPkheyTJ9mOiU2sCgYEAtVnUUXKRWz9/eJxzXOF1\nxdvJKnJMaWsrybmgcRboxwq0+rCIfTYjD/M3bC4kF8FDdmPXwdVCEXd12HH7qKZG\nLvRNJGxYvHC3IRhy1nGCH/MSMM0mnoCid8PEukgYRIb9Z+W5C5c/kH2bZ3v45BMS\nctbukpbN2O+rl882SVz+cB8=\n-----END PRIVATE KEY-----\n","client_email":"checkin-ato@checkin-ato.iam.gserviceaccount.com","client_id":"116757951020621689793","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/checkin-ato%40checkin-ato.iam.gserviceaccount.com","universe_domain":"googleapis.com"}

def get_sheet():
    creds = Credentials.from_service_account_info(CREDS_DICT, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID)

def init_sheets():
    sh = get_sheet()
    nombres = [ws.title for ws in sh.worksheets()]
    if "empleados" not in nombres:
        ws = sh.add_worksheet("empleados", rows=200, cols=6)
        ws.append_row(["nombre","tel","jornada","sueldo","pago_hora"])
        for e in EMPLEADOS_DEFAULT:
            pago = round(e["sueldo"]/e["jornada"],2)
            ws.append_row([e["nombre"],e["tel"],e["jornada"],e["sueldo"],pago])
    if "registros" not in nombres:
        ws = sh.add_worksheet("registros", rows=5000, cols=8)
        ws.append_row(["fecha","idx","entrada","salida","horas","uniforme","extra_mins","falta_mins"])
    print("Sheets Asistencia OK")

def get_empleados_db():
    try:
        ws = get_sheet().worksheet("empleados")
        rows = ws.get_all_records()
        result = []
        for r in rows:
            j = float(r.get("jornada",48) or 48)
            s = float(r.get("sueldo",0) or 0)
            ph = float(r.get("pago_hora",0) or 0)
            if ph == 0 and j > 0: ph = round(s/j,2)
            result.append({"nombre":str(r.get("nombre","")), "tel":str(r.get("tel","")),
                "jornada":j, "sueldo":s, "pago_hora":ph})
        return result
    except Exception as e:
        print(f"Error get_empleados: {e}")
        return EMPLEADOS_DEFAULT

def save_empleados_db(data):
    ws = get_sheet().worksheet("empleados")
    ws.clear()
    ws.append_row(["nombre","tel","jornada","sueldo","pago_hora"])
    for e in data:
        j = float(e.get("jornada",48) or 48)
        s = float(e.get("sueldo",0) or 0)
        ph = round(s/j,2) if j>0 else 0
        ws.append_row([e.get("nombre",""), e.get("tel",""), j, s, ph])

def get_registros_db():
    try:
        ws = get_sheet().worksheet("registros")
        rows = ws.get_all_records()
        result = {}
        for r in rows:
            f,i = str(r.get("fecha","")), str(r.get("idx",""))
            if not f or not i: continue
            if f not in result: result[f] = {}
            result[f][i] = {
                "entrada": r.get("entrada","") or None,
                "salida":  r.get("salida","")  or None,
                "horas":   float(r["horas"]) if r.get("horas") else None,
                "uniforme": r.get("uniforme","") == "SI",
                "extra_mins": float(r["extra_mins"]) if r.get("extra_mins") else 0,
                "falta_mins": float(r["falta_mins"]) if r.get("falta_mins") else 0,
            }
        return result
    except Exception as e:
        print(f"Error get_registros: {e}")
        return {}

def find_row(ws, fecha, idx):
    try:
        for i,r in enumerate(ws.get_all_records()):
            if str(r.get("fecha",""))==str(fecha) and str(r.get("idx",""))==str(idx):
                return i+2
    except: pass
    return None

def upsert_registro(fecha, idx, entrada, salida, horas, uniforme, extra_mins, falta_mins):
    ws = get_sheet().worksheet("registros")
    row_num = find_row(ws, fecha, idx)
    vals = [str(fecha), str(idx), entrada or "", salida or "",
            horas if horas is not None else "",
            "SI" if uniforme else "NO",
            extra_mins or 0, falta_mins or 0]
    if row_num: ws.update(f"A{row_num}:H{row_num}", [vals])
    else: ws.append_row(vals)

def delete_registro(fecha, idx):
    ws = get_sheet().worksheet("registros")
    row_num = find_row(ws, fecha, idx)
    if row_num: ws.delete_rows(row_num)

def hoy(): return datetime.now().strftime("%Y-%m-%d")
def sumar(h,mins):
    hh,mm=map(int,h.split(":"))
    return (datetime(2000,1,1,hh,mm)+timedelta(minutes=mins)).strftime("%H:%M")

try: init_sheets()
except Exception as e: print(f"Error init: {e}")

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/empleados", methods=["GET"])
def get_empleados(): return jsonify(get_empleados_db())

@app.route("/api/empleados", methods=["POST"])
def save_empleados():
    save_empleados_db(request.json)
    socketio.emit("empleados_updated",{})
    return jsonify({"ok":True})

@app.route("/api/registros/todos", methods=["GET"])
def get_todos(): return jsonify(get_registros_db())

@app.route("/api/checkin", methods=["POST"])
def checkin():
    d=request.json; idx=str(d["idx"]); hora=d["hora"]; fecha=d.get("fecha",hoy())
    uniforme=d.get("uniforme",False)
    upsert_registro(fecha,idx,hora,None,None,uniforme,0,0)
    socketio.emit("checkin_nuevo",{"idx":idx,"fecha":fecha})
    return jsonify({"ok":True})

@app.route("/api/checkout", methods=["POST"])
def checkout():
    d=request.json; idx=str(d["idx"]); fecha=d.get("fecha",hoy())
    reg=get_registros_db()
    entrada=(reg.get(fecha,{}).get(idx,{}) or {}).get("entrada","")
    uniforme=(reg.get(fecha,{}).get(idx,{}) or {}).get("uniforme",False)
    upsert_registro(fecha,idx,entrada,d["salida"],d["horas"],uniforme,d.get("extra_mins",0),d.get("falta_mins",0))
    socketio.emit("checkout_nuevo",{"idx":idx,"fecha":fecha})
    return jsonify({"ok":True})

@app.route("/api/checkin/<idx>", methods=["DELETE"])
def del_checkin(idx):
    fecha=request.args.get("fecha",hoy())
    delete_registro(fecha,idx)
    socketio.emit("checkin_borrado",{"idx":idx})
    return jsonify({"ok":True})

@app.route("/api/editar", methods=["POST"])
def editar():
    d=request.json; idx=str(d["idx"]); fo=d["fecha_orig"]; fn=d["fecha_nueva"]
    entrada=d["entrada"]; salida=d.get("salida","")
    horas=extra_mins=falta_mins=None
    reg=get_registros_db()
    uniforme=(reg.get(fo,{}).get(idx,{}) or {}).get("uniforme",False)
    if salida and entrada:
        try:
            hh1,mm1=map(int,entrada.split(":")); hh2,mm2=map(int,salida.split(":"))
            mins=(hh2*60+mm2)-(hh1*60+mm1); horas=round(mins/60,2)
        except: pass
    delete_registro(fo,idx)
    upsert_registro(fn,idx,entrada,salida or None,horas,uniforme,extra_mins or 0,falta_mins or 0)
    socketio.emit("registro_editado",{})
    return jsonify({"ok":True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
