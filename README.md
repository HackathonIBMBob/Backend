# Legacy Whisperer Backend

Backend en FastAPI para ingerir un repositorio, analizarlo con IBM watsonx, generar una versión modernizada del código y exponer los artefactos resultantes por API.

## Qué hace

- Ingiere un repositorio desde un `.zip`, una URL pública de GitHub o una ruta local.
- Detecta archivos de código soportados: `py`, `java`, `php`, `js`, `ts`, `cs`, `go`, `rb`.
- Ejecuta un pipeline asíncrono de análisis, refactorización y documentación.
- Genera una carpeta clonada con los archivos modernizados.
- Expone un `.zip` descargable del resultado final.
- Intenta generar un `report.docx` con resumen de cambios. Si falla esa parte, el pipeline continúa.

## Stack

- Python
- FastAPI
- Uvicorn
- IBM `ibm-watsonx-ai`
- GitPython
- Node.js opcional para el reporte `.docx`

## Estructura

```text
.
├── ai_pipeline/         # Orquestación de análisis, refactor y documentación
├── models/              # Schemas Pydantic
├── routers/             # Endpoints FastAPI
├── services/            # Ingesta, parsing, pipeline, transformaciones
├── uploads/             # Artefactos temporales por job
├── main.py              # Entrada de la API
├── requirements.txt
└── .env.example
```

## Requisitos

- Python 3.10+
- `git` instalado si vas a usar ingestión desde GitHub
- Node.js y paquete global `docx` solo si quieres generar `report.docx`

## Configuración

1. Crea y activa un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instala dependencias:

```bash
pip install -r requirements.txt
```

3. Crea tu archivo de entorno:

```bash
cp .env.example .env
```

4. Completa las variables:

```env
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_APIKEY=tu_api_key
WATSONX_PROJECT_ID=tu_project_id
```

## Ejecución

```bash
uvicorn main:app --reload
```

API local:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Flujo de uso

1. Ingerir repositorio.
2. Guardar el `job_id` devuelto.
3. Lanzar la modernización usando ese `job_id`.
4. Consultar el estado hasta que termine.
5. Descargar el `.zip` y, si existe, el `.docx`.

## Endpoints principales

### Health check

```http
GET /
```

Respuesta:

```json
{
  "status": "ok",
  "service": "Legacy Whisperer"
}
```

### Estado de un job

```http
GET /status/{job_id}
```

### Ingestar un ZIP

```http
POST /ingest
Content-Type: multipart/form-data
```

Ejemplo:

```bash
curl -X POST "http://127.0.0.1:8000/ingest" \
  -F "file=@repo.zip"
```

### Ingestar desde GitHub

```http
POST /ingest/github
Content-Type: application/json
```

```json
{
  "github_url": "https://github.com/owner/repo"
}
```

### Ingestar desde ruta local

```http
POST /ingest/local
Content-Type: application/json
```

```json
{
  "local_path": "/ruta/al/repositorio"
}
```

### Lanzar modernización

```http
POST /modernize
POST /modernize/full-repo
Content-Type: application/json
```

```json
{
  "job_id": "job-id-devuelto-por-ingest"
}
```

### Descargar resultados

```http
GET /download/zip/{job_id}
GET /download/docx/{job_id}
```

## Estados del pipeline

El job expone progreso y etapa (`stage`). Las etapas observables incluyen:

- `queued`
- `loading repo`
- `analyzing code`
- `refactoring code`
- `generating documentation`
- `modernizing files`
- `generating report`
- `writing output`
- `completed`
- `failed`

## Artefactos generados

Durante la ejecución se usa `uploads/<job_id>/` como almacenamiento temporal. Al finalizar:

- Se crea un `.zip` descargable con el repositorio modernizado.
- Se intenta crear `report.docx`.
- Se genera también un `bob_report.json` dentro de la salida modernizada.

Si la ingestión fue por ruta local, la carpeta modernizada se escribe junto al repositorio original con sufijo `_modernized`, `_modernized_2`, etc.

## Notas operativas

- Los jobs se guardan en memoria; si el proceso se reinicia, se pierde su estado.
- La clonación GitHub soporta repositorios públicos.
- El pipeline ignora archivos no soportados o demasiado grandes.
- La generación de `report.docx` es opcional: si `node` o `docx` no están disponibles, el proceso principal no falla.

## Utilidad adicional

`list_models.py` permite listar modelos disponibles en watsonx para cambiar el `MODEL_ID` usado por `services/bob_client.py`.

Ejemplo:

```bash
python list_models.py --filter llama
```
