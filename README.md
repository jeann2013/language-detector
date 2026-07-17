# litellm-plugin-language-detector

Reference implementation of a **LiteLLM Routing Plugin**. It exists to teach
the Routing Plugin API and set a quality bar for the ecosystem — not to be
the best language detector out there.

## Qué hace

* Lee `context.structured_messages`, se queda solo con los mensajes
  `role="user"`.
* Detecta el idioma del texto con [`lingua`](https://github.com/pemistahl/lingua-py)
  (offline, sin modelos enormes, buena precisión).
* Publica el resultado en `context.signals["language-detector"]`:

  ```json
  {
      "language": "es",
      "confidence": 0.99,
      "detector": "lingua"
  }
  ```

* Si no puede detectar el idioma (texto vacío, solo emojis, señal ambigua),
  publica:

  ```json
  {
      "language": "unknown",
      "confidence": 0.0,
      "detector": "lingua"
  }
  ```

* Nunca lanza una excepción. En el peor caso, publica el resultado `unknown`.

### Idiomas soportados (v1)

English, Spanish, French, German, Portuguese, Italian, Dutch, Japanese,
Chinese, Korean.

No es necesario cubrir 100 idiomas para que el plugin sea útil — ver
[Roadmap](#roadmap) para cómo crece esta lista.

## Qué NO hace

* No modifica `context.candidate_models` (no narrowing, no filtrado).
* No modifica `context.raw_messages`, `context.structured_messages` ni
  `context.metadata` — un routing plugin solo puede leerlos.
* No reescribe el prompt ni el contenido de ningún mensaje.
* No depende del Router ni de ningún otro plugin.
* No imprime ni loguea nada — solo publica señales.
* No lanza excepciones hacia quien lo invoca, ni corta el pipeline.

## Cómo instalar

```bash
pip install litellm-plugin-language-detector
```

Para desarrollo local (incluye `pytest` y `pytest-asyncio`):

```bash
pip install -e ".[dev]"
```

## Cómo configurar

Requiere `litellm>=1.92` (versión donde se introdujeron los Routing Plugins,
ver [discusión #32168](https://github.com/BerriAI/litellm/discussions/32168)).

### SDK

Se pasa como instancia a `Router(plugins=[...])`. Corre en cada decisión de
ruteo:

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

Dos superficies, según dónde quieras que corra:

**Global**, en cada decisión de ruteo (`router_settings.plugins`, equivalente
proxy de `Router(plugins=[...])`):

```yaml
router_settings:
  plugins:
    - litellm_plugin_language_detector.plugin.language_detector_plugin
```

**Solo dentro del complexity router**, contra el candidate pool ya filtrado
por tier (`complexity_router_config.plugins`):

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

En ambos casos la ruta apuntada debe ser una **instancia**, no la clase —
por eso el paquete expone `language_detector_plugin`, un singleton ya
instanciado, además de la clase `LanguageDetectorPlugin` para quien prefiera
instanciar la suya.

Ver [`examples/sdk.py`](examples/sdk.py) y [`examples/proxy.yaml`](examples/proxy.yaml)
para ejemplos completos.

## Cómo consumir el signal desde otro plugin

Cualquier plugin que corra después en la misma request (más adelante en la
lista de `plugins=[...]`) puede leer el namespace `language-detector` desde
`context.signals`:

```python
class MyDownstreamPlugin:
    async def run(self, context):
        signal = context.signals.get("language-detector")
        if signal and signal["language"] == "es":
            # ajustar candidate_models, lo que sea -- eso es
            # responsabilidad de MyDownstreamPlugin, no de este plugin.
            ...
        return context
```

Una vez que el pipeline de plugins termina, el Router y las estrategias de
auto-router (complexity, adaptive, quality) leen la misma señal desde
`metadata["routing_plugin_signals"]["language-detector"]` — así es como
`context.signals` "sale" del pipeline de plugins hacia el resto del ruteo.

Este plugin nunca lee sus propias señales de una ejecución anterior ni las
de otros plugins: solo escribe una vez, bajo su propio namespace.

## Cómo extenderlo

* **Nuevo idioma**: agregar la entrada correspondiente de `lingua.Language`
  al mapa `_SUPPORTED_LANGUAGES` en
  [`detector.py`](litellm_plugin_language_detector/detector.py).
* **Otro backend de detección** (p. ej. `fasttext`, `langdetect`): reemplazar
  la implementación de `detect_language()` en `detector.py` manteniendo el
  mismo contrato de salida (`language`, `confidence`, `detector`).
* **Más campos en la señal** (script, RTL, multilenguaje): ver
  [Roadmap](#roadmap) — la idea es agregarlos sin romper los campos v1.

## Signal contract

Espacio de nombres: `language-detector`.

| Campo        | Tipo      | Descripción                                   |
| ------------ | --------- | ---------------------------------------------- |
| `language`   | ISO-639-1 | Código de idioma, o `"unknown"`.               |
| `confidence` | float     | 0.0–1.0. `0.0` cuando `language` es `"unknown"`. |
| `detector`   | string    | Nombre del backend usado (`"lingua"`).         |

### Convención de nombres para `signals`

Este plugin usa un namespace explícito (`context.signals["language-detector"]`)
en vez de una clave genérica como `context.signals["language"]`. Esto evita
colisiones entre plugins distintos y establece una convención que otros
plugins del ecosistema pueden seguir: `domain-classifier`, `provider-health`,
`budget-policy`, etc. Si estás escribiendo tu propio plugin, adopta el mismo
patrón.

## Compatibilidad

LiteLLM >= 1.92 (versión donde se introdujeron los Routing Plugins). Solo
funciona con Router async (`router.acompletion(...)`) — `Router.completion()`
síncrono lanza si hay plugins configurados.

`plugin.py` intenta importar el `RoutingContext` real de
`litellm.types.router`; si el litellm instalado es anterior a 1.92 y no lo
tiene, usa un `RoutingContext` local (mismo shape: `raw_messages`,
`structured_messages`, `candidate_models`, `metadata`, `signals`) para que
el plugin siga pudiendo probarse y usarse de forma standalone. Cualquier
objeto que exponga esos cinco atributos es compatible.

## Roadmap

* **v1** — solo detectar idioma (este release).
* **v2** — agregar `"script": "latin"`.
* **v3** — agregar `"rtl": false`.
* **v4** — agregar una lista `"languages"` con múltiples candidatos y su
  confianza, para prompts multilingües.

## Tests

```bash
pytest
```

Cubre español, inglés, francés, chino, texto vacío, emojis y fragmentos de
código.
