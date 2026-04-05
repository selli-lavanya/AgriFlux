# AgriFlux

**Predictive Agricultural Operations Coordination Platform**



AgriFlux is a regional farm operations intelligence system that helps coordinate machines, labour teams, and irrigation schedules. It acts as an operational bottleneck forecast system and priority dispatcher.



## Folder Structure



- `/backend` - FastAPI Python Server

- `/frontend` - Next.js React Web Client

- `/docs` - System requirements and architecture



## Prerequisites

- Node.js (v18+)

- Python (v3.10+)

- PostgreSQL (v14+)



## Setup Instructions



### Backend

1. `cd backend`

2. `python -m venv venv`

3. `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)

4. `pip install -r requirements.txt`

5. Copy `.env.example` to `.env` and configure credentials.



### Frontend

1. `cd frontend`

2. `npm install`

3. Copy `.env.example` to `.env` and set `NEXT_PUBLIC_API_URL`.

4. `npm run dev`

