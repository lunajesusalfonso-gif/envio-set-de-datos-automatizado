# Envío de set de datos automatizado

Proceso en Python que, una vez al día, ejecuta una consulta SQL sobre SAP HANA, guarda el resultado en CSV, lo comprime en ZIP y lo envía por correo (SMTP) a una lista de distribución. Se programa en Windows con el Programador de tareas.

```text
.env → consulta SQL (HANA) → DataFrame → CSV → ZIP → correo con firma → log
```

## Estructura

| Ruta | Propósito |
|---|---|
| `main.py` | Orquesta el proceso completo. |
| `main.ps1` | Ejecuta `main.py` con el Python del entorno virtual y guarda la salida de consola en `log/`. |
| `register_task.ps1` | Registra la tarea diaria en el Programador de tareas de Windows. |
| `0-bi-utils/utils/` | Utilidades reutilizables: `db_extractor`, `email_dispatcher`, `log_factory`, `yaml_loader`. |
| `0-bi-utils/.env.example` | Plantilla de variables de conexión. |
| `src/queries/sell_out.example.sql` | Plantilla de la consulta. |
| `config/email_dispatcher/` | Plantillas HTML, cuerpo del correo, firma y listas de distribución. |

## Configuración

1. **Dependencias** (Python 3.12+):
   ```powershell
   python -m venv .venv
   .venv\Scripts\pip install -r 0-bi-utils\requirements.txt
   ```
2. **Credenciales:** copia `0-bi-utils/.env.example` como `0-bi-utils/.env` y llena los valores.
3. **Consulta:** copia `src/queries/sell_out.example.sql` como `src/queries/sell_out.sql` y escribe tu consulta.
4. **Destinatarios:** crea `config/email_dispatcher/distribution_lists/buen_fin.txt` con una línea por destinatario en formato `correo,to|cc|cco` (ver `example.txt`).
5. **Firma:** reemplaza `config/email_dispatcher/templates/assets/signature_logo.png` por tu logo.

## Ejecución

```powershell
# Manual
powershell -ExecutionPolicy Bypass -File .\main.ps1

# Programada (una vez, como Administrador)
powershell -ExecutionPolicy Bypass -File .\register_task.ps1
```

`main.ps1` usa `.venv\Scripts\python.exe`; para otro intérprete define la variable de entorno `HOTSALE_PYTHON`.

## Seguridad

`.gitignore` excluye el `.env`, las consultas productivas (`src/queries/*.sql`, salvo los `*.example.sql`), las listas de distribución reales, los datos generados (`data/`, `*.csv`, `*.zip`) y los logs.
