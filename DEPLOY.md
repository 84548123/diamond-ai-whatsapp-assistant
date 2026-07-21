# DiamondAI WhatsApp Assistant — Deployment Guide (2026)

This project has **two deployable parts**:

1. **preview.html** (recommended first) — Beautiful, self-contained static demo  
   (Chat + 117 trained queries + real stock + **query-based lead assignment** to sales associates + emails)

2. **Backend** (FastAPI) — For **real** WhatsApp Cloud API + webhook

---

## 1. Deploy the Static Demo (preview.html) — Easiest & Recommended

The demo is 100% static (HTML + JS + JSON). No server needed.

### Option A: GitHub Pages (Free, Recommended)

1. Push the entire `ai-whatsapp-assistant` folder to a GitHub repo.
2. Go to your repo → **Settings** → **Pages**
3. Under "Build and deployment":
   - Source: **Deploy from a branch**
   - Branch: `main`
   - Folder: `/ (root)`
4. Save
5. Wait ~1 minute
6. Your live link will be:  
   `https://YOUR-USERNAME.github.io/YOUR-REPO/preview.html`

**Pro tip**: Add a `CNAME` or custom domain later.

### Option B: Vercel (Fastest)

1. Go to [vercel.com](https://vercel.com) → Login with GitHub
2. **Add New Project**
3. Select your repo
4. **Root Directory**: leave as `/` (or set to `.`)
5. Click **Deploy**
6. Done — instant live link

(You can also set "Output Directory" to `frontend/dist` if you want.)

### Option C: Netlify (Drag & Drop — No Git needed)

1. Go to https://app.netlify.com/drop
2. Drag the entire `frontend/dist` folder (or the root folder)
3. Get instant public URL

### Option D: Any Static Host

Upload these **two files**:
- `preview.html`
- `demo_stock.json`

To any of these:
- Cloudflare Pages
- Surge.sh
- Firebase Hosting
- Render Static Sites

---

## 2. Deploy the Real WhatsApp Backend (for live customers)

### Prerequisites
- Meta WhatsApp Business API credentials (see section below)
- GitHub repo (recommended)

### Best Free Option: Render.com

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Settings:
   - **Name**: `diamondai-whatsapp`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add these **Environment Variables**:

   ```
   WHATSAPP_ACCESS_TOKEN=your_meta_token_here
   WHATSAPP_PHONE_NUMBER_ID=your_phone_id_here
   WHATSAPP_VERIFY_TOKEN=diamond-verify-2026
   GEMINI_API_KEY=optional
   ENV=production
   ```

6. Click **Create Web Service**
7. Copy your public URL (e.g. `https://diamondai-whatsapp.onrender.com`)

### Prevent Sleeping (Free Tier)
Add a free pinger:
- Go to https://uptimerobot.com
- Add HTTP monitor to your Render URL every 5 minutes

---

## 3. Get Meta WhatsApp Credentials (5 minutes)

1. Go to https://developers.facebook.com/
2. Create a **Business App**
3. Add product → **WhatsApp**
4. In left sidebar:
   - **WhatsApp → API Setup**
5. Note these values:
   - **Phone Number ID**
   - **Access Token** (click **Generate**)
6. Create your own **Verify Token** (example: `diamond-verify-2026`)

---

## 4. Connect Webhook (Real WhatsApp)

In Meta Developers Dashboard:

1. Go to **WhatsApp → Configuration**
2. **Callback URL**:  
   `https://YOUR-RENDER-URL.onrender.com/api/v1/whatsapp/webhook`
3. **Verify Token**: `diamond-verify-2026`
4. Click **Verify and Save**
5. Under **Webhook fields**, subscribe to **messages**

---

## 5. Test Everything

### Test Static Demo
Open your deployed `preview.html` link and:
- Type `1529267932`
- Click trained buttons
- Click "Assign Demo Lead"
- Check team workload + leads table

### Test Real WhatsApp
Send these messages from your phone to the WhatsApp Business number:

```
Send ur list
LGOV90-2946 Available ?
what price can do
HK delivery u do?
Can i get a twizzer or shade card video?
```

You should get instant professional replies.

---

## 6. Quick Local Testing (Before Deploy)

```bash
cd ai-whatsapp-assistant

# Static demo
./start.sh
# Open http://localhost:8765/preview.html

# Backend (for WhatsApp testing)
cd backend
pip install -r requirements.txt

# Create .env (copy from docs or create manually)
uvicorn app.main:app --reload --port 8000

# In another terminal
ngrok http 8000
```

---

## 7. What Gets Deployed Where

| Part                    | Where to Deploy     | Files Needed                     | Public URL Needed? |
|-------------------------|---------------------|----------------------------------|--------------------|
| Demo (preview)          | GitHub / Vercel / Netlify | `preview.html` + `demo_stock.json` | No                 |
| Real WhatsApp Backend   | Render.com          | `backend/` folder                | Yes                |
| Full stack (future)     | Same as above       | Both                             | Yes                |

---

## 8. Post-Deployment Checklist

- [ ] Static demo loads and chat works
- [ ] Stock search works
- [ ] Lead assignment + emails visible
- [ ] Real WhatsApp webhook verified in Meta
- [ ] Test messages return correct replies
- [ ] UptimeRobot added (for Render)
- [ ] (Optional) Add your custom domain

---

## Next Level (Optional)

Want me to add:
- Real query-based lead assignment inside the backend webhook (so every WhatsApp lead gets assigned to Priya / Rahul / Anjali etc. with email)
- Daily message counter
- Better logging / lead export endpoint

Just say the word.

---

**You're ready to go live in < 15 minutes.**

The `preview.html` is already the complete sales demo with client bifurcation. Deploy it first, then connect the backend when you're ready for real customers.