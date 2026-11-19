# Integración de utilidades BI para agentes de IA

## Objetivo

Integra únicamente las utilidades solicitadas y adáptalas a las convenciones del
proyecto receptor. La estructura de este repositorio es una referencia funcional,
no una arquitectura obligatoria. Conserva las interfaces públicas de `utils/`.

## Mapa de la implementación de referencia

| Ruta | Propósito |
|---|---|
| `config/settings.yaml` | Mapa central de rutas, timeouts, variables y opciones. |
| `.env` | Variables de conexión HANA y SMTP (no versionado; ver `.env.example`). |
| `utils/db_extractor/queries/example_query.sql` | Consulta de lectura sustituible. |
| `config/email_dispatcher/distribution_lists/example.txt` | Destinatarios `to`, `cc` y `cco`. |
| `config/email_dispatcher/body_template/example_body.html` | Contenido editable del correo. |
| `config/email_dispatcher/templates/default.html` | Estilo general y marcador `{{ body }}`. |
| `config/email_dispatcher/templates/assets/signature_logo.png` | Firma embebida mediante CID. |
| `example_use.py` | Ejemplo integral y prueba operativa. |

El flujo de referencia es:

```text
settings.yaml → .env → consulta SQL → DataFrame → TXT → correo → log
```

## Reglas de integración

1. Lee primero `config/settings.yaml` y `example_use.py` para entender las rutas
   y variables disponibles. No inventes configuraciones que ya estén definidas.
2. Importa solo desde `utils.<utilidad>`; no dependas de funciones privadas que
   comiencen con `_`.
3. Reutiliza la estructura y el gestor de dependencias del proyecto receptor.
   Usa `uv` cuando el proyecto no tenga otro estándar.
4. El `.env` contiene credenciales y no se versiona (base: `.env.example`). Puede
   cambiarse mediante `dot_env_root`. Nunca muestres sus valores, los escribas en
   logs ni los copies a código, YAML, documentación o respuestas.
5. Mantén las consultas en archivos `.sql`. `db_extractor` es únicamente para
   consultas que producen filas, no para escritura o control de transacciones.
6. En pruebas automatizadas simula bases y SMTP. Ejecuta consultas o envíos reales
   solo cuando el usuario solicite una verificación integral.
7. Cambia configuración e integración en el proyecto receptor antes de modificar
   el código compartido dentro de `utils/`.

## Integrar `yaml_loader`

Interfaz pública: `from utils.yaml_loader import read_yaml_value`.

Dependencia: `pyyaml>=6.0.2`.

1. Reutiliza un YAML existente o crea uno dentro de `config/`.
2. Lee claves con rutas como `database.query_path`.
3. Usa `must_exist=False` y `default=` solo para valores opcionales.
4. Informa al usuario qué archivo y claves debe editar.

## Integrar `log_factory`

Interfaces públicas: `from utils.log_factory import get_logger, purge_log_file`.

No requiere dependencias externas.

1. Usa `debug_mode=True` para consola o proporciona `log_dir` para archivo.
2. Ejecuta la purga antes de abrir el logger del mismo archivo.
3. `retention_days` debe ser un entero no negativo.
4. No registres credenciales, cadenas de conexión completas ni destinatarios
   sensibles.

## Integrar `db_extractor`

Interfaces públicas: `query_hana`, `query_mssql` y
`DatabaseAuthenticationError`, importadas desde `utils.db_extractor`.

Dependencias comunes: `pandas>=3.0.5` y `sqlalchemy>=2.0.52`.

Para HANA agrega `hdbcli>=2.29.25` y `sqlalchemy-hana>=4.6.1`. Para SQL Server
agrega `pyodbc>=5.3.0` y confirma el driver ODBC instalado.

1. Mantén la consulta en un archivo `.sql` y pasa su ruta a la función elegida.
2. Obtén la conexión desde el mecanismo de entorno del proyecto. En la referencia,
   `HANA_CONNECTION_STRING` se descompone con `sqlalchemy.engine.make_url()` y sus
   componentes se pasan a `query_hana()`.
3. Conserva timeouts configurables y captura `DatabaseAuthenticationError` sin
   revelar credenciales.
4. Para SQL Server adapta la configuración y llama `query_mssql()`; la ejecución
   exitosa de `example_use.py` valida HANA, no el driver de SQL Server.
5. Indica al usuario qué consulta, variable de conexión y driver debe proporcionar.

## Integrar `email_dispatcher`

Interfaz pública: `from utils.email_dispatcher import send_email`.

No requiere dependencias externas.

La estructura esperada bajo el `project_root` recibido es:

```text
config/email_dispatcher/
├── distribution_lists/example.txt
├── templates/default.html
├── templates/assets/signature_logo.png
└── body_template/example_body.html
```

1. Reutiliza esa estructura o cambia `email.project_root` y los nombres desde
   `settings.yaml`.
2. Construye `smtp_config` con variables de entorno. La referencia usa
   `BI_EMAIL_SMTP`, `BI_EMAIL_PORT`, `BI_EMAIL_USER` y `BI_EMAIL_PWD`.
3. Indica al usuario que edite la lista de distribución y el body. La lista usa
   `correo,to`, `correo,cc` o `correo,cco`.
4. Conserva `{{ body }}` en la plantilla y `cid:signature_logo` para la firma.
5. Verifica adjuntos y configuración antes de abrir la conexión SMTP.
6. No realices un envío real sin autorización explícita del usuario.

## Usar el ejemplo integral

Antes de ejecutarlo confirma:

1. `dot_env_root` apunta al `.env` autorizado.
2. `database.query_path` apunta a la consulta deseada.
3. La lista de distribución contiene destinatarios reales de prueba.
4. El body, asunto y plantilla son los esperados.

En Windows puede prepararse y ejecutarse con:

```text
poner a punto uv.bat
run_example_use.bat
```

De forma directa usa `uv sync` y después `uv run python example_use.py`.

Una ejecución exitosa confirma el flujo integrado de YAML, logging, HANA,
generación de TXT y correo SMTP. No confirma SQL Server si no se ejecutó una
prueba específica con `query_mssql()`.

## Entrega al usuario

Al terminar informa:

1. Utilidades integradas y archivos modificados.
2. Dependencias agregadas.
3. Ruta de configuración y variables utilizadas, sin mostrar sus valores.
4. Consulta, destinatarios o body que el usuario aún debe editar.
5. Pruebas ejecutadas y conexiones reales pendientes.

