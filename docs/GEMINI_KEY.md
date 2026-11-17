# Get your free Google Gemini key (EN)

**[Versión en español](CLAVE_GEMINI.md)**

> AskForever App's **Configure AI** dialog asks for this key the first time you open the app. It tests the key before saving it encrypted in the **Windows Credential Manager**, not in a text file.

Other services (Groq, Mistral, Cerebras, OpenRouter): see [Free AI keys](API_KEYS.md).

The key is like a password that lets AskForever App use Google's AI. Creating one is free and needs no credit card.

## 1. Create the key

1. Go to **[Google AI Studio](https://aistudio.google.com)**.
2. Sign in with your Google account. If it is your first time, accept the terms of use.
3. In the left menu, click **Dashboard**.
4. Open the **API keys** section and click **Create API key**.
5. Give it a name, for example `AskForever`. For the project, keep **Default Gemini Project** unless you prefer to create a new one.
6. After a few seconds Google shows you the key. Copy it with the copy button.

## 2. Give the key to AskForever

1. Open **AskForever App**. The first time, its **Configure AI** dialog opens.
2. Paste the key into the dialog and click **Test and save**. AskForever App tests it first, then stores it encrypted in the **Windows Credential Manager**.
3. If the dialog does not appear, a key is already saved. To add or replace a key, click **Configure AI** in the app window.

## Change the key

To replace the key, open **AskForever App** and click **Configure AI**. Enter the new Gemini key and click **Test and save**. No terminal or console is needed.

## Important

- **Never share your key** and never publish it. If it leaks, delete it in AI Studio (API keys section) and create a new one.
- The free plan has per-minute and per-day limits set by Google. If you exceed them, AskForever will tell you and you can ask again after a moment.
- On Google's free plan, request content may be used to improve its products, depending on your region and Google's terms. Do not write personal data in your questions.
- Enabling billing on Google is optional and not required for AskForever.
