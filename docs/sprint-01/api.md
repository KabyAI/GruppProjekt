# API-kandidater att utforska

I Sprint 1 undersöker vi olika publika API:er som kan användas i vårt projekt.  
Fokus ligger på att välja källor med olika uppdateringsfrekvens (dagligen, veckovis, månadsvis) och olika typer av data.

---

## 🌍 Internationella API:er

### 1. OpenWeatherMap
- **Uppdateringsfrekvens:** Daglig (även timvis och prognoser)  
- **Dokumentation:** [Current Weather Data API](https://openweathermap.org/current)  
- **Beskrivning:** Ger aktuell väderdata, prognoser och historiska data i JSON-format.  
- **Användning:** Bra för att bygga en enkel ingestion-pipeline med dagliga uppdateringar.

### 2. Carbon Monitor
- **Uppdateringsfrekvens:** Daglig (nära realtid)  
- **Dokumentation:** [Carbon Monitor](https://carbonmonitor.org/)  
- **Beskrivning:** Globalt dataset över CO₂-utsläpp från fossila bränslen och cementproduktion.  
- **Användning:** Kan kombineras med väderdata för klimatrelaterade insikter.

### 3. OpenStreetMap (Overpass API)
- **Uppdateringsfrekvens:** Minutvis (databas), veckovisa snapshots  
- **Dokumentation:** [Overpass API guide](https://wiki.openstreetmap.org/wiki/Overpass_API)  
- **Beskrivning:** Geodata (vägar, byggnader, platser) tillgänglig i JSON via Overpass.  
- **Användning:** Bra som sekundär datakälla för analys eller visualisering.

### 4. Open-Meteo
- **Uppdateringsfrekvens:** Daglig (real-time endpoint)  
- **Dokumentation:** [Open-Meteo API](https://open-meteo.com/)  
- **Beskrivning:** Enkel väder-API som inte kräver API-nyckel.  
- **Användning:** Snabb testkälla för ingestion utan auth.

---

## 🇸🇪 Svenska API:er

### 1. SCB – Statistikdatabasen (PxWeb API)
- **Uppdateringsfrekvens:** Varierar (månatlig, kvartalsvis eller årlig beroende på dataset)  
- **Dokumentation:** [SCB Open Data API](https://www.scb.se/en/services/open-data-api/)  
- **Beskrivning:** Ger officiell statistik om befolkning, arbetsmarknad, ekonomi och geodata.  
- **Användning:** Bra för att visualisera svenska samhällstrender.

### 2. Krisinformation.se API
- **Uppdateringsfrekvens:** Realtid  
- **Dokumentation:** [Krisinformation.se API v3](https://www.krisinformation.se/om-krisinformation/for-myndigheter-och-andra-aktorer/oppen-data)  
- **Beskrivning:** Krisnyheter och varningar direkt från myndigheter.  
- **Användning:** Enkel realtidskälla som kan integreras i pipeline.

### 3. Arbetsförmedlingen – Jobbdata API
- **Uppdateringsfrekvens:** Daglig/veckovis (annonser uppdateras löpande)  
- **Dokumentation:** [Arbetsförmedlingen öppna API:er](https://arbetsformedlingen.se/other-languages/english-engelska/about-the-website/apis-and-open-data)  
- **Beskrivning:** Jobbannonser, prognoser och arbetsmarknadsdata.  
- **Användning:** Exempel på dynamisk samhällsdata från Sverige.

### 4. SOCH – Swedish Open Cultural Heritage
- **Uppdateringsfrekvens:** Löpande, beroende på källor  
- **Dokumentation:** [SOCH API (Kulturarvsdata)](https://www.raa.se/in-english/digital-services/open-cultural-heritage/)  
- **Beskrivning:** Metadata om kulturarv, museisamlingar och historiska platser.  
- **Användning:** Kreativ datakälla som kan kombineras med andra dataset.

---

## 📌 Sammanfattning

- **Dagliga uppdateringar:** OpenWeatherMap, Carbon Monitor, Krisinformation.se, Arbetsförmedlingen  
- **Veckovisa uppdateringar:** Vissa Data.gov- och SCB-dataset, Arbetsförmedlingen prognoser  
- **Månadsvisa uppdateringar:** Många SCB-dataset, vissa kulturarvsdata (SOCH)  

