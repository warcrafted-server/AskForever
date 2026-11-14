# Get your free Google Gemini key (EN)

**[Versión en español](CLAVE_GEMINI.md)**

> Needed from the versions that include the **companion** (see the [ROADMAP](../ROADMAP.md)). Version 0.1.x does not use any key: you paste the prompt into the AI of your choice.

Other services (Groq, Mistral, Cerebras, OpenRouter): see [Free AI keys](API_KEYS.md).

The key is like a password that lets the companion use Google's AI. Creating one is free and needs no credit card.

## 1. Create the key

1. Go to **[Google AI Studio](https://aistudio.google.com)**.
2. Sign in with your Google account. If it is your first time, accept the terms of use.
3. In the left menu, click **Dashboard**.
4. Open the **API keys** section and click **Create API key**.
5. Give it a name, for example `AskForever`. For the project, keep **Default Gemini Project** unless you prefer to create a new one.
6. After a few seconds Google shows you the key. Copy it with the copy button.

## 2. Store the key on your computer

The companion keeps the key in the **Windows Credential Manager**, never in a text file and never in the repository. Do not paste it into chats, emails or documents.

- From version 0.2 on, the companion will have a command to store it. Until then, open **PowerShell** in the project folder and run:

  ```powershell
  $s = Read-Host 'Gemini key' -AsSecureString
  $env:AF_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
  .\companion\.venv\Scripts\python.exe -c "import keyring, os; keyring.set_password('AskForever', 'gemini', os.environ['AF_KEY'])"
  Remove-Item Env:AF_KEY
  ```

  Paste the key when asked (it shows as asterisks) and press Enter.

- To check that it was stored, without showing it:

  ```powershell
  .\companion\.venv\Scripts\python.exe -c "import keyring; k = keyring.get_password('AskForever', 'gemini'); print('Stored, length', len(k) if k else 'NO KEY')"
  ```

## Important

- **Never share your key** and never publish it. If it leaks, delete it in AI Studio (API keys section) and create a new one.
- The free plan has per-minute and per-day limits set by Google. If you exceed them, AskForever will tell you and you can ask again after a moment.
- On Google's free plan, request content may be used to improve its products, depending on your region and Google's terms. Do not write personal data in your questions.
- Enabling billing on Google is optional and not required for AskForever.
