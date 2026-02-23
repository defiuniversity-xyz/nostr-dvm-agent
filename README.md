# sats.ai - Nostr DVM AI Agent

An autonomous AI agent that sells compute for Bitcoin sats over the Lightning Network. Built on the [NIP-90 Data Vending Machine](https://github.com/nostr-protocol/nips/blob/master/90.md) protocol.

**Frontend**: [sats-ai-nostr-dvm.web.app](https://sats-ai-nostr-dvm.web.app) (Firebase Hosting)
**Backend**: Python daemon on Google Cloud Compute Engine
**Payments**: All sats go to `defiuniversity@strike.me`

## How It Works

```
User visits sats.ai
        |
        v
Types a query, picks a service (Generate, Translate, Summarize, Image)
        |
        v
Frontend publishes NIP-90 job request (Kind 5xxx) to Nostr relays
        |
        v
DVM Agent picks up the job, generates a Lightning invoice via Strike
        |
        v
Agent publishes Kind 7000 "payment-required" with BOLT-11 invoice
        |
        v
User scans QR code / pays with Lightning wallet
        |
        v
Sats settle to defiuniversity@strike.me -> Agent confirms via Strike API
        |
        v
Agent sends prompt to Gemini 3 Pro -> publishes Kind 6xxx result
        |
        v
Frontend displays the AI response
```

No accounts. No sign-ups. No credit cards. Just sats and AI.

## Architecture

```
nostr-dvm-agent/
├── backend/          Python DVM agent (Nostr + Gemini + Lightning)
│   ├── src/nostr_dvm_agent/
│   │   ├── main.py           Entry point
│   │   ├── config.py         Settings (.env)
│   │   ├── core/             Nostr client, event handler, state machine
│   │   ├── payment/          LNURL-pay + Strike API + Zap verification
│   │   ├── ai/               Gemini 3 Pro wrapper
│   │   ├── services/         DVM service implementations
│   │   ├── security/         NIP-44 v2 encryption
│   │   ├── advertising/      NIP-89 handler info
│   │   └── db/               SQLite job state persistence
│   ├── tests/
│   ├── scripts/
│   └── Dockerfile
│
└── frontend/         React SPA (sats.ai interface)
    ├── src/
    │   ├── App.tsx           Main page layout
    │   ├── lib/              Nostr relay pool, key management, types
    │   ├── hooks/            useNostrJob (full job lifecycle hook)
    │   └── components/       SearchBar, PaymentModal, ResultCard, etc.
    ├── firebase.json         Firebase Hosting config
    └── .firebaserc           Points to sats-ai-nostr-dvm project
```

## Supported DVM Services

| Kind | Service | Description | Default Cost |
|------|---------|-------------|-------------|
| 5001 | Text Generation | LLM chat/completion via Gemini 3 Pro | 500 msats |
| 5000 | Translation | Text translation between languages | 300 msats |
| 5100 | Image Generation | Text-to-image via Gemini | 2000 msats |
| 5002 | Text Extraction | Extract content from URLs | 200 msats |
| 5300 | Content Discovery | AI-powered content curation | 1000 msats |

## Quick Start

### 1. Generate Nostr Keys

```bash
cd backend
pip install .
python scripts/generate_keys.py
```

### 2. Configure Backend

```bash
cp backend/.env.example backend/.env
# Edit .env with your keys:
#   NOSTR_PRIVATE_KEY=nsec1...
#   GEMINI_API_KEY=AIza...
#   STRIKE_API_KEY=...
```

### 3. Run Backend Locally

```bash
cd backend
pip install -e ".[dev]"
python -m nostr_dvm_agent.main
```

### 4. Run Frontend Locally

```bash
cd frontend
cp .env.example .env
# Set VITE_DVM_PUBKEY to the public key from step 1
npm install
npm run dev
```

### 5. Test with a Job Request

```bash
cd backend
python scripts/test_job_request.py wss://relay.damus.io "What is Bitcoin?"
```

## Deployment

### Backend (Google Cloud Compute Engine)

```bash
# One-time setup on fresh instance
ssh your-instance "bash -s" < backend/scripts/setup-gce.sh

# Deploy
cd backend
./scripts/deploy-backend.sh YOUR_INSTANCE_IP
```

### Frontend (Firebase Hosting)

```bash
cd frontend
npm run build
firebase deploy --only hosting --project sats-ai-nostr-dvm
```

## Tech Stack

- **Backend**: Python 3.12, nostr-sdk, google-genai, httpx, aiosqlite, structlog
- **Frontend**: React 19, Vite, TypeScript, Tailwind CSS, nostr-tools, qrcode.react
- **Payments**: LNURL-pay protocol + Strike API (defiuniversity@strike.me)
- **Protocol**: NIP-90 (DVM), NIP-89 (Handler Info), NIP-57 (Zaps), NIP-44 (Encryption)

## License

MIT
