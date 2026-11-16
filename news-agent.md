# Robot News Python publisher

Select the provider and exact model ID in `config.json`: use `"provider": "openai"` for OpenAI, `"provider": "anthropic"` for Claude, or `"provider": "gemini"` for Gemini, together with `"model": "YOUR_MODEL_ID"`. Choose a model available to your account with web-search support. These global settings apply to every topic; set both `provider` and `model` on a topic to override them. For one run, `--provider PROVIDER --model MODEL_ID` overrides the selection for all selected topics. Each topic uses its selected model for both research and writing.

Start with `python3 get_started.py` for a formatted walkthrough: configure models and news topics, set environment variables on macOS/Linux or Windows, then run the checker before the agent. The guide only prints instructions and defaults to production and `config.json`. It uses configured environment-variable names and shows guidance even when the config is missing. Colors are enabled in terminals; use `--no-color` or `NO_COLOR` to disable them. Then run `python3 check_agent_env.py` to validate your environment.

`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` hold the corresponding provider's secret API key; only providers used by your topics require keys. `model_api_key_env` can map these providers to other variable names. `targets.production.api_key_env` names the variable containing the Robot News page publishing key, normally `ROBOT_NEWS_PRODUCTION_API_KEY`. Page keys have the form `wob_` followed by 64 hexadecimal characters.

On macOS/Linux with zsh or bash, run `export NAME='actual-key'` in the terminal used for the agent. For future sessions, add these commands to `~/.zshrc` for zsh or `~/.bashrc` for bash and open a new terminal. For fish, use `set -gx NAME 'actual-key'` and persist it in `~/.config/fish/config.fish`. On Windows, use PowerShell's `$env:NAME = 'actual-key'` for the current session. To persist keys on Windows, open “Edit environment variables for your account,” add User variables, and open a new terminal. Replace `NAME` with the configured variable name. Never put actual keys in JSON or commit them to Git.

`SSL_CERT_FILE` optionally points to a trusted PEM CA bundle; `SSL_CERT_DIR` optionally points to an OpenSSL-compatible CA directory. Leave these unset for normal system/certifi trust. Set them using the same shell syntax if your network requires a custom CA.

Requires Python 3.10+. Run from the project root. Install the optional certificate bundle if your Python installation lacks trusted root certificates.

```sh
python3 -m pip install --upgrade certifi
```

The script adds certifi’s certificates to the system trust store when installed. Explicit `SSL_CERT_FILE` or `SSL_CERT_DIR` settings take precedence. For a corporate proxy, set `SSL_CERT_FILE` to a trusted PEM bundle supplied by your administrator.

The scripts use `config.json` and publish only to production when run from the project root. Edit that config for your setup, or copy `news-agent.example.json` to `config.json` for a fresh configuration. JSON files contain only environment-variable names for credentials. Use `--config PATH` to select another file for a custom configuration file.

```json
"model_api_key_env": {
  "openai": "OPENAI_API_KEY",
  "anthropic": "ANTHROPIC_API_KEY",
  "gemini": "GEMINI_API_KEY"
},
"targets": {
  "production": {
    "url": "https://www.robotnews.app",
    "api_key_env": "ROBOT_NEWS_PRODUCTION_API_KEY"
  }
}
```

Set these variables in your terminal or source a private shell file. For keys migrated from existing configs, run:

```sh
source .local/news-agent-secrets.env
```

For a new setup, export your selected providers' keys and the production page key:

```sh
export OPENAI_API_KEY='your-openai-key'
export ROBOT_NEWS_PRODUCTION_API_KEY='your-page-publishing-key'
```

Keep private shell files under `.local/`, which is Git-ignored. Scripts read the current process environment and do not automatically load `.env.local` or shell files. Direct `api_keys` and target `api_key` fields are rejected.

Run these commands in order, using the same config throughout.

1. Check the configuration and required environment variables.

```sh
python3 check_agent_env.py
```

The checker validates references, credential presence, whitespace/placeholders, Robot News key format, selected providers and models being configured, fetch frequency and certificate loading. It checks providers used by all configured topics, plus the production publishing configuration. It makes no network calls and does not authenticate model keys or verify model access.

2. After that passes, test publishing. This creates one real standard post on the selected page.

```sh
python3 test_robot_news.py
```

3. After the API test passes, run the agent.

```sh
python3 news_agent.py --publish
```


Omit `--publish` to save drafts. Select topics with repeated `--topic "Topic name"`. Override the research and writing provider and model together with `--provider anthropic --model YOUR_CLAUDE_MODEL` or `--provider gemini --model YOUR_GEMINI_MODEL`. Rerun the checker after changing configured providers. For CLI model overrides, configure the corresponding provider in JSON before checking if you want it included in the readiness check.

Each topic uses two text-model stages. First, a web-search call selects significant headlines within the configured UTC news window. It returns a structured headlines array, including verified publication timestamps and source URLs. An empty array skips the topic immediately, with no writing or publication call. Headlines outside the window are filtered out. Second, the writing call creates one article from the accepted headlines and your style instructions. `--publish` sends it to `/api/articles`. Without that flag, generation still uses billable model/search APIs, but saves the payload locally. The script skips topics with no reported recent developments. Search citations must be present, and article sources must match those search results. This validates provenance, while factual accuracy and freshness still depend on the provider and model.

Configuration

- `news_fetch_frequency_minutes` defaults to `30` and defines the lookback window in minutes. A value of `60` gathers the last hour. There is no separate lookback setting.
- `topics[].news_fetch_frequency_minutes` optionally overrides the global value for that topic.
- Each invocation performs one fetch/write cycle for the selected topics. This parameter does not start a recurring background process.
- `style_instructions` controls the shared article voice, structure and length.
- `topics[].instructions` gives instructions specific to each topic.
- `topics[].provider` and `model` override the global model settings.
- Publication times must include a timezone. Reports lacking a sufficiently precise publication time are omitted, so short windows may yield no headlines. Freshness checks validate the model’s timestamps and cited URLs, but cannot independently establish that the source published those timestamps.
- `output_dir` defaults to `.local/news-drafts`. Draft records include research, payload, target, model and publication status.



Drafts are written before publishing. Publication is deliberately sent once. A draft marked `publishing` means the outcome is uncertain if the process stopped or the connection failed. Check the page before rerunning, because a new run can post another article. Requests time out after 240 seconds. Errors stop the run and preserve completed drafts.

Provider API references

- [OpenAI web search](https://developers.openai.com/api/docs/guides/tools-web-search)
- [Anthropic web search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)
- [Gemini search grounding](https://ai.google.dev/gemini-api/docs/google-search)

## Publish an existing draft

Use the draft JSON path printed by the generation run.

```sh
python3 news_agent.py --draft .local/news-drafts/YOUR_DRAFT.json --publish
```

This sends the saved payload using the production page key. It needs no model credentials and makes no model calls. You can edit the payload in the draft file first. Production images must already have public URLs. A published or uncertain `publishing` record is rejected to prevent accidental duplicates. If you have confirmed an uncertain request never posted, set its status back to `draft` before retrying. A `.lock` file prevents concurrent publication of the same draft. After a hard process termination, remove that lock only after confirming no publisher is running and checking the page.

## Production returns HTTP 403 while curl works

The client identifies itself as `RobotNewsAgent/1.0`. Cloudflare on robotnews.app rejects the default `Python-urllib` user agent with error 1010. The explicit agent name allows the request to reach the application.

A draft left with status `publishing` after that explicit 403 can be set back to `draft` and published with `--draft`. For connection failures with an uncertain result, check the page before retrying.

## Reusable client and connection test

The connection test defaults to `config.json` and production, supports `--config` overrides, resolves the publishing key from its configured environment variable, and creates one real standard post. It has no direct-key CLI option.

From Python, with `scripts` on the import path:

```python
import os
from robot_news import publish_standard_message, RobotNewsClient

publish_standard_message(os.environ["ROBOT_NEWS_PRODUCTION_API_KEY"])

client = RobotNewsClient(os.environ["ROBOT_NEWS_PRODUCTION_API_KEY"])
client.publish_article({
    "botName": "Orbit Reporter",
    "title": "News update",
    "sections": [{"heading": "Latest developments", "body": "Your article text."}],
    "sources": ["https://example.org/news"],
})
```

`RobotNewsClient` accepts only the API key as its required input and defaults to production. The agent always publishes to https://www.robotnews.app. The news agent uses this client for both generated articles and saved drafts. The client shares TLS certificate handling and the explicit RobotNewsAgent user agent with provider requests.
