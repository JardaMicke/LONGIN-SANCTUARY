<div align="center">

# 🌟 LONGIN SANCTUARY

**Plně lokální AI platforma pro tvorbu a interakci s konzistentními AI charaktery**

*Lokální · Soukromé · Distribuované · Multimodální*

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-integrated-orange.svg)](https://github.com/comfyanonymous/ComfyUI)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow.svg)]()

</div>

---

## 🎯 Co je LONGIN SANCTUARY?

LONGIN SANCTUARY je plně lokální, soukromá AI platforma pro tvorbu a interakci s AI charaktery. Každá postava má vlastní oddělenou paměť, osobnost a vizuální identitu. Veškeré generování — textu, obrázků i videa — probíhá **100% lokálně** na tvém hardwaru nebo napříč zařízeními v lokální síti.

> **Žádná data neopustí tvoji síť. Žádný cloud. Žádné předplatné.**

---

## ✨ Klíčové funkce

### 🧬 Character Engine
- Tvorba postav s vlastní osobností, historií a vizuálním stylem
- **Trojvrstvá vizuální konzistence**: IP-Adapter FaceID + ControlNet + LoRA
- Automatické trénování LoRA z referenčních fotek
- Oddělená paměť pro každou postavu

### 💬 Chat & Scénáře
- Přímý chat s postavou (zachování kontextu přes STM/LTM)
- Scénáře s textovým popisem světa a situace
- Plný roleplay s více postavami
- Multimodální scénáře: text + obrázky + video

### 🎨 Lokální Generování (100% offline)
| Typ | Popis |
|-----|-------|
| **Text → Obrázek** | Flux / SDXL + IP-Adapter (konzistence obličeje) |
| **Text → Video** | WanVideo 2.1 / CogVideoX |
| **Obrázek → Video** | SVD / CogVideoX |
| **Start+End → Video** | FILM interpolation |
| **Vizuál postavy** | Z fotek / textu → konzistentní charakter |

### 🧠 Paměťový systém
- **STM (Krátkodobá)**: Redis — aktivní kontext konverzace
- **LTM (Dlouhodobá)**: PostgreSQL — fakta, shrnutí, historie
- **RAG**: Qdrant — vektorové vyhledávání v paměti
- Automatická správa context window (tokenizer-aware)

### 🌐 Distribuovaný výpočet v síti
- **Automatická detekce zařízení** v lokální síti (mDNS)
- **Přidání zařízení do clusteru**: žádost → potvrzení → auto-instalace
- **Distribuce LLM vah** přes více zařízení ([exo](https://github.com/exo-labs/exo) / llama.cpp RPC)
- Spouštění většího modelu než by zvládlo jedno zařízení
- Distribuce ComfyUI jobů (obrázky/video) přes síť

### ⚙️ Unified Settings
- Veškerá nastavení na jednom místě (LLM, Image, Video, Memory, Network, ComfyUI)
- Real-time přehled clusteru (VRAM, zatížení, aktivní joby)

### 🔞 NSFW & Obsah
- LLM modely jsou plně zaměnitelné (SFW ↔ NSFW)
- NSFW obsah chráněn age-check vrstvou
- Oddělená konfigurace obsahu per-character

---

## 🖥️ Požadavky

### Minimální (jeden počítač)
- GPU s ≥ 8 GB VRAM (NVIDIA / AMD)
- 16 GB RAM
- 50 GB volného místa (+ místo pro modely)
- Windows 10/11, Ubuntu 22.04+, nebo macOS 12+
- Docker Desktop

### Doporučené (cluster)
- Hlavní node: GPU ≥ 12 GB VRAM (např. RTX 3060 12GB)
- Sekundární node(s): libovolná GPU/CPU
- Gigabit LAN (nebo rychlejší)
- Ollama nainstalovaný na všech nodech

---

## 🚀 Rychlý start

> ⚠️ **Aplikace je ve vývoji.** Setup instrukce budou doplněny.

```bash
# 1. Klonuj repozitář
git clone https://github.com/JardaMicke/LONGIN-SANCTUARY.git
cd LONGIN-SANCTUARY

# 2. Zkopíruj konfiguraci
cp .env.example .env
# Upravit .env podle svého hardwaru

# 3. Spusť pomocí Docker Compose
docker compose up -d

# 4. Otevři UI
# http://localhost:3000
```

---

## 📁 Struktura projektu

```
LONGIN-SANCTUARY/
├── backend/                    # Python FastAPI backend
│   ├── api/                   # REST endpointy
│   ├── core/
│   │   ├── characters/        # Character Engine
│   │   ├── memory/            # STM + LTM + RAG
│   │   ├── generation/        # AI generování (Quality Control)
│   │   ├── network/           # Cluster discovery & scheduling
│   │   ├── context/           # Context window / tokenizer
│   │   └── inference/         # LLM inference engine
│   ├── services/              # Integrace: ComfyUI, exo, Ollama
│   └── config/                # Unified konfigurace
├── frontend/                   # Next.js UI
│   ├── components/
│   ├── pages/
│   └── styles/
├── comfyui_workflows/          # Předpřipravené ComfyUI workflow
│   ├── text_to_image_character.json
│   ├── text_to_video_character.json
│   ├── image_to_video.json
│   ├── start_end_to_video.json
│   └── character_lora_trainer.json
├── scripts/
│   ├── setup.ps1              # Windows setup
│   ├── setup.sh               # Linux/macOS setup
│   └── cluster_agent.py       # Cluster worker agent
├── docker/
│   └── docker-compose.yml
└── docs/
    └── samples/               # Ukázkové výstupy
```

---

## 🌐 Architektura clusteru

```
┌─────────────────────────────────────────────────────┐
│               LONGIN SANCTUARY UI                    │
│          (Next.js — Unified Settings)                │
└──────────────────────┬──────────────────────────────┘
                       │ REST / WebSocket
┌──────────────────────▼──────────────────────────────┐
│              SANCTUARY CORE API (FastAPI)             │
├──────────────┬───────────────┬─────────────────────-┤
│  Character   │  Memory Engine │  Generation          │
│  Manager     │  STM+LTM+RAG  │  Orchestrator        │
└──────────────┴───────────────┴──────────────────────┘
                       │ Network Discovery (mDNS)
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ CORE-DT │   │NITRO-NB │   │ MiniPC  │  ← + libovolné zařízení
   │RTX 3060 │   │GTX 1650 │   │  ???    │
   │  12 GB  │   │   4 GB  │   │         │
   └─────────┘   └─────────┘   └─────────┘
         ↑              ↑              ↑
     exo / llama.cpp RPC — distribuce LLM vah
     ComfyUI distributed — generování médií
```

---

## 🔧 Tech Stack

| Komponenta | Technologie |
|-----------|-------------|
| **Backend** | Python 3.11, FastAPI, SQLModel |
| **Frontend** | Next.js 14, TypeScript |
| **LLM (lokální)** | Ollama + [exo](https://github.com/exo-labs/exo) (distributed) |
| **Distribuce LLM** | [exo-labs/exo](https://github.com/exo-labs/exo) + llama.cpp RPC |
| **Image Gen** | ComfyUI + Flux + SDXL |
| **Video Gen** | WanVideo 2.1 + CogVideoX |
| **Konzistence obličeje** | IP-Adapter FaceID Plus V2 + InsightFace |
| **Konzistence těla** | ControlNet OpenPose/Depth |
| **LoRA trénink** | AI-Toolkit |
| **STM DB** | Redis |
| **LTM DB** | PostgreSQL |
| **Vector DB (RAG)** | Qdrant |
| **Tokenizer** | tiktoken + HuggingFace transformers |
| **Network Discovery** | mDNS / Zeroconf |
| **Containerization** | Docker + Docker Compose |

---

## 🗺️ Roadmap

- [ ] **Fáze 1**: Základní infrastruktura a Docker setup
- [ ] **Fáze 2**: Character Engine + vizuální konzistence
- [ ] **Fáze 3**: Paměťový systém (STM + LTM + RAG)
- [ ] **Fáze 4**: Lokální generování médií (T2I, T2V, I2V)
- [ ] **Fáze 5**: Chat a scénáře / roleplay
- [ ] **Fáze 6**: Distribuovaný výpočet — cluster join flow
- [ ] **Fáze 7**: Unified Settings UI
- [ ] **Fáze 8**: Quality control, benchmarky, optimalizace

---

## ⚠️ Obsah a věková hranice

Tato platforma může být nakonfigurována pro NSFW obsah. NSFW funkce jsou:
- Deaktivovány ve výchozím nastavení
- Chráněny age-check vrstvou
- Vázány na konkrétní LLM modely (zaměnitelné)
- Kontrolovatelné per-character a per-session

---

## 📄 Licence

MIT License — viz [LICENSE](LICENSE)

---

<div align="center">

**LONGIN SANCTUARY** — *Tvoje AI. Tvůj hardware. Tvoje pravidla.*

</div>
