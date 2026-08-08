# Weather Retrieval Service - Deployment Guide

## 🔧 Latest Fixes Applied

✅ **Explicit template folder path** - Flask now finds templates correctly
✅ **Fallback inline HTML** - If templates fail, serves HTML directly  
✅ **Debug endpoint added** - `/debug` shows diagnostic information
✅ **Enhanced logging** - Better startup messages in logs

## 🚀 Deployment Steps

### 1. Push Updated Code to GitHub

```bash
cd Weather-Retrieval-Service
git add .
git commit -m "Fix app deployment with template fallback and debugging"
git push
```

### 2. Redeploy in Databricks

Your app should auto-redeploy if configured, or manually redeploy via:
- Databricks UI: **Compute** → **Apps** → Find your app → **Redeploy**
- CLI: `databricks apps update <app-name>`

### 3. Wait for Startup (2-3 minutes)

The app needs time to:
- Download dependencies (~1 min)
- Download embedding model (~1 min)  
- Start Flask server (~30 sec)

## 🧪 Testing Your Deployed App

### Your App URL Format:
```
https://<workspace-url>/apps/<app-name>
```

### Test These Endpoints:

#### 1. **Root Page** (should show HTML interface)
```
GET https://<workspace-url>/apps/<app-name>/
```
Expected: HTML page with search form

#### 2. **Health Check** (verify app is running)
```
GET https://<workspace-url>/apps/<app-name>/health
```
Expected: `{"status": "healthy", "model": "all-MiniLM-L6-v2"}`

#### 3. **Debug Info** (NEW - diagnose issues)
```
GET https://<workspace-url>/apps/<app-name>/debug
```
Expected: JSON with deployment details, file paths, environment

#### 4. **Search** (test the main feature)
```bash
curl -X POST https://<workspace-url>/apps/<app-name>/weather/search \
  -H "Content-Type: application/json" \
  -d '{"query": "risk of flooding near rivers", "top_k": 5}'
```
Expected: JSON with search results

## 🐛 Troubleshooting

### Issue: "App not found" or 404

**Check:**
1. Correct app URL in browser
2. App status is "Running" in Databricks UI
3. Try with `/health` appended to URL

### Issue: Blank page or "Cannot GET /"

**Solution:** The latest code has fallback HTML. If still blank:
1. Check `/debug` endpoint to see diagnostic info
2. View app logs in Databricks UI
3. Verify templates folder is in GitHub repo

### Issue: 500 Internal Server Error

**Check:**
1. `/debug` endpoint for error details
2. Lakebase secret is properly configured
3. App logs in Databricks UI

### Issue: Search returns empty results

**This is expected if:**
- Your `weather_alert_documents` table is empty
- Your `weather_alert_embeddings` table is empty  
- You haven't run Parts 1 & 2 of the assignment

The app will return:
```json
{
  "results": [],
  "message": "No results found. The weather_embeddings table may be empty..."
}
```

## 📊 Expected App Logs

When app starts successfully, you should see:

```
============================================================
🚀 Weather Retrieval Service Starting...
============================================================
📁 Template directory: /path/to/templates
📦 Loading embedding model (may take 30-60 seconds on first run)...
✅ Embedding model loaded in 45.2s
🎉 Service ready!
============================================================
 * Running on http://0.0.0.0:8080
```

## 🎯 Next Steps After Successful Deployment

1. ✅ Visit root URL - should see the landing page
2. ✅ Test `/health` - should return healthy status
3. ✅ Test `/debug` - verify all paths are correct
4. ✅ Test `/weather/search` with sample query
5. ✅ Verify search returns results (or empty if no data)

## 📝 Notes

- **First deployment** takes longer (downloads 80MB model)
- **Subsequent restarts** are faster (model cached)
- **Templates folder** must be in your GitHub repo
- **Fallback HTML** ensures you always see something

---

## 🆘 Still Having Issues?

If none of the above works:

1. Share the output from `/debug` endpoint
2. Share any error messages from app logs  
3. Confirm app status is "Running" in Databricks UI
4. Verify GitHub repo has all files (app.py, app.yaml, requirements.txt, templates/)
