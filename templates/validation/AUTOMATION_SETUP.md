# Hermes - Validation Automation Setup

## Architecture

```
Landing Page (HTML/JS)
    |
    v
Supabase API (REST) ---> PostgreSQL Table
    |
    +---> Realtime dashboard (HTML)
    +---> Python analytics script
    +---> Discord webhook alerts (optional)
```

## Method A: AI-Assisted with Supabase MCP (FASTEST - 2 minutes)

If your IDE supports MCP (Cursor, Claude, Windsurf):

1. **Configure MCP** (one-time):
   ```json
   {
     "mcpServers": {
       "supabase": {
         "type": "http",
         "url": "https://mcp.supabase.com/mcp"
       }
     }
   }
   ```

2. **Ask your AI assistant**:
   ```
   "Create a Supabase project named 'hermes-validation', 
   execute the SQL from supabase-schema.sql, 
   then give me the Project URL and Anon Key"
   ```

3. **The AI will**:
   - Create the project (after you authenticate via browser once)
   - Execute all SQL statements
   - Extract and provide the keys
   - Verify the table exists

## Method B: Manual Setup (5 minutes)

1. Go to https://supabase.com
2. Sign up / sign in
3. Create new project: `hermes-validation`
4. Choose region: closest to users
5. Open SQL Editor, run: `supabase-schema.sql`
6. Copy Project URL + Anon Key from Settings > API

## 3. Configure Landing

Edit `landing/config.js`:

```javascript
window.HERMES_SUPABASE_URL = "https://xxxx.supabase.co";
window.HERMES_SUPABASE_KEY = "eyJ...";
```

## 4. Deploy

Upload `landing/` folder to Netlify Drop (or any static host).

## 5. View Responses

Open `dashboard.html` from the deployed site.

## 6. Export/Analyze

```bash
# Set env vars
export HERMES_SUPABASE_URL="https://xxxx.supabase.co"
export HERMES_SUPABASE_KEY="eyJ..."

# Run analytics
python scripts/analyze_responses.py
```

## MCP Capabilities

With Supabase MCP configured, your AI can:
- `create_project` - Create new projects
- `execute_sql` - Run schema SQL
- `list_tables` - Verify structure
- `get_project_url` / `get_publishable_keys` - Extract config
- `apply_migration` - Deploy updates

## Cost

Supabase free tier: 500MB, 75K connections/day. More than enough for validation phase.
