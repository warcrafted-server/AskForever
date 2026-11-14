# Consigue tu clave gratuita de Google Gemini (ES)

**[English version](GEMINI_KEY.md)**

> Hace falta a partir de las versiones que incluyen el **companion** (consulta la [hoja de ruta](../ROADMAP.md)). La versión 0.1.x no usa ninguna clave: tú pegas el prompt en la IA que prefieras.

Otros servicios (Groq, Mistral, Cerebras, OpenRouter): consulta [Claves de IA gratuitas](CLAVES_API.md).

La clave es como una contraseña que permite al companion usar la IA de Google. Crearla es gratis y no pide tarjeta.

## 1. Crear la clave

1. Entra en **[Google AI Studio](https://aistudio.google.com)**.
2. Inicia sesión con tu cuenta de Google. Si es la primera vez, acepta los términos de uso.
3. En el menú de la izquierda, pulsa **Dashboard**.
4. Abre la sección **Claves de API** y pulsa **Crear clave de API**.
5. Ponle un nombre, por ejemplo `AskForever`. En proyecto, deja **Default Gemini Project** salvo que prefieras crear uno nuevo.
6. En unos segundos Google te muestra la clave. Cópiala con el botón de copiar.

## 2. Guardar la clave en tu equipo

El companion guarda la clave en el **Administrador de credenciales de Windows**, nunca en un archivo de texto ni en el repositorio. No la pegues en chats, correos ni documentos.

- A partir de la versión 0.2, el companion tendrá un comando para guardarla. Mientras tanto, abre **PowerShell** en la carpeta del proyecto y ejecuta:

  ```powershell
  $s = Read-Host 'Clave de Gemini' -AsSecureString
  $env:AF_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
  .\companion\.venv\Scripts\python.exe -c "import keyring, os; keyring.set_password('AskForever', 'gemini', os.environ['AF_KEY'])"
  Remove-Item Env:AF_KEY
  ```

  Pega la clave cuando la pida (se ve como asteriscos) y pulsa Enter.

- Para comprobar que se guardó, sin mostrarla:

  ```powershell
  .\companion\.venv\Scripts\python.exe -c "import keyring; k = keyring.get_password('AskForever', 'gemini'); print('Guardada, longitud', len(k) if k else 'NO HAY CLAVE')"
  ```

## Importante

- **No compartas tu clave** ni la publiques. Si se filtra, bórrala en AI Studio (sección Claves de API) y crea otra.
- El plan gratuito tiene límites por minuto y por día que fija Google. Si los superas, AskForever te avisará y podrás volver a preguntar en un momento.
- En el plan gratuito de Google, el contenido de las consultas puede usarse para mejorar sus productos, según tu región y las condiciones de Google. No escribas datos personales en tus preguntas.
- Activar la facturación en Google es opcional y no hace falta para AskForever.
