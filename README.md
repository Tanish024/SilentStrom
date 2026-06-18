# 🌩️ SilentStorm

**Fraud Campaign Intelligence System** — Automatically clusters, links, and lifecycle-tracks complaint waves to uncover coordinated fraud campaigns targeting Indian financial consumers.

Built for a 48-hour hackathon.

---

## 🎯 What It Does

SilentStorm ingests raw consumer fraud complaints (in Hindi, English, or mixed), and:

1. **Extracts entities** — UPI IDs, phone numbers, URLs, fake app names, monetary amounts using spaCy NER + custom regex
2. **Embeds complaints** — Generates 768-dimensional multilingual sentence embeddings (Hindi + English) using Sentence-BERT
3. **Clusters into campaigns** — Groups complaints into fraud campaigns using HDBSCAN density-based clustering
4. **Fingerprints campaigns** — Identifies top mule UPI IDs, phone numbers, app names, and date ranges per cluster
5. **Builds mule networks** — Constructs a Neo4j graph linking complaints → UPI → phone → campaign (shared UPI IDs become hub nodes)
6. **Detects lifecycle stages** — Tags each campaign as EMERGING, ACTIVE, DORMANT, RESURGENT, or DECLINED based on temporal patterns

---

## 📁 Project Structure

```
silentstorm/
├── backend/
│   ├── main.py                  # FastAPI entry-point
│   ├── ingest.py                # Complaint ingestion pipeline
│   ├── ner_extractor.py         # spaCy + regex entity extraction
│   ├── embedder.py              # Sentence-BERT embeddings (singleton)
│   ├── clusterer.py             # HDBSCAN clustering + fingerprinting
│   ├── graph_builder.py         # Neo4j mule-network graph
│   ├── lifecycle.py             # Campaign lifecycle stage detection
│   ├── test_clustering.py       # Phase 3 integration test
│   ├── download_models.py       # One-time model downloader
│   ├── requirements.txt         # Pinned Python dependencies
│   └── data/
│       ├── complaints.json      # 170 synthetic complaints (4 campaigns)
│       └── generate_complaints.py
├── frontend/
│   └── src/
│       └── components/
│           ├── Dashboard.jsx
│           ├── ClusterPanel.jsx
│           ├── GraphViewer.jsx
│           ├── CampaignTimeline.jsx
│           └── AlertPanel.jsx
├── docker-compose.yml           # Neo4j 5 container
└── .gitignore
```

---

## 🗃️ Seed Data — 4 Fraud Campaigns

| Campaign | Complaints | Theme | App Names | Dormancy |
|----------|-----------|-------|-----------|----------|
| **A** — KYC Fraud | 50 | SBI/HDFC KYC verification scam | SBI KYC Verify, HDFC KYC Update | — |
| **B** — Loan Scam | 50 | Fake loan processing fees | Easy Loan Approval, PM Loan App | — |
| **C** — Investment Scam | 40 | Fake stock/trading platforms | Stock Profit Pro, SEBI Trading | ✅ 10-day gap |
| **D** — Delivery Fraud | 30 | Amazon/Flipkart delivery phishing | Amazon Delivery Failed, Flipkart Delivery Failed | — |

Each campaign has **3 reused UPI IDs** that create visible hub nodes in the mule network graph.  
Complaints are written in **Hindi**, **English**, and **mixed (hi-en)** to test multilingual embedding quality.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker (for Neo4j)

### 1. Install Dependencies

```bash
cd silentstorm/backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Download Embedding Model (One-Time)

```bash
python download_models.py
```

This downloads and caches `paraphrase-multilingual-mpnet-base-v2` (~420 MB).

### 3. Start Neo4j

```bash
cd silentstorm
docker-compose up -d
```

Neo4j Browser: [http://localhost:7474](http://localhost:7474)  
Credentials: `neo4j` / `password123`

### 4. Run the Clustering Test (Phase 3)

```bash
cd silentstorm/backend
python test_clustering.py
```

Expected output: **4 clusters** matching the 4 campaigns, plus fingerprints and Campaign C dormancy gap analysis.

### 5. Start the API Server

```bash
cd silentstorm/backend
uvicorn main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| API | FastAPI | 0.111.0 |
| NER | spaCy (en_core_web_sm) | 3.7.5 |
| Embeddings | sentence-transformers (paraphrase-multilingual-mpnet-base-v2) | 3.0.1 |
| Clustering | HDBSCAN | 0.8.38.post1 |
| Graph DB | Neo4j | 5.x |
| Python driver | neo4j | 5.22.0 |
| Server | Uvicorn | 0.30.1 |

---

## 📊 Build Progress

| Phase | Hours | Status | Description |
|-------|-------|--------|-------------|
| **Phase 1** | 0–4 | ✅ Complete | Project scaffold, Docker, 170 synthetic complaints |
| **Phase 2** | 4–8 | ✅ Complete | NER extractor (spaCy + regex), Sentence-BERT embedder |
| **Phase 3** | 8–11 | ✅ Complete | HDBSCAN clustering, campaign fingerprints, integration test |
| **Phase 4** | 11–16 | 🔲 Pending | Neo4j mule-network graph construction |
| **Phase 5** | 16–20 | 🔲 Pending | Campaign lifecycle engine |
| **Phase 6** | 20–24 | 🔲 Pending | REST API wiring |
| **Phase 7** | 24–48 | 🔲 Pending | React frontend dashboard |

---

## 🔑 Key HDBSCAN Parameters

```python
run_clustering(
    embeddings,
    min_cluster_size=5,
    min_samples=2,
    metric="euclidean",
    cluster_selection_epsilon=0.3
)
```

---

## 📄 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/ingest` | Upload complaints JSON |
| `GET` | `/clusters` | List all campaign clusters |
| `GET` | `/clusters/{id}` | Get cluster details |
| `GET` | `/graph` | Full mule-network graph |
| `GET` | `/graph/campaign/{label}` | Campaign subgraph |
| `GET` | `/lifecycle` | All campaign lifecycle stages |
| `GET` | `/lifecycle/{label}` | Single campaign lifecycle |

---

## 👥 Team

- **Tanish Mehta** — Core development (Phases 1–3)

---

## 📝 License

This project was built for a hackathon and is provided as-is.