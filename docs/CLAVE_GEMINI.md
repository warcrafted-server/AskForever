# Consigue tu clave gratuita de Google Gemini (ES)

**[English version](GEMINI_KEY.md)**

> El asistente de AskForever pide esta clave la primera vez que abres el companion. La clave se guarda en el **Administrador de credenciales de Windows**, el lugar seguro donde Windows guarda las contraseñas, no en un archivo de texto.

Otros servicios (Groq, Mistral, Cerebras, OpenRouter): consulta [Claves de IA gratuitas](CLAVES_API.md).

La clave es como una contraseña que permite al companion usar la IA de Google. Crearla es gratis y no pide tarjeta.

## 1. Crear la clave

1. Entra en **[Google AI Studio](https://aistudio.google.com)**.
2. Inicia sesión con tu cuenta de Google. Si es la primera vez, acepta los términos de uso.
3. En el menú de la izquierda, pulsa **Dashboard**.
4. Abre la sección **Claves de API** y pulsa **Crear clave de API**.
5. Ponle un nombre, por ejemplo `AskForever`. En proyecto, deja **Default Gemini Project** salvo que prefieras crear uno nuevo.
6. En unos segundos Google te muestra la clave. Cópiala con el botón de copiar.

## 2. Dar la clave a AskForever

1. Abre **AskForever**. La primera vez, el asistente de la ventana de consola pide la clave gratuita de Gemini.
2. Pega la clave cuando la pida y pulsa Enter. El asistente la prueba y la guarda en el **Administrador de credenciales de Windows**.
3. Si el asistente no aparece, ya hay una clave guardada; consulta [Cambiar la clave](#cambiar-la-clave) más abajo.

## Cambiar la clave

Para cambiar la clave, abre una terminal en `%LOCALAPPDATA%\Programs\AskForever` y ejecuta `AskForever.exe setup`. La [guía de instalación](GUIA_INSTALACION.md#cambiar-la-clave) explica cómo abrir la carpeta y la terminal. Pega la clave nueva en el asistente y pulsa Enter.

## Importante

- **No compartas tu clave** ni la publiques. Si se filtra, bórrala en AI Studio (sección Claves de API) y crea otra.
- El plan gratuito tiene límites por minuto y por día que fija Google. Si los superas, AskForever te avisará y podrás volver a preguntar en un momento.
- En el plan gratuito de Google, el contenido de las consultas puede usarse para mejorar sus productos, según tu región y las condiciones de Google. No escribas datos personales en tus preguntas.
- Activar la facturación en Google es opcional y no hace falta para AskForever.
