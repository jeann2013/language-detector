"""Example: using LanguageDetectorPlugin standalone (no Router needed).

The plugin never depends on the Router -- it only reads
``context.structured_messages`` and writes ``context.signals``. This shows
the whole round trip by hand, so it works regardless of which litellm
version (if any) is installed.

With litellm>=1.92 (Routing Plugins), wire it into the real Router instead:

    from litellm import Router
    from litellm_plugin_language_detector import LanguageDetectorPlugin

    router = Router(
        model_list=[...],
        plugins=[LanguageDetectorPlugin()],
    )

    response = await router.acompletion(
        model="smart-router",
        messages=[{"role": "user", "content": "Hola, necesito ayuda con Python."}],
    )
    # response's routing decision was made with
    # metadata["routing_plugin_signals"]["language-detector"] available.
"""

import asyncio

from litellm_plugin_language_detector import LanguageDetectorPlugin, RoutingContext


async def main() -> None:
    plugin = LanguageDetectorPlugin()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hola, necesito ayuda con Python."},
    ]
    context = RoutingContext(
        raw_messages=messages,
        structured_messages=messages,
        candidate_models=["openai/gpt-4o"],
    )

    context = await plugin.run(context)

    print(context.signals["language-detector"])
    # {'language': 'es', 'confidence': 0.99, 'detector': 'lingua'}


if __name__ == "__main__":
    asyncio.run(main())
