# copy-spotlight-images

Python-Skript, das die Windows-Spotlight-Bilder (Sperrbildschirm-Hintergründe) aus dem
versteckten Ordner des ContentDeliveryManagers in einen eigenen Bilderordner kopiert.

## Funktionen

- Kopiert nur Bilder im **Querformat** mit mindestens **1920 Pixel Breite**.
- Benennt die Kopien um in `Asset_Image_<YYYY-MM-DD>_<Nr>.jpg` (Kopierdatum, laufende Nummer pro Tag).
  Die Dateiendung richtet sich nach dem tatsächlichen Bildformat.
- Erkennt bereits kopierte Bilder am **Inhalt** (SHA-256), auch wenn sie im Zielordner
  umbenannt oder in Unterordner verschoben wurden.
- Überspringt beschädigte oder unvollständige Bilder.
- Protokolliert alles in `copy_assets.log` neben dem Skript; Einträge älter als 60 Tage
  werden automatisch entfernt.

## Voraussetzungen

- Windows 10/11 mit aktiviertem Windows-Blickpunkt (Spotlight)
- Python 3.10 oder neuer
- [Pillow](https://pypi.org/project/pillow/):

  ```
  pip install pillow
  ```

## Konfiguration

Die Einstellungen stehen als Konstanten am Anfang von `copy_assets.py`:

| Konstante            | Bedeutung                                   |
|----------------------|---------------------------------------------|
| `SOURCE_DIR`         | Spotlight-Assets-Ordner                     |
| `TARGET_DIR`         | Zielordner für die Bilder                   |
| `MIN_WIDTH`          | Mindestbreite in Pixel (Standard 1920)      |
| `NAME_PREFIX`        | Präfix der Dateinamen (`Asset_Image_`)      |
| `LOG_RETENTION_DAYS` | Aufbewahrungsdauer der Logeinträge in Tagen |

`SOURCE_DIR` und `TARGET_DIR` enthalten einen Benutzernamen und müssen an das eigene
System angepasst werden.

## Automatisch bei der Anmeldung ausführen

Geplante Aufgabe in PowerShell anlegen (Pfade anpassen):

```powershell
$action = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument '"C:\Pfad\zu\copy_assets.py"'
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$trigger.Delay = "PT1M"
Register-ScheduledTask -TaskName "Copy Spotlight Assets" -Action $action -Trigger $trigger
```

`pythonw.exe` startet das Skript ohne Konsolenfenster.
