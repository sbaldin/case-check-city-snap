# Gateway Service (FastAPI)

Minimal FastAPI gateway for Guide-Architect.

## Endpoints
- GET /api/v1/health — simple health check.
- POST /api/v1/building/info — accepts JSON with address, coordinates and/or image_base64 and returns a stubbed building info response.

## Init Poetry in this folder with an in-project virtualenv (.venv)

This service is set up to keep its virtualenv inside the `gateway_service` folder.
The `poetry.toml` here already enforces that:

```
[virtualenvs]
in-project = true
package-mode = false
```

Quick start:

1) Ensure Poetry is installed (see https://python-poetry.org/docs/#installation).

2) From the repo root, change into this service folder:

```
cd gateway_service
```

3) Select the Python you want (for example Python 3.10) and create the in-folder venv:

```
poetry env use python3.10
```

4) Install dependencies (this will create `.venv/` inside `gateway_service`):

```
poetry install
```

5) (Optional) Activate the venv in your shell:

- Bash/Zsh:
  
  ```
  source .venv/bin/activate
  ```

- Fish:
  
  ```
  source .venv/bin/activate.fish
  ```

You can also avoid manual activation by always prefixing commands with `poetry run`.

## Run (dev)

- With uvicorn directly:

```
poetry run uvicorn citysnap.app.main:app --reload --port 8081
```

- Or via the Poetry script (defined in pyproject.toml as `api`):

```
poetry run api
```
