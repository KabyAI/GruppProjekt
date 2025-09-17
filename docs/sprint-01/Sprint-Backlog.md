# Sprint 1 – Backlog

## Sprint Goal
Utforska publika API:er och analysera vilka uppdateras dagligen, veckovis eller månadsvis.  
Planera arbetet i Trello som project board.

## Tasks
- [ ] Identifiera minst 3 publika API:er som uppdateras dagligen  
- [ ] Identifiera minst 2 publika API:er som uppdateras veckovis  
- [ ] Identifiera minst 2 publika API:er som uppdateras månadsvis  
- [ ] Dokumentera korta anteckningar om varje API (datatyp, frekvens, auth ja/nej)  
- [ ] Välja 1 API som kandidat för nästa sprint  
- [ ] Sätta upp Trello board (To Do / In Progress / Review / Done)  
- [ ] Dela in roller (PO, Scrum Master) och lägga in första uppgifterna i Trello

# Sprint 2 – Backlog

## Sprintmål
Få igång första pipelinen (API → GCP), träna en baseline-ML-modell, testa deployment i GCP och förtydliga Task 2-kraven med läraren.

## Tasks
- [ ] Ingestion-service (Python+Docker) → Cloud Run + Cloud Scheduler.
- [ ] Spara data i GCS/BigQuery, enkel transform.
- [ ] Träna och spara baseline-ML-modell.
- [ ] Testa Cloud Run + FastAPI (alt. Vertex AI jämförelse).
- [ ] Lägg till CI/CD-workflow i GitHub.
- [ ] Dokumentera sprinten i `docs/sprint-01/`.

## Definition of Done
- Pipeline schemalagd och körbar.
- Första ML-modell tränad.
- Target/problem dokumenterat.
- Minst en service deployas via CI/CD.
- **Lärarens svar dokumenterade och inkorporerade i planeringen.**
