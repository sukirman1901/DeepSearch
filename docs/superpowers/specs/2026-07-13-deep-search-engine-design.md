# Design Spec: Deep Search Engine

## Overview

Custom search engine MCP server yang menggabungkan 7 free sources + semantic search via vector database. Alternatif free untuk Exa, lebih powerful dengan custom crawlers.

**Goal:** General-purpose search engine yang bisa search informasi dari web + social media, tanpa biaya API.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  MCP Server                      │
│         (FastMCP - Interface untuk AI)           │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│              Search Engine                        │
│   Query → Embed → Vector Search → Rank → Output  │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│            Vector Database (ChromaDB)             │
│         Menyimpan konten sebagai embedding        │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│              Crawler Manager                      │
│      Mengelola & menjalankan semua crawler        │
└───┬────────┬────────┬────────┬────────┬────────┬────────┬────────┐
    │        │        │        │        │        │        │        │
┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐
│ Web  │ │Reddit│ │YouTube│ │GitHub│ │Twitter│ │DDG   │ │Wiki  │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

## Components

### 1. Crawlers (7 Sources, 100% Free)

| Crawler | Source | Method |
|---------|--------|--------|
| WebCrawler | URL apapun | `httpx` + `BeautifulSoup` |
| RedditCrawler | r/* | Reddit JSON API (publik) |
| YouTubeCrawler | YouTube | `yt-dlp` (metadata + subtitle) |
| GitHubCrawler | Repos, Issues | GitHub REST API (60 req/jam) |
| Twitter/XCrawler | Tweet | Nitter scraping |
| DuckDuckGoCrawler | Web search | `duckduckgo-search` library |
| WikipediaCrawler | Wikipedia | Wikipedia API (publik) |

**Output format (semua crawler):**
```python
{
    "source": "reddit",
    "title": "...",
    "content": "konten bersih, tanpa HTML",
    "url": "...",
    "metadata": {
        "author": "...",
        "date": "...",
        "score": ...,
        "tags": [...]
    },
    "crawled_at": "2026-07-13T..."
}
```

**Rate limiting:**
- WebCrawler: 1 req/detik per domain
- RedditCrawler: 10 request/menit
- YouTubeCrawler: Bergantung yt-dlp
- GitHubCrawler: 60 request/jam (tanpa token)
- TwitterXCrawler: Bergantung Nitter instance
- DuckDuckGoCrawler: 10 request/menit
- WikipediaCrawler: 10 request/detik

### 2. Vector Database (ChromaDB)

**Penyimpanan:**
- Local, tanpa server
- Setiap konten disimpan sebagai embedding vector
- Metadata disimpan terpisah untuk filtering

**Schema:**
```python
{
    "id": "unique_id",
    "text": "konten bersih",
    "embedding": [0.12, -0.34, ...],  # 384 floats
    "metadata": {
        "source": "reddit",
        "title": "...",
        "url": "...",
        "crawled_at": "...",
        "author": "..."
    }
}
```

### 3. Embedding Model

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)
- 384-dimensional vectors
- Cepat, ringan, jalan lokal tanpa GPU
- Free, open source

**Cara kerja:**
1. Query dari user → embed dengan model yang sama
2. Cosine similarity search di ChromaDB
3. Return top-N results dengan skor relevansi

### 4. MCP Tools

| Tool | Fungsi | Parameter |
|------|--------|-----------|
| `deep_search` | Semantic search di DB | `query`, `source` (optional), `limit` |
| `web_crawl` | Crawl URL spesifik | `url` |
| `index_topic` | Crawl topik dari semua sources | `topic`, `sources` (optional) |
| `quick_search` | Real-time search tanpa DB | `query`, `source` |
| `get_content` | Ambil konten lengkap dari URL | `url` |
| `list_sources` | List semua sources | `—` |
| `db_stats` | Statistik DB | `—` |

### 5. AI Skill (SKILL.md)

Agent skill yang mendeskripsikan persona dan workflow untuk AI:
- Persona: Search assistant yang membantu cari informasi
- Workflow: Pilih source → search/crawl → validate → present
- Output: Hasil pencarian terstruktur dengan sumber

## Project Structure

```
mining/
├── .agents/skills/
│   └── deep-search/
│       └── SKILL.md
├── crawlers/
│   ├── __init__.py
│   ├── base.py
│   ├── web_crawler.py
│   ├── reddit_crawler.py
│   ├── youtube_crawler.py
│   ├── github_crawler.py
│   ├── twitter_crawler.py
│   ├── duckduckgo_crawler.py
│   └── wikipedia_crawler.py
├── db/
│   ├── __init__.py
│   ├── vector_store.py
│   └── embeddings.py
├── search/
│   ├── __init__.py
│   └── engine.py
├── server.py
├── requirements.txt
└── README.md
```

## Dependencies

- `mcp` — MCP server
- `httpx` — HTTP client
- `beautifulsoup4` — HTML parsing
- `duckduckgo-search` — DuckDuckGo
- `yt-dlp` — YouTube metadata
- `chromadb` — Vector database
- `sentence-transformers` — Embedding model
- `fastmcp` — MCP server wrapper

**Total: 8 dependencies, semua free, zero cost.**

## Data Flow

```
1. User: "Cari tentang AI di Indonesia"
2. AI: → index_topic("AI Indonesia")
3. Crawler Manager: → jalankan semua crawler
4. Crawlers: → kumpulkan data dari 7 sources
5. Embedding: → convert text ke vectors
6. ChromaDB: → simpan vectors + metadata
7. AI: → deep_search("AI Indonesia")
8. Search Engine: → embed query → cosine search → rank
9. AI: → validate + score hasil
10. AI: → present ke user
```

## Error Handling

- **Crawler gagal:** Skip source, lanjut ke source lain
- **Rate limit:** Auto-wait, tidak crash
- **DB penuh:** Auto-cleanup konten lama (configurable)
- **Embedding gagal:** Fallback ke keyword search
- **Network error:** Retry 3x, lalu skip

## Success Criteria

1. Bisa search dari 7 sources berbeda
2. Semantic search works (bukan cuma keyword)
3. Zero cost (tidak ada API key yang dibutuhkan)
4. MCP server bisa dipakai di Claude, Cursor, OpenCode
5. Response time < 5 detik untuk search biasa
6. Response time < 30 detik untuk index_topic
