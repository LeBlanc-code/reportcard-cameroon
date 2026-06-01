# Deployment Guide for Report Card Cameroon

This guide will help you deploy your Django app to a free hosting platform.

## **Setup Steps (Required for All Platforms)**

### 1. Create a GitHub Repository
```bash
git init
git add .
git commit -m "Initial commit"
```
Then push to GitHub (most platforms auto-deploy from GitHub).

### 2. Generate a Secret Key
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Save this value for later.

### 3. Prepare Environment Variables
Copy `.env.example` to `.env` and fill in:
- `SECRET_KEY`: Use the generated key above
- `DEBUG`: Set to `False`
- `ALLOWED_HOSTS`: Your domain name

---

## **Deploy to PythonAnywhere (Recommended)**

### Best For: Beginners, Django-specific features

**Pros:**
- Easiest Django deployment
- Free database included
- No credit card needed

**Steps:**

1. **Sign up:** https://pythonanywhere.com (free account)

2. **Upload code:**
   - Click "Upload a zip file" or use GitHub integration
   - Upload your project

3. **Create Web App:**
   - Go to "Web" tab → "Add a new web app"
   - Choose "Manual configuration" → Python 3.12
   - Set source code directory to your project folder

4. **Configure:**
   - Edit `/var/www/yourusername_pythonanywhere_com_wsgi.py`
   - Replace with this code:
   ```python
   import os
   import sys
   from pathlib import Path
   
   path = '/home/yourusername/reportcard_cameroon'
   if path not in sys.path:
       sys.path.append(path)
   
   os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

5. **Set Environment Variables:**
   - Go to "Web" → "Virtualenv"
   - Edit `~/.bashrc`:
   ```bash
   export SECRET_KEY="your-key-here"
   export DEBUG="False"
   export ALLOWED_HOSTS="yourusername.pythonanywhere.com"
   ```

6. **Install Dependencies:**
   - Open console
   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py collectstatic
   ```

7. **Reload:** Click reload button on Web tab

---

## **Deploy to Render**

### Best For: Modern deployment, GitHub integration

**Pros:**
- Auto-deploys on GitHub push
- Easy PostgreSQL setup
- Free tier generous

**Steps:**

1. **Push to GitHub** (required)

2. **Sign up:** https://render.com (free account)

3. **Create Web Service:**
   - Click "New" → "Web Service"
   - Connect your GitHub repo
   - Choose `main` branch

4. **Configure:**
   - **Name:** reportcard-cameroon
   - **Environment:** Python 3.12
   - **Build Command:**
   ```
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
   ```
   - **Start Command:**
   ```
   gunicorn config.wsgi:application
   ```

5. **Environment Variables:**
   - Add in Render dashboard:
   ```
   SECRET_KEY=your-generated-key
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.onrender.com
   ```

6. **Deploy:** Render automatically deploys on push to GitHub

---

## **Deploy to Railway**

### Best For: Generous free credits ($5/month)

**Pros:**
- $5/month free credits
- Easy to upgrade later
- PostgreSQL included

**Steps:**

1. **Sign up:** https://railway.app

2. **Connect GitHub** or upload project

3. **Add Services:**
   - Add PostgreSQL service
   - Add Web service pointing to your repo

4. **Configure Web Service:**
   - **Build Command:**
   ```
   pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
   ```
   - **Start Command:**
   ```
   gunicorn config.wsgi:application
   ```

5. **Set Environment Variables**

6. **Deploy:** Railway auto-deploys

---

## **Troubleshooting**

### Static Files Not Loading
- Run: `python manage.py collectstatic --noinput`
- Ensure WhiteNoise is installed in requirements.txt

### Database Migration Errors
- Check ALLOWED_HOSTS setting
- Run migrations: `python manage.py migrate`

### Secret Key Issues
- Generate new one: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

### 500 Error
- Check logs on hosting platform
- Ensure DEBUG=False and SECRET_KEY is set

---

## **Recommended Next Steps**

1. ✅ Choose a hosting platform (start with PythonAnywhere or Render)
2. ✅ Create GitHub repository
3. ✅ Generate SECRET_KEY
4. ✅ Test locally: `python manage.py runserver`
5. ✅ Deploy!

---

## **Custom Domain (Optional)**

Once deployed, you can add a custom domain:
- PythonAnywhere: $5/year
- Render/Railway: Free with DNS setup

Need help? Check platform documentation links above.
