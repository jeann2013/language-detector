# litellm-plugin-language-detector

Reference implementation of a **LiteLLM Routing Plugin**. It exists to teach
the Routing Plugin API and set a quality bar for the ecosystem — not to be
the best language detector out there.

## What it does

* Reads `context.structured_messages`, keeping only `role="user"` messages.
* Detects the text's language with [`lingua`](https://github.com/pemistahl/lingua-py)
  (offline, no huge models, good accuracy).
* Publishes the result to `context.signals["language-detector"]`:

  ```json
  {
      "language": "es",
      "confidence": 0.99,
      "detector": "lingua"
  }
  ```

* If it can't detect a language (empty text, emojis only, ambiguous
  signal), it publishes:

  ```json
  {
      "language": "unknown",
      "confidence": 0.0,
      "detector": "lingua"
  }
  ```

* Never raises an exception. In the worst case, it publishes the `unknown`
  result.

### Supported languages (v1)

English, Spanish, French, German, Portuguese, Italian, Dutch, Japanese,
Chinese, Korean.

Covering 100 languages isn't necessary for the plugin to be useful — see the
[Roadmap](#roadmap) for how this list grows.

## What it does NOT do

* Doesn't modify `context.candidate_models` (no narrowing, no filtering).
* Doesn't modify `context.raw_messages`, `context.structured_messages`, or
  `context.metadata` — a routing plugin can only read those.
* Doesn't rewrite the prompt or any message content.
* Doesn't depend on the Router or on any other plugin.
* Doesn't print or log anything — it only publishes signals.
* Never raises an exception back to the caller, and never short-circuits
  the pipeline.

## How to install

```bash
pip install litellm-plugin-language-detector
```

For local development (includes `pytest` and `pytest-asyncio`):

```bash
pip install -e ".[dev]"
```

## How to configure

Requires `litellm>=1.92` (the version where Routing Plugins were
introduced, see [discussion #32168](https://github.com/BerriAI/litellm/discussions/32168)).

### SDK

Passed as an instance to `Router(plugins=[...])`. Runs on every routing
decision:

```python
from litellm import Router
from litellm_plugin_language_detector import LanguageDetectorPlugin

router = Router(
    model_list=[...],
    plugins=[
        LanguageDetectorPlugin()
    ]
)
```

### Proxy

Two surfaces, depending on where you want it to run:

**Global**, on every routing decision (`router_settings.plugins`, the proxy
equivalent of `Router(plugins=[...])`):

```yaml
router_settings:
  plugins:
    - litellm_plugin_language_detector.plugin.language_detector_plugin
```

**Scoped to the complexity router only**, against the tier's already
filtered candidate pool (`complexity_router_config.plugins`):

```yaml
model_list:
  - model_name: smart-router
    litellm_params:
      model: auto_router/complexity_router
      complexity_router_config:
        tiers:
          SIMPLE: ["gpt-4o-mini"]
          COMPLEX: ["gpt-4o"]
        default_model: gpt-4o-mini
        plugins:
          - litellm_plugin_language_detector.plugin.language_detector_plugin
```

In both cases the referenced path must point to an **instance**, not the
class — that's why the package exposes `language_detector_plugin`, an
already-instantiated singleton, in addition to the `LanguageDetectorPlugin`
class for anyone who'd rather instantiate their own.

See [`examples/sdk.py`](examples/sdk.py) and [`examples/proxy.yaml`](examples/proxy.yaml)
for complete examples.

## How to consume the signal from another plugin

Any plugin that runs later in the same request (further down the
`plugins=[...]` list) can read the `language-detector` namespace from
`context.signals`:

```python
class MyDownstreamPlugin:
    async def run(self, context):
        signal = context.signals.get("language-detector")
        if signal and signal["language"] == "es":
            # adjust candidate_models, whatever -- that's
            # MyDownstreamPlugin's responsibility, not this plugin's.
            ...
        return context
```

Once the plugin pipeline finishes, the Router and the auto-router
strategies (complexity, adaptive, quality) read the same signal from
`metadata["routing_plugin_signals"]["language-detector"]` — that's how
`context.signals` "exits" the plugin pipeline into the rest of routing.

This plugin never reads its own signal from a previous run, nor any other
plugin's: it only writes once, under its own namespace.

## How to extend it

* **New language**: add the corresponding `lingua.Language` entry to the
  `_SUPPORTED_LANGUAGES` map in
  [`detector.py`](litellm_plugin_language_detector/detector.py).
* **Different detection backend** (e.g. `fasttext`, `langdetect`): replace
  the `detect_language()` implementation in `detector.py`, keeping the same
  output contract (`language`, `confidence`, `detector`).
* **More fields in the signal** (script, RTL, multilingual): see the
  [Roadmap](#roadmap) — the idea is to add them without breaking the v1
  fields.

## Signal contract

Namespace: `language-detector`.

| Field        | Type      | Description                                |
| ------------ | --------- | ------------------------------------------- |
| `language`   | ISO-639-1 | Language code, or `"unknown"`.              |
| `confidence` | float     | 0.0–1.0. `0.0` when `language` is `"unknown"`. |
| `detector`   | string    | Name of the backend used (`"lingua"`).      |

### Naming convention for `signals`

This plugin uses an explicit namespace (`context.signals["language-detector"]`)
instead of a generic key like `context.signals["language"]`. This avoids
collisions between different plugins and establishes a convention other
plugins in the ecosystem can follow: `domain-classifier`, `provider-health`,
`budget-policy`, etc. If you're writing your own plugin, adopt the same
pattern.

## Compatibility

LiteLLM >= 1.92 (the version where Routing Plugins were introduced). Only
works with the async Router (`router.acompletion(...)`) — the sync
`Router.completion()` raises when plugins are configured.

`plugin.py` tries to import the real `RoutingContext` from
`litellm.types.router`; if the installed litellm predates 1.92 and doesn't
have it, it falls back to a local `RoutingContext` (same shape:
`raw_messages`, `structured_messages`, `candidate_models`, `metadata`,
`signals`) so the plugin can still be tested and used standalone. Any
object exposing those five attributes is compatible.

## Roadmap

* **v1** — language detection only (this release).
* **v2** — add `"script": "latin"`.
* **v3** — add `"rtl": false`.
* **v4** — add a `"languages"` list with multiple candidates and their
  confidence, for multilingual prompts.

## Tests

```bash
pytest
```

Covers Spanish, English, French, Chinese, empty text, emojis, and code
snippets.
