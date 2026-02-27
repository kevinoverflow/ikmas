# IKMAS

## Intelligent Knowledge Management Assistance System

**IKMAS (Intelligent Knowledge Management Assistance System in Collaborative Scenarios)** ist ein forschungsorientierter Open-Source-Prototyp zur Unterstützung wissensintensiver Prozesse in Arbeitsgruppen.

Das Projekt schlägt eine methodische Brücke zwischen etablierter Wissensmanagement-Theorie und modernen technischen Möglichkeiten der generativen Künstlichen Intelligenz (GenAI).  
Im Zentrum steht die theoriegeleitete Integration von KI-Assistenzfunktionen, basierend auf der Kombination des **SECI-Modells (Wissensentstehung)** und der **Knowledge Reuse Theory (Wissenswiederverwendung)**.

---

## 🚀 Kernkonzept

Das System ist darauf ausgelegt, **16 spezifische GenAI-Rollen** abzubilden, die den Wissensaustausch zwischen unterschiedlichen Akteuren (z. B. Expert:innen, Noviz:innen, Teams) fördern.

**Beispiele:**

- **Digital Memory Agent (SWP × Socialization)**  
  Bewahrung des flüchtigen Kontexts aus Team-Diskussionen.

- **Expert Proxy Agent (SWPr × Socialization)**  
  Skalierung von Expertenwissen durch dialogfähige Avatare.

- **Mentor Agent (ESN × Socialization)**  
  Übersetzung von Fachterminologie für Einsteiger:innen.

- **Concept Mining Agent (SKM × Combination)**  
  Identifikation abstrakter Muster in unstrukturierten Daten.

---

## 🛠 Technische Architektur

Der Prototyp nutzt einen **RAG-basierten Architekturansatz (Retrieval-Augmented Generation)**, um kontextspezifisches Wissen aus lokalen Dokumenten nutzbar zu machen.

Die Implementierung setzt auf Open-Source-Technologien wie:

- **[ChromaDB](https://www.trychroma.com/)** (Vektordatenbank)
- [ScaDS.ai](https://scads.ai/) **LLMs**

### MVP API Highlights (v1)

- `POST /v1/chat` now supports hybrid mode control via `mode_override` (`AUTO|SWP|ESN|SKM`).
- `POST /v1/router/preview` returns router decisions (mode distance, SECI state, role, retrieval policy) without an LLM call.
- Chat responses include:
  - schema-first `data`
  - `citations` + `why_sources`
  - `router` metadata
  - `retrieval.policy_applied`
  - validation incl. `citation_coverage`

---

## 📂 Projektstruktur

```bash
.
├── app
│   ├── infrastructure/      # System-Konfiguration
│   ├── rag/                 # Kernlogik (Ingest, Retriever, Reranker, Vectorstore)
│   └── ui/                  # Benutzeroberfläche (Streamlit)
├── data
│   ├── chroma/              # Persistente Vektordatenbank
│   └── uploads/             # Dokumentenspeicher (PDFs)
├── tokenizers/              # Lokale Embedding-Modelle (Qwen3-Embedding-4B)
├── requirements.txt         # Python-Abhängigkeiten
└── run.sh                   # Start-Skript
```

---

## 📖 Methodik

Die Entwicklung folgt dem **Design-Science-Research-Ansatz**.

Anforderungen wurden durch:

- quantitative Umfragen
- qualitative Expert:inneninterviews

ermittelt, um den wahrgenommenen Mehrwert des IKMAS zu sichern.

---

## 🛠 Installation & Start

### Voraussetzungen

- Python 3.10+
- Eine gesetzte API-Variable: `SCADS_API_KEY` (alternativ `OPENAI_API_KEY`)

Beispiel:

```bash
export SCADS_API_KEY="<dein_key>"
```

> Hinweis: `run.sh` fragt den Schlüssel interaktiv ab, falls er nicht gesetzt ist. In CI-/nicht-interaktiven Umgebungen sollte der Key daher **vorher** als Umgebungsvariable gesetzt werden.

1. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

2. Dokumente bereitstellen:

- Dokumente können bequem über die **Streamlit-Oberfläche** hochgeladen werden.
- Der Ordner `data/uploads/default` dient dabei als **Speicherort** für hochgeladene Dateien.

3. Anwendung starten:

```bash
./run.sh
```

---

## Förderung

Dieses Vorhaben wird gefördert vom **Bundesministerium für Bildung und Forschung (BMBF)** und dem **Freistaat Sachsen** im Rahmen der Exzellenzstrategie von Bund und Ländern.
<br>

<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/a/a2/Logo_TU_Dresden_2025.svg" alt="TU Dresden Logo" width="180"/>
  &nbsp;&nbsp;&nbsp;
  <img src="https://upload.wikimedia.org/wikipedia/de/b/ba/Dresden-concept_Logo.png" alt="Dresden Concept Logo" width="180"/>
</p>
