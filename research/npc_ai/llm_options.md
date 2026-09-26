# LLMs for AI-driven NPC dialogue: options (researched 2026-09-25)

The goal is free or very cheap LLM access with an API, to drive NPC dialogue in Space Station
Columbia (Godot 4.3 on the Steam Deck; a move to 4.5 is already pending).

## What an NPC conversation costs
Assume about 1,500 input tokens per line. That covers the persona, the station and world facts, the
NPC's memory and the recent turns. Most of it is the same every time, so it can be cached. Assume
about 80 output tokens per spoken line.
**1,000 NPC lines ≈ 1.5 M input + 0.08 M output tokens.**

| Option | Price per 1 M tokens, in / out | Cost of 1,000 lines | Notes |
|---|---|---|---|
| Groq gpt-oss-20b (paid) | $0.075 / $0.30 (cached in $0.0375) | ~$0.14 | ~1,000 tokens/s: the fastest replies |
| Gemini 2.5 Flash-Lite (paid) | $0.10 / $0.40 | ~$0.18 | the cheapest Gemini |
| DeepSeek flash (V4.1-Flash) | $0.30 / $1.20 peak, half off-peak; cache hit $0.006 | ~$0.10 with the persona cached | no free tier |
| OpenAI GPT-6 Luna | $0.10 / $0.50 (cut 2026-09-23) | ~$0.19 | |
| Mistral Small 4 | $0.15 / $0.60 | ~$0.27 | the free plan includes $10 a month of API credit |
| Qwen3.7 Flash (aggregator figure) | $0.03 / $0.13 | ~$0.06 | cheapest listed; not checked against the provider |
| Claude Haiku 4.5 | $1 / $5 | ~$1.90 (less with caching) | best character writing of the cheap tier; not free |

## Free tiers (no credit card)
- **Google Gemini API (AI Studio).**
  - Free models: Gemini 3.x Flash, 3.5 Flash-Lite, 2.5 Flash / Flash-Lite, 2.5 Pro, Gemma 4.
  - Catch: free-tier content "is used to improve Google's products". The EU, UK and EEA are exempt.
  - Limits are no longer published; you see them in AI Studio once signed in. Third-party figures are
    5–15 requests/min and 20–1,500 requests/day depending on the model.
  - It has an OpenAI-compatible endpoint.
- **Groq.**
  - Free models: gpt-oss-120b, gpt-oss-20b and qwen3.8-27b.
  - Limits: 30 requests/min, 1,000 requests/day, 8K tokens/min and 200K tokens/day per model.
  - Replies are near-instant. Llama 3.3 70B left the free tier on 2026-08-16.
- **Cerebras.**
  - Free models: gpt-oss-120b and qwen-3.8-27b.
  - Limits: 5 requests/min and 1 M tokens/day.
- **OpenRouter.**
  - One API in front of many providers, with about 19 `:free` models.
  - Limits: 20 requests/min and 50 requests/day, rising to 1,000/day after a one-time $10 credit.
  - Useful as a single integration with fallbacks.
- **Mistral.** The free plan has $10 a month of API credit. Its "Experiment" tier trains on your data.
- **Others:** Cloudflare Workers AI (small context), NVIDIA NIM (~1,000 requests/day), Hugging Face,
  and Cohere (non-commercial only). GitHub Models was retired on 2026-07-30.

## Local (free, offline, no key)
- **NobodyWho.**
  - A Godot plugin (llama.cpp inside) with streaming, tool calling, and structured output from
    grammars.
  - It also does embeddings, speech-to-text and text-to-speech.
  - Needs **Godot 4.5+**. Vulkan on Linux. Licence EUPL-1.2, which allows commercial games.
  - Suggested starter model: Qwen3 0.6B (~330 MB).
- **GDLlama** (Godot 4.4+) and **godot-local-llm** (Godot 4.3+): GDExtensions over llama.cpp.
- **On the Deck:**
  - The game already uses most of the APU. A 0.6–4B model would compete with rendering for the GPU
    and the 16 GB of shared memory.
  - A 1–4B model on the Deck is small enough to follow a persona, but its lines are thinner and it
    loses track more easily.
  - Best as an offline fallback, or for barks (short one-liners), not the main voice.

## Recommendation
1. **Build against the OpenAI-compatible chat API.** Gemini, Groq, Cerebras, DeepSeek, OpenRouter,
   Mistral, OpenAI and a local llama-server all accept it. One client then only needs a
   configurable base URL, key and model, and each NPC request can fall back to another provider.
2. **Develop on free tiers:** Groq (fastest, 1,000 requests/day) with Gemini as the fallback. Neither
   needs a card.
3. **Paid play:** Groq gpt-oss-20b or Gemini 2.5 Flash-Lite, at about $0.15 per 1,000 NPC lines. Use
   DeepSeek flash with prompt caching if volume grows.
4. **Offline / no key:** NobodyWho with a small Qwen or Gemma model, once the project is on Godot 4.5.
5. **Keys:** never ship a key inside an exported game. Read the player's key from their settings,
   or route through a small server.

## Sources
- Google Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Groq pricing (third-party): https://www.cloudzero.com/blog/groq-pricing/
- DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing
- Cerebras rate limits: https://inference-docs.cerebras.ai/support/rate-limits
- Mistral pricing: https://mistral.ai/pricing
- OpenRouter free API comparison (June 2026): https://openrouter.ai/blog/tutorials/free-llm-apis-compared/
- Free-tier changes: https://klymentiev.com/blog/free-llm-api
- Price rankings: https://costgoat.com/compare/llm-api, https://benchlm.ai/llm-pricing
- OpenAI Luna price cut: https://qz.com/openai-gpt-6-sol-luna-api-price-cut-092326
- NobodyWho: https://github.com/nobodywho-ooo/nobodywho
- GDLlama: https://github.com/xarillian/GDLlama
- godot-local-llm: https://github.com/MhrnMhrn/godot-local-llm
