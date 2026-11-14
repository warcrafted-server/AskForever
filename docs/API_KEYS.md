# Free AI keys: where to create them (EN)

**[Versión en español](CLAVES_API.md)**

> Needed from the versions that include the **companion** (see the [ROADMAP](../ROADMAP.md)). Every player uses their own free key from the service they prefer. Free plans and limits change often: check each service's console for your real limits. For Google Gemini there is a more detailed [step-by-step guide](GEMINI_KEY.md).

| Service | Where to create the key | Official docs | Notes |
|---|---|---|---|
| **Google Gemini** | [aistudio.google.com](https://aistudio.google.com) → Dashboard → API keys → **Create API key** | [Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) | Current default of AskForever. On the free plan Google may use your requests to improve its products |
| **Groq** | [console.groq.com/keys](https://console.groq.com/keys) | [Quickstart](https://console.groq.com/docs/quickstart) | Keys belong to a project; only team owners and developers can create them |
| **Mistral** | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys) → **New key** | [Create your first API key](https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key) | The full key is shown only once: copy it right away. The free Experiment plan may use requests to train their models ([details](https://help.mistral.ai/en/articles/450104-how-can-i-try-the-api-for-free-with-the-experiment-plan)) |
| **Cerebras** | [cloud.cerebras.ai](https://cloud.cerebras.ai) → **API Keys** → **Generate API Key** | [API keys](https://inference-docs.cerebras.ai/console/api-keys) | Free trial accounts have no projects |
| **OpenRouter** | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | [Quickstart](https://openrouter.ai/docs/cookbook/get-started/quickstart) | One key for free and paid models; free models end in `:free` and have low daily limits |

## Store the key

Never paste a key into chats, emails or documents. In **PowerShell**, from the `companion` folder (replace `groq` with `gemini`, `mistral`, `cerebras` or `openrouter`):

```powershell
$s = Read-Host 'Key' -AsSecureString
$env:AF_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
.venv\Scripts\python.exe -m askforever set-key --provider groq
Remove-Item Env:AF_KEY
```

Then check which keys are stored with `.venv\Scripts\python.exe -m askforever providers`, list a service's models with `... list-models --provider groq`, and test it with `... test-key --provider groq`.
