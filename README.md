# FALO Edge Platform (Cloud Foundation)

Welcome to the **FALO Edge Platform** repository, the foundational cloud infrastructure for FALO projects. This repository coordinates the setup and management of our global edge infrastructure, bridging localhost services securely to the internet.

## 🌟 Architecture Overview

```
          [ Internet ]
               │
               ▼
       [ Cloudflare Edge ]
  (DNS, SSL, Workers, WAF, Pages)
               │
               ▼
   [ Cloudflare Tunnel Agent ]
         (cloudflared)
               │
               ▼
       [ Local Services ]
  (Python APIs, AI Models, Runtimes)
```

By leveraging Cloudflare Tunnels, we route public domains directly to containerized or local microservices without opening inbound firewall ports.

---

## 📂 Project Structure

```
├── .gitignore
├── .env.example
├── .env                  # Local secret configs (ignored by Git)
├── README.md
├── bin/                  # Directory for local cloudflared binary
├── docs/                 # Detailed architectural guides and SOPs
│   └── cloudflare_tunnel_guide.md
└── scripts/              # Infrastructure scripts
    ├── setup.sh          # Auto-downloader and installer
    └── run-tunnel.sh     # Script to run the local tunnel agent
```

---

## 🚀 Quick Start

### 1. Setup the Environment
Clone this repository and create your local `.env` file from the example template:
```bash
cp .env.example .env
```
Open `.env` and configure your `CLOUDFLARE_TUNNEL_TOKEN`.

### 2. Download and Set Up cloudflared
We provide a setup script that automatically checks your machine's CPU architecture, downloads the correct official precompiled binary from Cloudflare, and verifies its installation.

Run the setup script:
```bash
chmod +x scripts/*.sh
./scripts/setup.sh
```

### 3. Run the Tunnel Agent
To start the tunnel and route requests to your local environment:
```bash
./scripts/run-tunnel.sh
```
Check your Cloudflare Dashboard; the tunnel status should shift to **Connected**.
