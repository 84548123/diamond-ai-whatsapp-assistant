# DiamondAI WhatsApp Assistant - Junior Engineer Guide

## What This Is
A beautiful working demo of an AI WhatsApp assistant for diamonds.
- All common customer questions are trained
- Uses real stock data (32k+ diamonds)
- Shows instant replies with Rep No / Stone No

**Only 2 files matter for the demo:**
- `preview.html`
- `demo_stock.json`

No Docker. No databases. No complex stuff.

---

## Run Locally (One Command)

```bash
cd ai-whatsapp-assistant
./start.sh
```

Then open: http://localhost:8765/preview.html

All trained questions appear as clickable buttons under the chat box.

---

## Deploy to Internet (Pick One - All Free)

### 1. GitHub Pages (Recommended)
1. Push this folder to GitHub
2. Go to your repo → Settings → Pages
3. Source = "Deploy from a branch" → main → /root
4. Save
5. Wait 1 minute
6. Your link: https://yourname.github.io/repo/preview.html

### 2. Vercel (Super Easy)
1. Go to vercel.com → Login with GitHub
2. "Add New Project"
3. Pick your repo
4. Set "Root Directory" to `frontend/dist`
5. Click Deploy
6. Done

### 3. Netlify Drop (No account needed)
1. Go to https://app.netlify.com/drop
2. Drag the `frontend/dist` folder
3. Get instant live link

---

## That's It

A junior can do local run + deployment in < 10 minutes.

For real WhatsApp replies later, we can add the backend. For now, the preview is the main thing and is fully working.
