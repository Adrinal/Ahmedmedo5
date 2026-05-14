import requests
import json
import os
import sys
import datetime

# ─── ANSI COLORS ──────────────────────────────────────────
R  = "\033[0m"
B  = "\033[1m"
CY = "\033[96m"
GR = "\033[92m"
YE = "\033[93m"
RE = "\033[91m"
MA = "\033[95m"
BL = "\033[94m"
DG = "\033[90m"

BANNER = f"""
{CY}{B}
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║        ▄▀▄ █▀▄ █▀▄ █ █▄ █ ▄▀▄ █           ║
    ║        █▀█ █▄▀ █▀▄ █ █ ▀█ █▀█ █▄▄         ║
    ║                                           ║
    ║              C L I  C H A T               ║
    ║         Powered by OpenRouter API         ║
    ╚═══════════════════════════════════════════╝
{R}"""

CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"

# ─── LOAD CONFIG ──────────────────────────────────────────
def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"{RE}✗ config.json not found. Copy config.example.json to config.json and fill it in.{R}")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

# ─── LOAD / SAVE HISTORY ──────────────────────────────────
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-40:], f, indent=2)

# ─── MODEL PICKER ─────────────────────────────────────────
def pick_model(models):
    print(f"\n{BL}{B}  Available Models:{R}")
    for i, m in enumerate(models, 1):
        print(f"  {DG}[{CY}{i}{DG}]{R} {m['name']}  {DG}({m['id']}){R}")
    print(f"  {DG}[{CY}0{DG}]{R} 🔁 Auto (best available)")
    print()

    while True:
        try:
            choice = input(f"{YE}  Select model (0-{len(models)}): {R}").strip()
            idx = int(choice)
            if idx == 0:
                return {"name": "Auto", "id": "openrouter/auto"}
            if 1 <= idx <= len(models):
                return models[idx - 1]
            print(f"{RE}  ✗ Invalid choice.{R}")
        except ValueError:
            print(f"{RE}  ✗ Enter a number.{R}")

# ─── SEND MESSAGE ─────────────────────────────────────────
def send(api_key, model_id, history, system_prompt):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history)

    try:
        start = datetime.datetime.now()
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={"model": model_id, "messages": messages},
            timeout=120
        )
        elapsed = (datetime.datetime.now() - start).total_seconds()

        if r.status_code != 200:
            return None, None, f"API error {r.status_code}: {r.text[:300]}"

        data = r.json()
        reply = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens = (
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0)
        )
        return reply, (elapsed, tokens), None

    except requests.exceptions.Timeout:
        return None, None, "Request timed out (120s)"
    except Exception as e:
        return None, None, str(e)

# ─── PRINT HELP ───────────────────────────────────────────
def print_help():
    print(f"""
{BL}{B}  Commands:{R}
  {CY}/model{R}   — switch model
  {CY}/clear{R}   — clear conversation history
  {CY}/history{R} — show message count
  {CY}/stats{R}   — show session stats
  {CY}/help{R}    — show this
  {CY}/exit{R}    — quit
""")

# ─── MAIN ─────────────────────────────────────────────────
def main():
    print(BANNER)

    config      = load_config()
    api_key     = config.get("api_key", "")
    models      = config.get("models", [])
    system      = config.get("system_prompt", "You are a helpful assistant.")
    keep_history = config.get("keep_history", True)

    if not api_key or api_key == "YOUR_OPENROUTER_KEY_HERE":
        print(f"{RE}  ✗ Set your api_key in config.json{R}\n")
        sys.exit(1)

    if not models:
        print(f"{RE}  ✗ No models defined in config.json{R}\n")
        sys.exit(1)

    # Session stats
    session_stats = {"requests": 0, "success": 0, "failed": 0, "tokens": 0}

    # Load or start history
    history = load_history() if keep_history else []
    if history:
        print(f"  {DG}↩ Resumed {len(history)} messages from last session{R}\n")

    # Pick model
    current_model = pick_model(models)
    print(f"\n  {GR}✓ Using: {B}{current_model['name']}{R}  {DG}({current_model['id']}){R}")
    print(f"  {DG}Type /help for commands{R}\n")
    print(f"  {DG}{'─' * 43}{R}\n")

    while True:
        try:
            user_input = input(f"{GR}{B}  You:{R} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {YE}Goodbye!{R}\n")
            break

        if not user_input:
            continue

        # ── Commands ──
        if user_input.startswith("/"):
            cmd = user_input.lower()

            if cmd == "/exit":
                print(f"\n  {YE}Goodbye!{R}\n")
                break

            elif cmd == "/clear":
                history = []
                if keep_history:
                    save_history([])
                print(f"  {GR}✓ History cleared.{R}\n")

            elif cmd == "/model":
                current_model = pick_model(models)
                print(f"\n  {GR}✓ Switched to: {B}{current_model['name']}{R}\n")

            elif cmd == "/history":
                print(f"  {BL}Messages in context: {len(history)}{R}\n")

            elif cmd == "/stats":
                print(f"""
  {BL}{B}Session Stats:{R}
  Requests : {session_stats['requests']}
  Success  : {GR}{session_stats['success']}{R}
  Failed   : {RE}{session_stats['failed']}{R}
  Tokens   : {CY}{session_stats['tokens']}{R}
  Model    : {current_model['name']}
""")
            elif cmd == "/help":
                print_help()
            else:
                print(f"  {RE}✗ Unknown command. Type /help{R}\n")
            continue

        # ── Send message ──
        history.append({"role": "user", "content": user_input})
        session_stats["requests"] += 1

        print(f"\n  {MA}{B}  AI ({current_model['name']}):{R}")
        print(f"  {DG}{'─' * 43}{R}")

        reply, meta, error = send(api_key, current_model["id"], history, system)

        if error:
            session_stats["failed"] += 1
            history.pop()  # remove failed message
            print(f"  {RE}✗ {error}{R}")
            print(f"  {DG}Tip: use /model to switch to another{R}\n")
            continue

        session_stats["success"] += 1
        elapsed, (pt, ct, tt) = meta
        session_stats["tokens"] += tt
        history.append({"role": "assistant", "content": reply})

        if keep_history:
            save_history(history)

        # Print reply with indentation
        for line in reply.split("\n"):
            print(f"  {R}{line}")

        print(f"\n  {DG}⏱ {elapsed:.1f}s  🔢 {pt}+{ct}={tt} tokens{R}\n")
        print(f"  {DG}{'─' * 43}{R}\n")

if __name__ == "__main__":
    main()
config.example.json
{
  "api_key": "YOUR_OPENROUTER_KEY_HERE",
  "system_prompt": "You are an expert Android and Java developer assistant.",
  "keep_history": true,
  "models": [
    {
      "name": "NVIDIA Nemotron Super 120B",
      "id": "nvidia/nemotron-3-super-120b-a12b:free"
    },
    {
      "name": "Qwen3 Coder 480B",
      "id": "qwen/qwen3-coder:free"
    },
    {
      "name": "Meta LLaMA 3.3 70B",
      "id": "meta-llama/llama-3.3-70b-instruct:free"
    },
    {
      "name": "OpenAI GPT-OSS 120B",
      "id": "openai/gpt-oss-120b:free"
    },
    {
      "name": "Google Gemma 4 31B",
      "id": "google/gemma-4-31b-it:free"
    },
    {
      "name": "Tencent Hy3 Preview",
      "id": "tencent/hy3-preview:free"
    },
    {
      "name": "Auto (Best Available)",
      "id": "openrouter/auto"
    }
  ]
}
