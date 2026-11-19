# Utilidades BI: guía rápida

Estas utilidades se copian dentro de un proyecto y pueden adaptarse con ayuda de
un agente de IA.

| Utilidad | Qué hace |
|---|---|
| `yaml_loader` | Lee valores de configuración desde archivos YAML. |
| `log_factory` | Crea logs en consola o archivo y elimina registros antiguos. |
| `db_extractor` | Ejecuta consultas `.sql` en HANA o SQL Server y devuelve un DataFrame. |
| `email_dispatcher` | Envía correos HTML con destinatarios, firma y adjuntos. |

Para comenzar, dile a tu agente:

> Lee `utils/UTILS_README_AGENTS.md` e integra la utilidad `<nombre>` en este proyecto.

El repositorio incluye `example_use.py`, un ejemplo funcional que lee
`config/settings.yaml`, carga `.env`, consulta HANA, genera un TXT y lo envía por
correo.

## Preguntas útiles para tu agente

1. “Dame un resumen de los tests que pasan las utilidades.”
2. “¿Puedo enviar un archivo Excel como adjunto y cómo lo configuro?”
3. “¿Qué archivos y variables debo cambiar para usar mi consulta?”
4. “Integra `<utilidad>` respetando la estructura actual de mi proyecto.”
