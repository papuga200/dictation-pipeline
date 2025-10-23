# Environment Variables Setup

## Quick Setup

### 1. Create `.env` file

Copy the example file:

```bash
# Copy the example
cp .env.example .env
```

Or create manually:

```bash
# Create new file
echo "XAI_API_KEY=your-api-key-here" > .env
```

### 2. Add your API key

Edit `.env` and replace `your-api-key-here` with your actual xAI API key:

```
XAI_API_KEY=xai-abc123def456...
```

### 3. Get your API key

1. Visit: https://console.x.ai/
2. Sign up or log in
3. Navigate to "API Keys"
4. Create a new API key
5. Copy the key to your `.env` file

### 4. Test it works

```bash
python demo_grok_alignment.py
```

## How It Works

The `.env` file is loaded by `python-dotenv` library:

```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env file into environment

# Now os.getenv() can read the values
api_key = os.getenv("XAI_API_KEY")
```

## Security Notes

- ⚠️ **Never commit `.env` files to git** (already in `.gitignore`)
- ✅ Share `.env.example` as a template (no secrets)
- ✅ Each developer creates their own `.env` file locally

## Alternative Methods

### Option A: Set in PowerShell (Windows)

```powershell
$env:XAI_API_KEY='your-api-key-here'
python demo_grok_alignment.py
```

This only lasts for the current PowerShell session.

### Option B: Set in Bash (Linux/Mac)

```bash
export XAI_API_KEY='your-api-key-here'
python demo_grok_alignment.py
```

This only lasts for the current terminal session.

### Option C: Set permanently in Python

Edit your script to set it directly (not recommended for production):

```python
import os
os.environ['XAI_API_KEY'] = 'your-api-key-here'
```

## Troubleshooting

### "XAI_API_KEY not set" error

1. Check `.env` file exists in project root
2. Check `.env` has correct format: `XAI_API_KEY=your-key`
3. Check no spaces around `=`: `KEY=value` not `KEY = value`
4. Try running `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('XAI_API_KEY'))"`

### .env file not loading

1. Ensure `python-dotenv` is installed: `pip install python-dotenv`
2. Check the script calls `load_dotenv()` at the top
3. Verify `.env` is in the same directory where you run the script

### Still not working?

Set it directly in your terminal before running:

**PowerShell:**
```powershell
$env:XAI_API_KEY='your-key-here'
```

**Bash:**
```bash
export XAI_API_KEY='your-key-here'
```

Then immediately run your script in the same terminal window.

