# Get your free Google Gemini key (EN)

**[Versión en español](CLAVE_GEMINI.md)**

> AskForever's assistant asks for this key the first time you open the companion. The key is saved in the **Windows Credential Manager**, the secure place where Windows stores passwords, not in a text file.

Other services (Groq, Mistral, Cerebras, OpenRouter): see [Free AI keys](API_KEYS.md).

The key is like a password that lets the companion use Google's AI. Creating one is free and needs no credit card.

## 1. Create the key

1. Go to **[Google AI Studio](https://aistudio.google.com)**.
2. Sign in with your Google account. If it is your first time, accept the terms of use.
3. In the left menu, click **Dashboard**.
4. Open the **API keys** section and click **Create API key**.
5. Give it a name, for example `AskForever`. For the project, keep **Default Gemini Project** unless you prefer to create a new one.
6. After a few seconds Google shows you the key. Copy it with the copy button.

## 2. Give the key to AskForever

1. Open **AskForever**. The first time, the assistant in the console window asks for the free Gemini key.
2. Paste the key when it asks and press Enter. The assistant tests it and saves it in the **Windows Credential Manager**.
3. If the assistant does not appear, a key is already saved; see [Change the key](#change-the-key) below.

## Change the key

To replace the key, open a terminal in `%LOCALAPPDATA%\Programs\AskForever` and run `AskForever.exe setup`. The [installation guide](INSTALL_GUIDE.md#change-the-key) explains how to open the folder and the terminal. Paste the new key in the assistant and press Enter.

## Important

- **Never share your key** and never publish it. If it leaks, delete it in AI Studio (API keys section) and create a new one.
- The free plan has per-minute and per-day limits set by Google. If you exceed them, AskForever will tell you and you can ask again after a moment.
- On Google's free plan, request content may be used to improve its products, depending on your region and Google's terms. Do not write personal data in your questions.
- Enabling billing on Google is optional and not required for AskForever.
