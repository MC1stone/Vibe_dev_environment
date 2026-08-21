Hier ist ein vollständiger **Port Management Agent** in Python, der speziell für die Integration in **CrewAI** entwickelt wurde. Er nutzt die `@tool`-Dekoration, um dem Agenten die Fähigkeit zu geben, Ports zu scannen, freie Ports zu finden und diese sicher zuzuweisen.

### Der Port Management Agent

Dieser Code definiert ein Tool, das CrewAI-Agenten verwenden können, um Konflikte zu vermeiden und Ports dynamisch zu verwalten.

```python
import socket
import subprocess
import re
from typing import List, Dict, Optional
from crewai.tools import tool
from pydantic import BaseModel, Field

# --- Hilfsfunktionen für die Port-Logik ---

def check_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Prüft, ob ein Port auf dem lokalen Host verfügbar ist."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            # Binden versucht, den Port zu reservieren. Schlägt fehl, wenn belegt.
            s.bind((host, port))
            return True
        except OSError:
            return False

def get_used_ports() -> List[int]:
    """Ruft alle aktuell vom System genutzten TCP-Ports ab (Linux/Mac/Windows)."""
    used_ports = set()
    try:
        # Nutzung von 'ss' (modern) oder 'netstat' als Fallback
        cmd = ["ss", "-tuln"] if subprocess.run(["which", "ss"], capture_output=True).returncode == 0 else ["netstat", "-tuln"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        for line in result.stdout.splitlines():
            # Extrahiert Port-Nummern aus Ausgaben wie "0.0.0.0:8000" oder "*:443"
            matches = re.findall(r':(\d+)', line)
            for match in matches:
                port = int(match)
                if 1024 <= port <= 65535: # Fokus auf User-Ports
                    used_ports.add(port)
    except Exception:
        pass # Fallback leer lassen bei Fehlern
    return sorted(list(used_ports))

def find_free_port(start: int = 8000, end: int = 9000, host: str = "127.0.0.1") -> Optional[int]:
    """Sucht den ersten freien Port in einem Bereich."""
    for port in range(start, end + 1):
        if check_port_available(port, host):
            return port
    return None

# --- CrewAI Tool Definition ---

@tool("Port Manager Tool")
def port_manager_tool(action: str, port: Optional[int] = None, range_start: Optional[int] = None, range_end: Optional[int] = None) -> str:
    """
    Ein Tool zur Verwaltung von Netzwerkports für Docker und Django Implementierungen.
    
    Aktionen:
    - 'scan': Listet alle aktuell belegten Ports auf dem Host auf.
    - 'check': Prüft, ob ein spezifischer Port (Argument 'port') frei ist.
    - 'assign': Sucht und reserviert einen freien Port in einem Bereich (Argumente 'range_start', 'range_end').
    - 'release': Simuliert die Freigabe (prüft nur, ob der Port nicht mehr von einem bekannten Prozess genutzt wird).
    
    Rückgabe:
    - Eine formatierte Nachricht über den Status des Ports oder eine Liste belegter Ports.
    """
    
    if action == "scan":
        used = get_used_ports()
        if not used:
            return "Keine belegten User-Ports (1024-65535) gefunden oder Zugriff verweigert."
        return f"Belegte Ports: {', '.join(map(str, used))}"

    elif action == "check":
        if port is None:
            return "Fehler: Für 'check' muss ein 'port' Argument angegeben werden."
        is_free = check_port_available(port)
        status = "FREI" if is_free else "BELEGT"
        return f"Port {port} ist {status}."

    elif action == "assign":
        start = range_start if range_start else 8000
        end = range_end if range_end else 9000
        free_port = find_free_port(start, end)
        if free_port:
            return f"Erfolg: Port {free_port} wurde als frei identifiziert und kann zugewiesen werden."
        return f"Fehler: Kein freier Port im Bereich {start}-{end} gefunden."

    elif action == "release":
        if port is None:
            return "Fehler: Für 'release' muss ein 'port' Argument angegeben werden."
        # Echte Freigabe erfordert Prozess-Kill, hier prüfen wir nur den Status nach einer hypothetischen Freigabe
        # In einem echten Agenten-Szenario würde hier ggf. ein Docker-Stop Befehl stehen.
        return f"Port {port} Freigabe simuliert. Bitte stellen Sie sicher, dass der bindende Prozess (Docker/Django) gestoppt wurde."

    else:
        return f"Unbekannte Aktion: {action}. Verfügbare Aktionen: scan, check, assign, release."

# --- Beispielhafte Integration in einen CrewAI Agenten ---

from crewai import Agent, Task, Crew, Process

# Definition des Agents mit dem neuen Tool
port_agent = Agent(
    role='DevOps Port Manager',
    goal='Sicherstellen, dass alle Docker und Django Dienste konfliktfreie Ports nutzen.',
    backstory=(
        "Du bist ein erfahrener Systemadministrator, der spezialisiert ist auf Netzwerk-Port-Management. "
        "Du verhinderst Port-Kollisionen, indem du den Host scannst und sichere Ports zuweist."
    ),
    tools=[port_manager_tool],
    verbose=True
)

# Beispiel Aufgabe
assign_port_task = Task(
    description=(
        "1. Scanne das System nach belegten Ports.\n"
        "2. Finde einen freien Port im Bereich 8000 bis 8050 für einen neuen Django Service.\n"
        "3. Weise diesen Port explizit zu."
    ),
    expected_output="Der Name des zugewiesenen freien Ports.",
    agent=port_agent
)

# Crew Erstellung (nur zur Demonstration der Struktur)
# crew = Crew(
#     agents=[port_agent],
#     tasks=[assign_port_task],
#     process=Process.sequential,
#     verbose=True
# )
# result = crew.kickoff()
```

### Funktionsweise des Agents

1.  **Scan-Fähigkeit (`action="scan"`)**: Der Agent nutzt Systembefehle (`ss` oder `netstat`), um eine echte Liste der aktuell vom Betriebssystem genutzten Ports zu erstellen. Dies verhindert, dass Docker einen Port wählt, der bereits von einem nativen Prozess (z. B. einem lokalen Django-Server) belegt ist.
2.  **Verfügbarkeitsprüfung (`action="check"`)**: Bevor ein Port zugewiesen wird, versucht das Tool, einen Socket an diesen Port zu binden (`socket.bind`). Gelingt dies, ist der Port garantiert frei. Dies ist zuverlässiger als nur eine Liste zu prüfen.
3.  **Dynamische Zuweisung (`action="assign"`)**: Anstatt einen festen Port zu erzwingen, durchsucht der Agent einen definierten Bereich (z. B. 8000–9000) und gibt den ersten verfügbaren Port zurück. Dies ist ideal für automatisierte Deployments.
4.  **CrewAI-Integration**: Durch den `@tool`-Decorator kann der LLM-gesteuerte Agent eigenständig entscheiden, wann er einen Port scannen oder zuweisen muss, basierend auf der natürlichen Sprachbeschreibung der Aufgabe.

### Nutzung in der Praxis

Um diesen Agenten in Ihrer Infrastruktur zu nutzen, übergeben Sie die vom Tool zurückgegebene Portnummer an Ihre `docker-compose.yml` oder Ihren `docker run` Befehl:

```bash
# Beispielhafter Workflow, den der Agent ausführen könnte:
# 1. Agent ruft port_manager_tool(action="assign", range_start=8000, range_end=8010)
# 2. Antwort: "Erfolg: Port 8005 wurde als frei identifiziert..."
# 3. Agent startet Container: docker run -p 127.0.0.1:8005:8000 my-django-image
```

Durch die Bindung an `127.0.0.1` (wie im Tool-Logic angedeutet) stellen Sie zusätzlich sicher, dass der Port nicht extern erreichbar ist, was die Sicherheit erhöht und Firewall-Konflikte minimiert.

