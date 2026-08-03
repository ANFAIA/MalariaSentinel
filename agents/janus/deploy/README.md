# Langfuse self-host deploy (M15)

This directory contains the artifact for deploying a self-hosted Langfuse stack
on the user's Raspberry Pi 4 8GB via Dockploy. The Pi is reached from the Mac
through a Cloudflare tunnel.

The janus code on the Mac emits OpenTelemetry-compatible traces to this
Langfuse instance whenever `--tracing langfuse` is passed (or `JANUS_TRACING=langfuse`
is set in `.env`).

## Files

- `langfuse-compose.yml` — 5-service stack (web, worker, postgres, redis, clickhouse).
  Copy this into Dockploy as a new app on your Pi.

## Deploy steps (on the Pi via Dockploy)

### 1. Set up env vars in Dockploy

Required (always):

| Var | Example | Notes |
|---|---|---|
| `LANGFUSE_NEXTAUTH_SECRET` | `openssl rand -base64 32` | 32+ char random. Used by NextAuth. |
| `LANGFUSE_SALT` | `openssl rand -base64 32` | 32+ char random. Used for password hashing. |

Optional (defaults shown):

| Var | Default |
|---|---|
| `LANGFUSE_PG_USER` / `_PASSWORD` / `_DB` | `langfuse` / `langfuse_pw` / `langfuse` |
| `LANGFUSE_CLICKHOUSE_USER` / `_PASSWORD` / `_DB` | `langfuse` / `langfuse_pw` / `langfuse` |
| `LANGFUSE_INIT_ORG_ID` | `malaria-sentinel` |
| `LANGFUSE_INIT_PROJECT_ID` | `janus` |
| `LANGFUSE_INIT_PROJECT_NAME` | `Janus` |
| `LANGFUSE_INIT_USER_EMAIL` / `_PASSWORD` / `_NAME` | (empty — manual signup) |
| `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` / `_SECRET_KEY` | (empty — created on signup) |
| `LANGFUSE_NEXTAUTH_URL` | `http://localhost:3000` (override with your tunnel URL once known) |

### 2. Paste `langfuse-compose.yml` into Dockploy

- New app → "Docker Compose" → paste the file.
- Map env vars from step 1.
- Deploy.

### 3. Wait for first-boot migrations (~2-3 min)

The langfuse-web container runs DB migrations against postgres + clickhouse on
startup. Watch the logs in Dockploy. Once `langfuse-web` reports it's serving
on :3000, it's ready.

### 4. Configure Cloudflare tunnel

Cloudflared config (separate from this stack — point at the langfuse service):

```yaml
# /etc/cloudflared/config.yml on the Pi (or your cloudflared host)
tunnel: <your-tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  - hostname: langfuse.your-domain.example.com
    service: http://langfuse-web:3000
  - service: http_status:404
```

Then in Cloudflare dashboard:

```
DNS → Records → Add CNAME
  Name: langfuse
  Target: <your-tunnel-id>.cfargotunnel.com
  Proxy: Proxied
```

### 5. Override `LANGFUSE_NEXTAUTH_URL` to the public URL

Once the tunnel is live, update the `LANGFUSE_NEXTAUTH_URL` env var in Dockploy
to `https://langfuse.your-domain.example.com`. Restart `langfuse-web`.

This is critical: NextAuth uses `NEXTAUTH_URL` to build callback URLs. If it
points at `http://localhost:3000` while the user is at the tunnel URL, auth
cookies don't work.

### 6. Sign up + create project

1. Open `https://langfuse.your-domain.example.com`.
2. Sign up (first user becomes org admin).
3. Create a project named `janus`.
4. Go to Project Settings → API Keys → copy `Public Key` (`pk-lf-...`) and
   `Secret Key` (`sk-lf-...`).

## Mac-side wiring

Add to your project-root `.env` (NOT committed):

```bash
LANGFUSE_HOST=https://langfuse.your-domain.example.com
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx
JANUS_TRACING=langfuse
```

Install the langfuse SDK in the venv:

```bash
uv pip install -e 'agents/janus[observability]'
```

## Usage

```bash
# All three flags are equivalent — pick your style.
janus improve -g "Implement M13" --plan docs/plans/in-process/m13-daily-env-nc.md --tracing langfuse
janus improve -g "..." --tracing langfuse --quiet     # langfuse only, no terminal panel
JANUS_TRACING=langfuse janus improve -g "..."         # from .env, no flag needed
```

Each run creates one Langfuse **trace** named `janus-improve` (or `janus-run`)
with nested observations:

- One `generation` per LLM call (model + tokens + latency + preview)
- One `span` per tool call (input + output + latency, marked ERROR on failure)
- Top-level metadata: session_id, llm_calls, tool_calls, token totals

## Persistence

Langfuse data lives in 3 named Docker volumes on the Pi:

| Volume | Contents | Approx size after 1 week of typical janus use |
|---|---|---|
| `clickhouse_data` | Trace observations (the bulk) | ~500MB |
| `langfuse_pg` | Users, projects, API keys | ~50MB |
| `langfuse_redis` | Job queue (transient) | ~10MB |

Total: ~600MB for a typical week. The 8GB Pi has plenty of room.

## Backups

If you want to back up langfuse state, snapshot the three named volumes. The
`postgres` volume is the most critical (it has your users + API keys). The
`clickhouse` volume has the trace data — losing it loses history but not auth.

## Pi 4 8GB sizing

| Service | Idle RAM | Under load |
|---|---|---|
| langfuse-clickhouse | ~500MB | ~1.5GB |
| langfuse-postgres | ~150MB | ~400MB |
| langfuse-redis | ~30MB | ~100MB |
| langfuse-worker | ~250MB | ~500MB |
| langfuse-web | ~300MB | ~700MB |
| **Total** | **~1.2GB** | **~3.2GB** |

Pi 4 8GB has 4-5GB headroom even at peak. No swap, no special tuning needed.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Mac can't reach `LANGFUSE_HOST` | Cloudflare tunnel not pointing at `langfuse-web:3000` | Check `cloudflared` config + Cloudflare DNS |
| `langfuse-web` keeps restarting | Clickhouse not ready when web starts | Wait 30s, restart web manually |
| Auth callback fails on signup | `NEXTAUTH_URL` still set to `localhost:3000` | Override with public tunnel URL, restart `langfuse-web` |
| `LANGFUSE_PUBLIC_KEY` invalid | Wrong project keys | Re-copy from Project Settings → API Keys |
| Traces not appearing in UI | `langfuse.flush()` not called | Already handled in `ObservabilityMiddleware.after_agent`; check `runs/<session>/session.jsonl` for `langfuse_error` events |

## When you're done with M15

The langfuse stack on the Pi runs independently of janus on the Mac. You can
leave it running 24/7 (~1.2GB idle RAM). Restart only when you bump the langfuse
image version (e.g. `langfuse/langfuse:3` → `:3.1`).