# UR Robot Vezérlő Projekt

Ez a projekt egy Universal Robots ipari robotok programozásához és vezérléséhez készült Python keretrendszer. A rendszer különböző interfészeken keresztül teszi lehetővé a robottal való kommunikációt, beleértve a Dashboard szervert, az RTDE (Real-Time Data Exchange) interfészt és a Secondary Client Interface-t.

## Funkciók

- Robot állapotának lekérdezése
- Egyszerű mozgásvezérlés
- Rajzolási trajektóriák követése
- Programfuttatás, robotvezérlés és monitoring
- Valós idejű adatcsere az RTDE protokollon keresztül
- Interpreter módú programvégrehajtás
- Védő-stop kezelés és helyreállítás

## Rendszerkövetelmények

- Python 3.6 vagy újabb
- Universal Robots e-Series robot (UR3e, UR5e, UR10e, UR16e) vagy CB-Series (UR3, UR5, UR10) PolyScope 5.10 vagy újabb verzióval
- Hálózati kapcsolat a robottal

## Telepítés

1. Klónozd le a repót: git clone ...

   Elnézést a problémákért. Hadd próbáljam meg helyesen, a megfelelő formázással. A szöveget közvetlenül ide másolom, hogy pontosan azt lásd, amit a README.md fájlba kell tenned:
# UR Robot Vezérlő Projekt

Ez a projekt egy Universal Robots ipari robotok programozásához és vezérléséhez készült Python keretrendszer. A rendszer különböző interfészeken keresztül teszi lehetővé a robottal való kommunikációt, beleértve a Dashboard szervert, az RTDE (Real-Time Data Exchange) interfészt és a Secondary Client Interface-t.

## Funkciók

- Robot állapotának lekérdezése
- Egyszerű mozgásvezérlés
- Rajzolási trajektóriák követése
- Programfuttatás, robotvezérlés és monitoring
- Valós idejű adatcsere az RTDE protokollon keresztül
- Interpreter módú programvégrehajtás
- Védő-stop kezelés és helyreállítás

## Rendszerkövetelmények

- Python 3.6 vagy újabb
- Universal Robots e-Series robot (UR3e, UR5e, UR10e, UR16e) vagy CB-Series (UR3, UR5, UR10) PolyScope 5.10 vagy újabb verzióval
- Hálózati kapcsolat a robottal

## Telepítés

1. Klónozd le a repót:
git clone [repo URL]
cd ur-robot-control

2. Állítsd be a robot IP címét és egyéb konfigurációs paramétereket a `calibration.json` fájlban.

## Főbb komponensek

### Dashboard.py
Dashboard szerver interfész a robot rendszerszintű vezérléséhez.

### rtdeState.py
RTDE (Real-Time Data Exchange) interfész a robot állapotának valós idejű monitorozásához.

### commanding_Interp.py
Interpreter módú vezérlés, amely lehetővé teszi a robot programvégrehajtását.

### commanding_RTDE.py
RTDE alapú vezérlés, amely a robot mozgását vezérli a megadott útvonal alapján.

### drawing_app.py
Felhasználói alkalmazás, amely lehetővé teszi rajzpályák végrehajtását a robottal.

### connector.py
Általános csatlakozási interfész a robottal való kommunikációhoz.

### rtdePathRecorder.py
RTDE alapú útvonalrögzítő, amely rögzíti a robot mozgását.

## Használat

### Robot állapot ellenőrzése

```python
from Dashboard import Dashboard
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
```
## Egyszerű mozgásvezérlés

```python
from drawing_app import URScriptClient, mm_to_m, move_to_position

client = URScriptClient('10.150.0.1', 30002)
if client.connect():
    # Mozgás a kezdőpozícióba
    home_position = [-37, -295, -42, 2.2, 2.2, 0]
    move_to_position(client, home_position, speed=0.1, acceleration=0.5)
    client.disconnect()
```

## RTDE használata

```python
from rtdeState import RtdeState

rtde_config = 'rtdeState.xml'
state_monitor = RtdeState('10.150.0.1', rtde_config)
state_monitor.initialize()

# Adatok fogadása
state = state_monitor.receive()
print(f"Aktuális ízületi pozíciók: {state.actual_q}")

# Kapcsolat bontása
state_monitor.con.send_pause()
state_monitor.con.disconnect()
```

## Kalibrációs fájl

```json
{
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
```

## Fejlesztési lehetőségek
1. Grafikus felhasználói felület
2. Kamera integrálása
3. Bővített hibajavítás és diagnosztika
4. Trajektória optimalizáció
