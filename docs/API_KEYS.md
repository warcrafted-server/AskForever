# Free AI keys: where to create them (EN)

**[Versión en español](CLAVES_API.md)**

> AskForever App currently configures Google Gemini. The other services below are listed for reference. Every player needs their own key. Free plans and limits change often: check each service's console for your real limits. For Gemini there is a more detailed [step-by-step guide](GEMINI_KEY.md).

| Service | Where to create the key | Official docs | Notes |
|---|---|---|---|
| **Google Gemini** | [aistudio.google.com](https://aistudio.google.com) → Dashboard → API keys → **Create API key** | [Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) | Current default of AskForever. On the free plan Google may use your requests to improve its products |
| **Groq** | [console.groq.com/keys](https://console.groq.com/keys) | [Quickstart](https://console.groq.com/docs/quickstart) | Keys belong to a project; only team owners and developers can create them |
| **Mistral** | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys) → **New key** | [Create your first API key](https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key) | The full key is shown only once: copy it right away. The free Experiment plan may use requests to train their models ([details](https://help.mistral.ai/en/articles/450104-how-can-i-try-the-api-for-free-with-the-experiment-plan)) |
| **Cerebras** | [cloud.cerebras.ai](https://cloud.cerebras.ai) → **API Keys** → **Generate API Key** | [API keys](https://inference-docs.cerebras.ai/console/api-keys) | Free trial accounts have no projects |
| **OpenRouter** | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | [Quickstart](https://openrouter.ai/docs/cookbook/get-started/quickstart) | One key for free and paid models; free models end in `:free` and have low daily limits |

## Enter the key in AskForever App

Never paste a key into chats, emails or documents. To enter a Gemini key in AskForever App, click **Configure AI**, enter the key and click **Test and save**. The app tests it first, then stores it encrypted in the **Windows Credential Manager**. The current app dialog is for Gemini; the other services above are listed for reference. See the [installation guide](INSTALL_GUIDE.md#configure-the-ai-key) for more about changing a key.
