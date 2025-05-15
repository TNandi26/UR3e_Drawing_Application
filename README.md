## UR Robot Vezérlő Projekt
Ez a projekt egy Universal Robots ipari robotok programozásához és vezérléséhez készült Python keretrendszer. A rendszer különböző interfészeken keresztül teszi lehetővé a robottal való kommunikációt, beleértve a Dashboard szervert, az RTDE (Real-Time Data Exchange) interfészt és a Secondary Client Interface-t.
Funkciók

Robot állapotának lekérdezése
Egyszerű mozgásvezérlés
Rajzolási trajektóriák követése
Programfuttatás, robotvezérlés és monitoring
Valós idejű adatcsere az RTDE protokollon keresztül
Interpreter módú programvégrehajtás
Védő-stop kezelés és helyreállítás

## Rendszerkövetelmények

Python 3.6 vagy újabb
Universal Robots e-Series robot (UR3e, UR5e, UR10e, UR16e) vagy CB-Series (UR3, UR5, UR10) PolyScope 5.10 vagy újabb verzióval
Hálózati kapcsolat a robottal

## Telepítés

1. Klónozd le a repót:
git clone [repo URL]
cd ur-robot-control

2. Állítsd be a robot IP címét és egyéb konfigurációs paramétereket a calibration.json fájlban.

## Főbb komponensek
Dashboard.py
Dashboard szerver interfész a robot rendszerszintű vezérléséhez.
rtdeState.py
RTDE (Real-Time Data Exchange) interfész a robot állapotának valós idejű monitorozásához.
commanding_Interp.py
Interpreter módú vezérlés, amely lehetővé teszi a robot programvégrehajtását.
commanding_RTDE.py
RTDE alapú vezérlés, amely a robot mozgását vezérli a megadott útvonal alapján.
drawing_app.py
Felhasználói alkalmazás, amely lehetővé teszi rajzpályák végrehajtását a robottal.
connector.py
Általános csatlakozási interfész a robottal való kommunikációhoz.
rtdePathRecorder.py
RTDE alapú útvonalrögzítő, amely rögzíti a robot mozgását.
## Használat
Robot állapot ellenőrzése
pythonfrom Dashboard import Dashboard
from rtdeState import RtdeState

# Robot állapotának ellenőrzése Dashboard és RTDE interfészeken keresztül
dash = Dashboard('10.150.0.1')
dash.connect()
robot_mode = dash.sendAndReceive("robotmode")
print(f"Robot mód: {robot_mode}")
dash.close()

# RTDE állapot
rtde_config = 'rtdeState.xml'
state_monitor = RtdeState('10.150.0.1', rtde_config)
state_monitor.initialize()
state = state_monitor.receive()
print(f"Robot futási állapota: {state_monitor.programState.get(state.runtime_state)}")
state_monitor.con.send_pause()
state_monitor.con.disconnect()
Egyszerű mozgásvezérlés
pythonfrom drawing_app import URScriptClient, mm_to_m, move_to_position

client = URScriptClient('10.150.0.1', 30002)
if client.connect():
    # Mozgás a kezdőpozícióba
    home_position = [-37, -295, -42, 2.2, 2.2, 0]
    move_to_position(client, home_position, speed=0.1, acceleration=0.5)
    client.disconnect()
Rajz végrehajtása
python# Használd a drawing_app.py főprogramot
# Válaszd a 2-es menüpontot a rajzoláshoz
Parancsok a Dashboard szerveren
A Dashboard szerver számos parancsot támogat:

robotmode - A robot aktuális üzemmódja
programstate - A robot program állapota
isPowerOn - Jelzi, hogy a robot be van-e kapcsolva
safetystatus - A robot biztonsági állapota
is in remote control - Jelzi, hogy a robot távvezérlés módban van-e
load [program path] - Program betöltése
play - Program indítása
stop - Program leállítása
pause - Program szüneteltetése
shutdown - Robot leállítása
brake release - Fékek kioldása
unlock protective stop - Védőstop feloldása

RTDE használata
Az RTDE (Real-Time Data Exchange) interfész lehetővé teszi a robot valós idejű adatainak elérését és a robot vezérlését.
pythonfrom rtdeState import RtdeState

rtde_config = 'rtdeState.xml'
state_monitor = RtdeState('10.150.0.1', rtde_config)
state_monitor.initialize()

# Adatok fogadása
state = state_monitor.receive()
print(f"Aktuális ízületi pozíciók: {state.actual_q}")

# Kapcsolat bontása
state_monitor.con.send_pause()
state_monitor.con.disconnect()
Kalibrációs fájl (calibration.json)
A calibration.json fájl tartalmazza a robot alapvető konfigurációs beállításait:
json{
    "drawing_surface": -145,
    "home_position": [ -37, -295, -42, 2.2, 2.2, 0],
    "default_speed": 0.1,
    "default_acc": 0.5,
    "robot_ip": "10.150.0.1",
    "robot_port": 30002,
    "rtde_port": 30004,
    "dashboard_port": 29999,
    "blend": 0.001
}
Hibakezelés és helyreállítás
A rendszer képes kezelni a robot védő-stopját és segíteni a helyreállításban:
python# commanding_Interp.py tartalmazza a pStopRecover() funkciót
Megjegyzések

A Secondary Client Interface (port 30002) bináris kommunikációt használ, amely megfelelően van kezelve a kódban.
Az RTDE interfész 500 Hz frekvenciával képes adatokat fogadni a robottól.
A real-time kontroll frekvenciát a frequency paraméterrel lehet beállítani az RTDE inicializálásakor.

## Hibaelhárítás

Kapcsolódási problémák:

Ellenőrizd a robot IP címét a calibration.json fájlban
Ellenőrizd, hogy a robot be van-e kapcsolva és elérhető-e a hálózaton
Ellenőrizd a tűzfalbeállításokat


Védő-stop probléma:

Használd a pStopRecover() funkciót a commanding_Interp.py-ból
Vagy manuálisan oldd fel a védő-stopot a robot vezérlőpanelén


RTDE hibák:

Ellenőrizd, hogy a rtdeState.xml létezik és megfelelően van konfigurálva
Ellenőrizd, hogy a robot támogatja-e az RTDE interfészt (Polyscope 5.10 vagy újabb)



Fejlesztési lehetőségek

Grafikus felhasználói felület
Több robot párhuzamos vezérlése
Bővített hibajavítás és diagnosztika
Trajektória optimalizáció
