#!/usr/bin/env bash
# Installiert den Service-Report-Formatter als Desktop-Anwendung (Ubuntu/GNOME).
# Erzeugt die .desktop-Verknuepfung mit den korrekten Pfaden des aktuellen
# Nutzers, verankert sie im Anwendungsmenue und (optional) im Dock.
#
# Aufruf:   ./install-app.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ID="service-report-formatter"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$APPS_DIR/$APP_ID.desktop"

mkdir -p "$APPS_DIR"

# launch-gui.sh ausfuehrbar machen
chmod +x "$PROJECT_DIR/launch-gui.sh"

# .desktop-Datei mit den Pfaden dieses Nutzers erzeugen
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Service-Report-Formatter
Comment=Arbeitsnotizen in rechnungsfähige Service-Reports umwandeln
Exec=$PROJECT_DIR/launch-gui.sh
Path=$PROJECT_DIR
Icon=x-office-document
Terminal=false
Categories=Office;
StartupNotify=true
StartupWMClass=ServiceReportFormatter
EOF
chmod +x "$DESKTOP_FILE"

# Menue-Datenbank aktualisieren (Fehler ignorieren)
update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true

echo "Installiert: $DESKTOP_FILE"
echo "Die App erscheint im Anwendungsmenue (Super-Taste -> 'Service')."
echo "Hinweis: Ggf. einmal ab-/anmelden, damit GNOME den Eintrag einliest."
