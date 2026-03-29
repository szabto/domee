<div align="center">

# 🌐 Domee

**Self-hosted domain availability checker with watchlist & email notifications**

[![Docker Pulls](https://img.shields.io/docker/pulls/szabto/domee?style=flat-square&color=4ade80)](https://hub.docker.com/r/szabto/domee)
[![Docker Image Size](https://img.shields.io/docker/image-size/szabto/domee/latest?style=flat-square&color=333)](https://hub.docker.com/r/szabto/domee)
[![License](https://img.shields.io/github/license/szabto/domee?style=flat-square&color=333)](LICENSE)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/szabto/domee/docker-publish.yml?style=flat-square)](https://github.com/szabto/domee/actions)

<br>

*Monitor domain names, get notified the moment they become available.*

<br>

<!-- Add a screenshot here once the app is running -->
<!-- ![Domee Screenshot](docs/screenshot.png) -->

</div>

---

## Features

- **Instant domain check** — type any domain and see if it's available in seconds
- **Watchlist** — save domains to monitor, with automatic WHOIS expiry date lookup
- **Background polling** — checks all watched domains at a configurable interval
- **Email notifications** — get alerted via SMTP when a domain becomes available
- **Modern dark UI** — clean, minimal interface that works on desktop and mobile
- **Single container** — everything runs in one Docker image with SQLite storage
- **Lightweight** — ~80MB image, minimal resource usage

## Quick Start

### Docker Run

```bash
docker run -d \
  --name domee \
  -p 8000:8000 \
  -v domee-data:/data \
  --restart unless-stopped \
  szabto/domee:latest
```

### Docker Compose

```yaml
services:
  domee:
    image: szabto/domee:latest
    container_name: domee
    ports:
      - "8000:8000"
    volumes:
      - domee-data:/data
    restart: unless-stopped

volumes:
  domee-data:
```

```bash
docker compose up -d
```

Then open **http://localhost:8000** in your browser.

## Usage

### Checking a Domain

1. Type a domain name in the search bar (e.g. `example.com`)
2. Click **Check** or press **Enter**
3. See instantly whether the domain is available or taken
4. Click the **+** button to add it to your watchlist

### Watchlist

- Domains in the watchlist show the **name**, **expiry date** (from WHOIS), and **status**
- Click the **×** button to remove a domain
- Click the **refresh** icon in the header to manually poll all domains

### Settings

Click the **gear** icon to configure:

| Setting | Description | Default |
|---------|-------------|---------|
| **Polling interval** | How often to check all watched domains (minutes) | `60` |
| **Notification email** | Where to send availability alerts | — |
| **SMTP Host** | Your mail server hostname | — |
| **SMTP Port** | Mail server port | `587` |
| **Username** | SMTP authentication username | — |
| **Password** | SMTP authentication password | — |
| **From email** | Sender address for notifications | — |
| **Use TLS** | Enable STARTTLS encryption | `true` |

### Gmail SMTP Example

To use Gmail for notifications:

1. Enable [App Passwords](https://myaccount.google.com/apppasswords) on your Google account
2. Generate an app password for "Mail"
3. Configure in Domee settings:
   - **SMTP Host:** `smtp.gmail.com`
   - **SMTP Port:** `587`
   - **Username:** `your@gmail.com`
   - **Password:** your app password
   - **From email:** `your@gmail.com`
   - **Use TLS:** enabled

## Building from Source

```bash
git clone https://github.com/szabto/domee.git
cd domee
docker build -t domee .
docker run -d -p 8000:8000 -v domee-data:/data domee
```

## CLI Help

```
Domee — Self-hosted Domain Availability Checker

USAGE:
  docker run -d -p 8000:8000 -v domee-data:/data szabto/domee:latest

OPTIONS:
  Port mapping     -p <host>:8000     Map container port 8000 to host
  Data volume      -v <name>:/data    Persist database across restarts
  Auto restart     --restart unless-stopped

ENVIRONMENT VARIABLES:
  DOMEE_DB_PATH    Path to SQLite database (default: /data/domee.db)

ENDPOINTS:
  GET  /              Web interface
  GET  /api/domains   List watched domains
  POST /api/domains   Add domain to watchlist
  DEL  /api/domains/  Remove domain from watchlist
  POST /api/check     Check domain availability
  GET  /api/settings  Get current settings
  PUT  /api/settings  Update settings
  POST /api/poll      Trigger manual poll
```

## Architecture

```
┌──────────────────────────────────────┐
│          Docker Container            │
│                                      │
│  ┌────────────┐   ┌──────────────┐   │
│  │  Frontend   │   │   FastAPI     │   │
│  │  HTML/CSS   │──▶│   Backend    │   │
│  │  Vanilla JS │   │              │   │
│  └────────────┘   └──────┬───────┘   │
│                          │           │
│                   ┌──────┴───────┐   │
│                   │   SQLite DB  │   │
│                   │   (/data)    │   │
│                   └──────────────┘   │
│                          │           │
│  ┌────────────┐   ┌──────┴───────┐   │
│  │   SMTP      │◀──│  APScheduler │   │
│  │   Email     │   │  Background  │   │
│  └────────────┘   └──────────────┘   │
└──────────────────────────────────────┘
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ☕ by [szabto](https://github.com/szabto)

</div>
