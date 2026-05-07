# Campspotter server

## Setup intructions

### Installing uv
Install uv. For more details refer to this [guide](https://docs.astral.sh/uv/getting-started/installation/).

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ensure you have the latest version
`uv self update`
```bash
info: Checking for updates...
success: Upgraded uv from v0.11.6 to v0.11.7! https://github.com/astral-sh/uv/releases/tag/0.11.7
```

And now simply run:  
`uv sync`

Now create the requirements.txt file using the command
`uv pip compile pyproject.toml -o requirements.txt`

Once this has run successfully you can start the server 
```bash
uv run python server.py
```

If all is well, you will see

```bash
Installed 1 package in 4ms
2026-04-25 10:40:36,404 [DEBUG] Using selector: KqueueSelector
INFO:     Started server process [84816]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```