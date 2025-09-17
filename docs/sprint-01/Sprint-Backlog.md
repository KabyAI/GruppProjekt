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


# Sprint 3 – Backlog

## Sprintmål
Få in all data i BigQuery, bestämma hur den ska transformeras och förstå kolumnerna för dashboard. Utforska hur ML-modellen ska fungera i GCP samt planera för logging och testing.

## Tasks
- [ ] Ladda in dataset i BigQuery.  
- [ ] Definiera schema och transformationssteg.  
- [ ] Analysera kolumner och koppla till dashboard-design.  
- [ ] Utforska hur ML-modellen ska köras i GCP och vilka komponenter som behövs.  
- [ ] Planera logging (Cloud Logging/Monitoring).  
- [ ] Planera testing för pipelines och ML-modell (CI/CD, pytest).  
- [ ] Dokumentera sprinten i `docs/sprint-03/`.  

## Definition of Done
- Data finns i BigQuery.  
- Transformationsplan och schema är definierade.  
- Dashboard-design har ett första utkast.  
- ML-modellens deployment i GCP är undersökt och dokumenterad.  
- Plan för logging och testing är dokumenterad.  
