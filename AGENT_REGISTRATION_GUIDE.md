# Agent Registration Guide

This guide shows how to register your MCP server in Agent Bricks and capture evidence for grading.

## Prerequisites

1. **MCP Server Deployed**: Your `weather-mcp-server` app must be running
   ```bash
   databricks apps get weather-mcp-server
   ```
   Status should show `RUNNING`

2. **App URL**: Note the URL from the command above
   ```
   https://<workspace-id>.cloud.databricks.com/apps/weather-mcp-server
   ```

---

## Step 1: Register MCP Server as External Tool

### Navigate to Agent Bricks

1. Open your Databricks workspace
2. Go to **AI Playground** or **Agent Bricks** (usually in left sidebar under "Machine Learning" or "AI")
3. Alternative URL: `https://<workspace>.cloud.databricks.com/ml/playground`

### Register the MCP Server

1. Click **"Tools"** or **"External Tools"** tab at the top
2. Click **"+ Add External Tool"** or **"+ New Tool"**
3. Select **"MCP Server"** from the tool type dropdown

4. **Fill in the MCP Server details:**
   - **Name**: `Weather MCP Server` (or descriptive name)
   - **Description**: `Weather data from National Weather Service via MCP`
   - **URL**: `https://<workspace-id>.cloud.databricks.com/apps/weather-mcp-server`
   - **Authentication**: `None` (or select your workspace auth)

5. Click **"Discover Tools"** or **"Connect"**
   - The system will query your MCP server's tool list
   - You should see 3 tools appear:
     - `get_current_weather_by_location`
     - `get_weather_forecast_by_location`
     - `predict_umbrella_needed_by_location`

6. Click **"Register"** or **"Save"**

### 📸 IMPORTANT: Capture Screenshot #1

**What to capture:**
- The **"External Tools"** page showing your registered MCP server
- Make sure visible:
  - MCP server name ("Weather MCP Server")
  - MCP server URL
  - Status ("Connected" or similar)
  - The 3 discovered tools listed

**Filename:** `screenshots/mcp_server_registration.png`

---

## Step 2: Create Weather Assistant Agent

### Create New Agent

1. In Agent Bricks/Playground, click **"+ New Agent"** or **"Create Agent"**
2. **Name**: `Weather Assistant`
3. **Description**: `Provides weather forecasts and umbrella recommendations`

### Configure System Prompt

1. Find the **"System Prompt"** or **"System Instructions"** field
2. Copy the entire content from `SYSTEM_PROMPT.md`
3. Paste it into the field
4. Verify it includes:
   - Tool descriptions
   - 40% umbrella threshold explanation
   - Error handling guidelines
   - Supported cities list

### Attach Tools

1. Find the **"Tools"** section in agent configuration
2. Click **"+ Add Tool"** or similar
3. Select **"Weather MCP Server"** (the one you just registered)
4. Check all 3 tools:
   - ☑ `get_current_weather_by_location`
   - ☑ `get_weather_forecast_by_location`
   - ☑ `predict_umbrella_needed_by_location`
5. Click **"Add"** or **"Attach"**

### Select Model

1. Choose your LLM model (you mentioned using Llama)
2. Recommended: `llama-3.1-70b` or `llama-3.3-70b` for tool calling
3. Temperature: `0.7` (default)

### Save Agent

1. Click **"Save"** or **"Create Agent"**
2. You should see a success message

### 📸 IMPORTANT: Capture Screenshot #2

**What to capture:**
- The **"Agent Configuration"** page showing:
  - Agent name ("Weather Assistant")
  - System prompt (first few lines visible)
  - **Attached tools section** showing the 3 weather tools
  - Model selection (e.g., "llama-3.1-70b")

**Filename:** `screenshots/agent_configuration.png`

---

## Step 3: Test the Agent

### Run Test Queries

1. Open the **"Chat"** or **"Test"** interface for your agent
2. Run at least 3 different queries (see examples below)
3. **IMPORTANT**: Capture screenshots showing:
   - User question
   - Tool call made by agent (with parameters)
   - Tool response received
   - Agent's final answer

### Test Query Examples

#### Test 1: Current Weather
**User Input:**
```
What's the weather in Boston?
```

**What to verify:**
- Agent calls `get_current_weather_by_location`
- Parameters: `{"city": "Boston, MA"}`
- Response includes temperature, precipitation, wind
- Agent provides conversational summary

#### Test 2: Umbrella Prediction
**User Input:**
```
Should I bring an umbrella to Austin tomorrow?
```

**What to verify:**
- Agent calls `predict_umbrella_needed_by_location`
- Parameters include correct city and date
- Response mentions 40% threshold
- Agent gives yes/no recommendation

#### Test 3: Multi-Day Forecast
**User Input:**
```
Give me the 3-day forecast for Denver
```

**What to verify:**
- Agent calls `get_weather_forecast_by_location`
- Parameters: `{"city": "Denver, CO", "days": 3}`
- Response contains multiple forecast periods
- Agent summarizes daily highs/lows

### 📸 IMPORTANT: Capture Screenshots #3-5

**For EACH test query, capture:**
- Full conversation showing:
  - Your question
  - Agent's tool call (expand "Tool Calls" section if collapsed)
  - Tool response data
  - Agent's final answer

**Filenames:**
- `screenshots/test_current_weather.png`
- `screenshots/test_umbrella_prediction.png`
- `screenshots/test_forecast.png`

---

## Step 4: Capture Additional Evidence

### MCP Server Logs

Capture logs showing tool calls being received:

```bash
databricks apps logs weather-mcp-server --tail 50
```

**Save output to:** `screenshots/mcp_server_logs.txt`

### App Status

Capture full app configuration:

```bash
databricks apps get weather-mcp-server
```

**Save output to:** `screenshots/app_status.txt`

---

## Evidence Checklist

Before submitting, ensure you have:

### ☑ Required Screenshots

1. **MCP Server Registration** (`screenshots/mcp_server_registration.png`)
   - Shows MCP server URL
   - Shows 3 tools discovered
   - Shows "Connected" status

2. **Agent Configuration** (`screenshots/agent_configuration.png`)
   - Shows agent name and system prompt
   - Shows 3 weather tools attached
   - Shows model selection

3. **Test 1 - Current Weather** (`screenshots/test_current_weather.png`)
   - User question visible
   - Tool call with parameters visible
   - Tool response visible
   - Agent answer visible

4. **Test 2 - Umbrella Prediction** (`screenshots/test_umbrella_prediction.png`)
   - Complete conversation visible
   - Tool call shows date parameter
   - 40% threshold mentioned

5. **Test 3 - Forecast** (`screenshots/test_forecast.png`)
   - Complete conversation visible
   - Tool call shows days=3 parameter
   - Multi-period forecast visible

### ☑ Optional but Recommended

6. **Error Handling Test** (`screenshots/test_error_handling.png`)
   - Query for unsupported city (e.g., Seattle)
   - Shows agent lists 5 supported cities
   - Shows graceful error handling

7. **MCP Server Logs** (`screenshots/mcp_server_logs.txt`)
   - Shows incoming tool requests
   - Shows successful responses

8. **App Status** (`screenshots/app_status.txt`)
   - Shows app URL
   - Shows RUNNING status
   - Shows app configuration

---

## Screenshot Best Practices

### For UI Screenshots

1. **Use full browser window** - Show address bar with Databricks URL
2. **Expand all relevant sections** - Tool calls, tool responses, etc.
3. **Zoom to readable text** - 100% or 125% browser zoom
4. **Include timestamps** - If visible, include to show real-time testing
5. **Annotate if needed** - Draw boxes/arrows to highlight key elements

### For Text Output

1. **Copy full output** - Don't truncate
2. **Include command** - Show what command you ran
3. **Include timestamp** - When the output was captured
4. **Format as code block** - Use markdown ```bash ``` formatting

---

## Alternative: Video Walkthrough

Instead of screenshots, you can record a short video (2-3 minutes) showing:

1. MCP server registration in Agent Bricks
2. Agent configuration with tools attached
3. Running 3 test queries with visible tool calls
4. Agent providing correct responses

**Upload to:**
- YouTube (unlisted link)
- Loom
- Databricks Notebooks (embedded video)

**Include video link in:** `DEMONSTRATION.md` or `README.md`

---

## Troubleshooting

### Tools Not Discovered

**Problem:** "No tools found" when registering MCP server

**Solutions:**
1. Check app status: `databricks apps get weather-mcp-server`
2. Verify app is RUNNING (not STOPPED)
3. Test MCP endpoint directly:
   ```bash
   curl -X POST https://<workspace>/apps/weather-mcp-server/mcp/v1/list_tools
   ```
4. Check logs: `databricks apps logs weather-mcp-server`
5. Restart app: `databricks apps restart weather-mcp-server`

### Agent Not Calling Tools

**Problem:** Agent responds without calling tools

**Solutions:**
1. Verify tools are **attached** in agent config (not just registered)
2. Check system prompt is loaded correctly
3. Try more explicit query: "Use the get_current_weather tool for Boston"
4. Switch to a different model (some models have better tool calling)

### Tool Calls Failing

**Problem:** Tool calls return errors or timeout

**Solutions:**
1. Check database connection: `weather_forecast` table populated
2. Verify Databricks secrets are set: `database` scope, `lakebase-url` key
3. Check app logs for Python errors
4. Run notebook cells 11-12 to refresh forecast data

---

## Summary

For grading, you MUST provide:

1. **Evidence of MCP server registration** (screenshot or config export)
2. **Evidence of agent configuration** (screenshot showing tools attached)
3. **3+ demonstration transcripts** (screenshots or `DEMONSTRATION.md`)
4. **Deployment artifacts** (`mcp_server/requirements.txt`, `mcp_server/app.yaml`)

All evidence should be in a `screenshots/` folder or linked in the README.

---

**Last Updated:** August 18, 2026