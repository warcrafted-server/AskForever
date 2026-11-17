# Claves de IA gratuitas: dónde crearlas (ES)

**[English version](API_KEYS.md)**

> AskForever App permite configurar actualmente Google Gemini. Los demás servicios aparecen abajo como referencia. Cada jugador necesita su propia clave. Los planes gratuitos y sus límites cambian a menudo: mira la consola de cada servicio para ver tus límites reales. Para Gemini hay una [guía paso a paso](CLAVE_GEMINI.md) más detallada.

| Servicio | Dónde crear la clave | Documentación oficial | Notas |
|---|---|---|---|
| **Google Gemini** | [aistudio.google.com](https://aistudio.google.com) → Dashboard → Claves de API → **Crear clave de API** | [Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) | Es el predeterminado de AskForever. En el plan gratuito Google puede usar tus consultas para mejorar sus productos |
| **Groq** | [console.groq.com/keys](https://console.groq.com/keys) | [Quickstart](https://console.groq.com/docs/quickstart) | Las claves pertenecen a un proyecto; solo propietarios del equipo y desarrolladores pueden crearlas |
| **Mistral** | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys) → **New key** | [Create your first API key](https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key) | La clave completa se muestra una sola vez: cópiala enseguida. El plan gratuito Experiment puede usar las consultas para entrenar sus modelos ([detalles](https://help.mistral.ai/en/articles/450104-how-can-i-try-the-api-for-free-with-the-experiment-plan)) |
| **Cerebras** | [cloud.cerebras.ai](https://cloud.cerebras.ai) → **API Keys** → **Generate API Key** | [API keys](https://inference-docs.cerebras.ai/console/api-keys) | Las cuentas de prueba gratuita no tienen proyectos |
| **OpenRouter** | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | [Quickstart](https://openrouter.ai/docs/cookbook/get-started/quickstart) | Una clave sirve para modelos gratuitos y de pago; los gratuitos terminan en `:free` y tienen límites diarios bajos |

## Introducir la clave en AskForever App

No pegues nunca una clave en chats, correos ni documentos. Para introducir una clave de Gemini en AskForever App, pulsa **Configurar IA**, escribe la clave y pulsa **Probar y guardar**. La app la prueba primero y después la almacena cifrada en el **Administrador de credenciales de Windows**. El diálogo actual de la app es para Gemini; los otros servicios de arriba se incluyen como referencia. Consulta la [guía de instalación](GUIA_INSTALACION.md#configurar-la-clave-de-ia) para saber más sobre cómo cambiar una clave.
