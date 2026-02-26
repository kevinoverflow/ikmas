# Aufgabenvorschläge aus Code-Review

## 1) Aufgabe: Tippfehler korrigieren

**Fundstelle**
- In `app/rag/ingest.py` wird bei hochgeladenen Dateien `getValue()` aufgerufen.

**Problem**
- Bei Streamlit-`UploadedFile` lautet die Methode `getvalue()` (kleines `v`). Das aktuelle `getValue()` wirkt wie ein Tippfehler im Methodennamen.

**Vorschlag für die Aufgabe**
- Ersetze `f.getValue()` durch `f.getvalue()` in `ingest_uploads`.
- Ergänze eine kurze Regressionsprüfung, dass `ingest_uploads` mit einem `UploadedFile`-ähnlichen Objekt funktioniert.

**Akzeptanzkriterien**
- Ingest stürzt bei gültigen Uploads nicht wegen `AttributeError` ab.
- Ein Test deckt den korrekten Methodenaufruf explizit ab.

---

## 2) Aufgabe: Programmierfehler beheben

**Fundstelle**
- In `app/rag/ingest.py` werden Exceptions in der Upload-Schleife pauschal geschluckt.

**Problem**
- Durch den fehlerhaften Methodenaufruf (`getValue`) werden alle Uploads in `errors` gezählt, ohne dass der eigentliche Fehler sichtbar wird. Das macht den Defekt schwer auffindbar und führt zu stillschweigendem Funktionsausfall.

**Vorschlag für die Aufgabe**
- Fehlerbehandlung in `ingest_uploads` so verbessern, dass Fehlerursachen protokolliert oder gesammelt zurückgegeben werden (z. B. `stats["error_messages"]`).
- Optional: nur erwartbare Fehler gezielt abfangen statt blanket `except Exception`.

**Akzeptanzkriterien**
- Bei Fehlern ist die Ursache im Rückgabewert oder Log nachvollziehbar.
- Ein fehlerhafter Upload verhindert nicht die Verarbeitung weiterer Dateien.

---

## 3) Aufgabe: Kommentar-/Doku-Unstimmigkeit korrigieren

**Fundstelle**
- `README.md` beschreibt den Start über `./run.sh`, erwähnt aber nicht, dass `SCADS_API_KEY` benötigt wird.
- `run.sh` fordert den Key interaktiv an, falls er fehlt.

**Problem**
- Nutzer:innen bekommen die zentrale Voraussetzung (API-Key) nicht frühzeitig aus der Doku mit. In nicht-interaktiven Umgebungen ist das besonders problematisch.

**Vorschlag für die Aufgabe**
- `README.md` um einen klaren Abschnitt „Voraussetzungen“ ergänzen:
  - `SCADS_API_KEY` setzen (inkl. Beispiel `export SCADS_API_KEY=...`).
  - Hinweis auf nicht-interaktive Umgebungen.

**Akzeptanzkriterien**
- README enthält eine explizite, reproduzierbare Anleitung zum Setzen des API-Keys vor dem Start.
- Das Verhalten von `run.sh` ist in der Doku verständlich erklärt.

---

## 4) Aufgabe: Testqualität verbessern

**Fundstelle**
- Es gibt aktuell keine automatisierten Tests für Upload-Storage/Ingest-Edgecases.

**Problem**
- Wichtige Pfade wie Deduplizierung, Namenskonflikt-Strategien (`skip/replace/rename`) und Fehlerfälle sind ungesichert.

**Vorschlag für die Aufgabe**
- Einführung von `pytest`-Tests für:
  1. `save_upload` (identische Datei, Namenskonflikt, rename/replace).
  2. `delete_file` und `get_file_path`.
  3. `ingest_uploads` mit minimalem Mock für Upload-Objekte.
- Tests gegen temporäre Verzeichnisse laufen lassen (Monkeypatch für `UPLOAD_DIR`).

**Akzeptanzkriterien**
- Test-Suite deckt alle Konfliktpfade von `save_upload` ab.
- Ein Regressionstest verhindert Wiederauftreten des `getvalue`-Fehlers.
