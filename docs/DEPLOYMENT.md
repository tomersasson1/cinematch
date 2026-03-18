# Deployment Guide: Temporary Sharing & Portfolio Hosting

This guide covers two use cases for your movie recommendation app:

1. **Temporary sharing** – Expose your local dev environment for quick feedback.
2. **Portfolio deployment** – Host the app permanently for resume/portfolio links.

Your stack: **Python, Streamlit, MovieLens data, TMDB API**. The app builds or loads precomputed artifacts and calls TMDB; it is not a static site.

---

## Part 1: Temporary Sharing (Quick Feedback)

Goal: Share your **running local app** with others for a short time, without deploying to a server.

### Option A: **ngrok**

| | |
|---|---|
| **How it works** | Creates a public URL (e.g. `https://abc123.ngrok.io`) that tunnels to your `localhost:8501`. |
| **Pros** | Fast setup, stable URLs (paid), HTTPS, works with Streamlit. Very popular. |
| **Cons** | Free tier: URL changes each run; rate limits. Paid for custom subdomain. |
| **Cost** | Free tier; paid from ~$8/mo for fixed subdomain. |

**Quick start:**
```bash
# Install: https://ngrok.com/download
ngrok http 8501
# Share the https://....ngrok-free.app URL (Streamlit runs on 8501)
```

### Option B: **Cloudflare Tunnel (cloudflared)**

| | |
|---|---|
| **How it works** | Same idea: tunnel from Cloudflare’s edge to your machine. No account required for quick tunnels. |
| **Pros** | Free, no URL signup for quick tunnels, good performance, from a major provider. |
| **Cons** | URL changes each time unless you use a Cloudflare domain + config. Slightly more setup for persistent hostname. |
| **Cost** | Free. |

**Install on Windows (PowerShell):**

1. Install using Windows Package Manager (run PowerShell as yourself, not necessarily Admin):
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. **Close and reopen PowerShell** (or your terminal) so `cloudflared` is on your PATH.
3. In the project folder, with your Streamlit app already running in another terminal:
   ```powershell
   cloudflared tunnel --url http://localhost:8501
   ```
4. Copy the `https://....trycloudflare.com` URL and share it.

**If `winget` doesn’t work:** Download the Windows amd64 executable from [Cloudflare Releases](https://github.com/cloudflare/cloudflared/releases) (e.g. `cloudflared-windows-amd64.exe`), rename to `cloudflared.exe`, and either put it in a folder that’s on your PATH or run it by full path, e.g.:
```powershell
& "C:\path\to\cloudflared.exe" tunnel --url http://localhost:8501
```

### Option C: **LocalTunnel**

| | |
|---|---|
| **How it works** | npm package that creates a tunnel to localhost. |
| **Pros** | Free, no signup, simple. |
| **Cons** | Less reliable than ngrok/Cloudflare; can be slow or drop. |
| **Cost** | Free. |

**Quick start:**
```bash
npx localtunnel --port 8501
# Share the https://... URL
```

### Option D: **VS Code / Cursor Port Forwarding**

| | |
|---|---|
| **How it works** | IDE can forward a port and give you a “Public” URL (often via a Microsoft tunnel). |
| **Pros** | No extra install if you use VS Code/Cursor; good for quick tests. |
| **Cons** | Tied to your IDE; not ideal for sending to external clients. |
| **Cost** | Free. |

---

### Temporary sharing – recommendation

- **Best balance:** **Cloudflare Tunnel** – free, reliable, one command.
- **If you want a stable URL and don’t mind paying:** **ngrok** paid plan (fixed subdomain).

**Security for temporary sharing:**

- Don’t leave the tunnel running when you’re not sharing.
- Your TMDB key is in the app’s environment; only people with the link can use the app (no built-in auth). For sensitive data, add a simple password in the app or use ngrok’s optional auth.

---

## Part 2: Permanent Deployment (Portfolio / Production)

Goal: Host the app **24/7** so you can put the link on your resume or portfolio.

Important: **Vercel and Netlify** are aimed at static sites and serverless functions. They can run small Python serverless functions but are **not** a good fit for a long‑running Streamlit server. So we focus on platforms that run a **persistent Python process**.

### Option A: **Streamlit Community Cloud**

| | |
|---|---|
| **How it works** | Streamlit’s own hosting: connect a GitHub repo, it builds and runs your app. |
| **Pros** | Free tier, made for Streamlit, simple (Git push = deploy), HTTPS, no server management. |
| **Cons** | Free apps sleep after inactivity (cold start); resource limits; must use GitHub. |
| **Cost** | Free tier; paid for always-on / more resources. |

**Fit for you:** Very good for a portfolio: minimal setup, looks professional.

### Option B: **Render**

| | |
|---|---|
| **How it works** | Connect GitHub; create a “Web Service”, choose Docker or native Python. Runs 24/7 or on-demand. |
| **Pros** | Free tier for web services, supports Python, Docker, background workers; clear dashboard. |
| **Cons** | Free tier spins down after ~15 min inactivity (cold start); 512 MB RAM; build/runtime limits. |
| **Cost** | Free tier; paid from ~$7/mo for always-on. |

**Fit for you:** Good if you want more control (e.g. Docker, env vars, cron later).

### Option C: **Railway**

| | |
|---|---|
| **How it works** | Deploy from GitHub or CLI; auto-detects or use a Dockerfile. |
| **Pros** | Simple UX, good free credit, supports Streamlit, DBs, Redis. |
| **Cons** | Free credit can run out; pricing is usage-based after that. |
| **Cost** | ~$5 free credit/mo; then pay-as-you-go. |

**Fit for you:** Good for portfolio and for learning modern deploy workflows.

### Option D: **Fly.io**

| | |
|---|---|
| **How it works** | Deploy containers globally; you provide a Dockerfile. |
| **Pros** | Generous free tier, global regions, full control. |
| **Cons** | More ops-oriented; you manage Docker and config. |
| **Cost** | Free tier (e.g. 3 shared-cpu VMs); then by usage. |

**Fit for you:** Best if you’re comfortable with Docker and want a “real” production setup.

### Option E: **Heroku**

| | |
|---|---|
| **How it works** | Git push to Heroku; buildpacks or Docker run the app. |
| **Pros** | Mature, lots of docs. |
| **Cons** | No meaningful free tier anymore; paid dynos only. |
| **Cost** | From ~$5–7/mo. |

**Fit for you:** Viable but not the best value for a single portfolio app.

### Option F: **AWS (EC2, ECS, Lightsail, etc.)**

| | |
|---|---|
| **How it works** | You run a VM or container; install Python, run Streamlit (or use Docker). |
| **Pros** | Full control, scalable, good for learning cloud. |
| **Cons** | You manage OS, security, SSL, restarts; more setup and responsibility. |
| **Cost** | Lightsail from ~$3.5/mo; EC2 free tier then by usage. |

**Fit for you:** Best for learning cloud and if you want maximum control.

---

## Part 3: Security & Cost Summary

**Security**

- **Secrets:** Never commit `TMDB_API_KEY` or `.env`. Use the platform’s **environment variables** (e.g. Streamlit Cloud, Render, Railway “Variables”).
- **HTTPS:** All options above give you HTTPS in production; tunnels (ngrok, Cloudflare) give HTTPS for temporary sharing.
- **Data:** MovieLens data in the repo or in precomputed artifacts is public-dataset; TMDB key in env is the main secret to protect.

**Cost (rough)**

- **Temporary:** Cloudflare Tunnel / LocalTunnel free; ngrok free (rotating URL) or paid for fixed URL.
- **Portfolio:** Streamlit Community Cloud or Render free tier = $0 with cold starts; Railway/Fly.io free tiers often enough for one app; Heroku/AWS from a few dollars/month.

---

## Part 4: Recommended Path

**Temporary sharing**

- Use **Cloudflare Tunnel**: one command, free, reliable.  
  Command: `cloudflared tunnel --url http://localhost:8501`

**Portfolio (permanent)**

- **First choice:** **Streamlit Community Cloud** – purpose-built for Streamlit, free tier, GitHub-based, ideal for resume/portfolio.
- **Second choice:** **Render** – if you prefer a generic PaaS or plan to add Docker/workers later.

---

## Part 5: Step-by-Step – Temporary Sharing (Cloudflare Tunnel)

1. **Install Cloudflare Tunnel (Windows)**
   - In PowerShell run:
     ```powershell
     winget install Cloudflare.cloudflared
     ```
   - **Important:** Close and reopen your terminal so `cloudflared` is on your PATH. Otherwise you’ll get “cloudflared is not recognized”.
   - If winget isn’t available, download from: https://github.com/cloudflare/cloudflared/releases (e.g. `cloudflared-windows-amd64.exe`), put it somewhere and run it by full path.

2. **Start your app locally**
   ```powershell
   cd "c:\programing\Movie recommandation system"
   $env:TMDB_API_KEY = "your_key"
   python -m streamlit run app/streamlit_app.py
   ```
   Leave this terminal open.

3. **In a second terminal, start the tunnel**
   ```powershell
   cloudflared tunnel --url http://localhost:8501
   ```

4. **Share the URL**  
   Copy the `https://....trycloudflare.com` URL and send it to whoever should try the app. When you close the tunnel or stop Streamlit, the link stops working.

**If you get “cloudflared is not recognized”:** The app isn’t on your PATH yet. Close **all** PowerShell/terminal windows, open a new one, and run `cloudflared tunnel --url http://localhost:8501` again. If you installed via a manual download, run the exe by full path (see Option B above).

**Easiest on Windows:** From the project root run `.\scripts\tunnel.ps1` — it downloads cloudflared into `scripts\bin` once and runs the tunnel. Have Streamlit running on 8501 first. No PATH or separate install needed.

**No-install alternative (if you have Node.js):** You can tunnel without cloudflared by running:
```powershell
npx localtunnel --port 8501
```
Share the printed URL. No account or install required; Node/npm must be installed.

---

## Part 6: Step-by-Step – Portfolio Deployment (Streamlit Community Cloud)

### Prerequisites

- GitHub account.
- Project pushed to a GitHub repo (e.g. `your-username/movie-recommendation`).

### 1. Prepare the repo for Streamlit Cloud

- **Requirements file**  
  Ensure `requirements.txt` is in the repo root and includes everything the app needs (e.g. `streamlit`, `pandas`, `scikit-learn`, `requests`, etc.). You already have this.

- **No local-only paths**  
  The app should read data from paths that exist in the deployed environment. Options:
  - **A)** Commit a **small dataset** (e.g. MovieLens 1M or a subset) under something like `data/raw/movielens/` and run the download script only for local/full data.
  - **B)** Or run `scripts/build_artifacts.py` **locally**, then commit the generated `data/processed/artifacts.pkl` (if not too large) and have the app load from that so the cloud app doesn’t need to build artifacts at startup.

- **Entrypoint**  
  Streamlit Cloud expects a command like:
  ```bash
  streamlit run app/streamlit_app.py
  ```
  So your app should be runnable as:
  ```bash
  streamlit run app/streamlit_app.py
  ```
  from the **repo root**. If your app assumes “project root = current working directory”, that’s the repo root on Streamlit Cloud.

- **Set TMDB key in the cloud**  
  You will set `TMDB_API_KEY` in the Streamlit Cloud dashboard (see below); do **not** commit the key.

### 2. Point Streamlit Cloud at your repo

1. Go to **https://share.streamlit.io** and sign in with GitHub.
2. Click **“New app”**.
3. **Repository:** `your-username/movie-recommendation` (or your repo name).  
4. **Branch:** `main` (or your default branch).  
5. **Main file path:** `app/streamlit_app.py`.  
6. **App URL:** optional subdomain, e.g. `movie-recommendation-app`.

### 3. Configure the run command and working directory

- **Run command (optional):** If you want to be explicit:
  ```bash
  streamlit run app/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
  ```
- **Working directory:** Leave as repo root (so `app/streamlit_app.py` and `src/` are where the app expects).

### 4. Add secrets (TMDB key)

1. In the app’s **“Settings”** or **“Secrets”**, add:
   ```toml
   TMDB_API_KEY = "your_actual_key_here"
   ```
2. Save. Streamlit Cloud injects this as an environment variable, so your existing code that uses `os.environ.get("TMDB_API_KEY")` will work.

### 5. Deploy and wait for build

- Click **Deploy**. Streamlit Cloud will:
  - Clone the repo
  - Install from `requirements.txt`
  - Run the streamlit command
- First run can take a few minutes (install + optional artifact building). If you committed precomputed `artifacts.pkl`, startup is faster.

### 6. Handle data size and cold starts

- If the repo is large (e.g. full MovieLens 25M CSV), consider:
  - Using a **subset** of the data in the repo, or
  - Building artifacts locally and committing only `data/processed/artifacts.pkl`, and not the raw CSVs.
- Free apps **sleep** when idle; the first visit after sleep will have a **cold start** (30 s–1 min). You can mention “Starts in ~30s after idle” in your portfolio.

### 7. Share the link

- After a successful deploy, you get a URL like:
  `https://movie-recommendation-app-xxxx.streamlit.app`
- Use this link on your resume and portfolio.

---

## Optional: Run command and `packages.txt` (Streamlit Cloud)

- If you use system libraries, add a **packages.txt** in the repo root listing them (one per line).
- Your app is pure Python + pip, so **requirements.txt** is enough.

If you want, the next step can be a minimal **Streamlit Cloud config** (e.g. `.streamlit/config.toml` for port/address) and a short **README section** that points to this deployment doc.
