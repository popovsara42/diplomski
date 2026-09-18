Sistem koristi:

Python/FastAPI za backend
Vue.js za frontend
LegalRuleML za predstavljanje pravnih pravila
ASP/Clingo za rezonovanje
OWL ontologiju i HermiT za rad sa ontoloskim podacima

Pokretanje
Bekend:
Iz foldera legal_reasoning:
python -m uvicorn backend.orchestra:app --reload --port 8000

Frontend:
Iz foldera legal_reasoning/frontend:
npm install
npm run dev
