"""Shared LLM client using Cloudflare Workers AI - the project's primary AI backbone."""
import os
import json
import logging

logger = logging.getLogger("LLMClient")

# Cloudflare project models
MODEL_SAST       = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"   # SAST code audit
MODEL_DAST       = "THUDM/glm-4-9b-chat"                        # DAST dynamic analysis / Qwen Fallback
MODEL_REMEDIATION = "THUDM/glm-4-9b-chat"                       # Remediation patches
MODEL_FALLBACK   = "THUDM/glm-4-9b-chat"                        # General fallback

def get_cf_credentials() -> list:
    default_models = [
        "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
        "@cf/qwen/qwen1.5-14b-chat-awq"
    ]
    creds = []
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        secrets_path = os.path.join(project_dir, ".secrets.json")
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                sec = json.load(f)
                for idx, (usr, val) in enumerate(sec.items()):
                    if isinstance(val, dict) and val.get("cf_account_id") and val.get("cf_token"):
                        m = default_models[idx % len(default_models)]
                        creds.append({"acc_id": val["cf_account_id"], "token": val["cf_token"], "model": m})
    except Exception:
        pass

    if not creds:
        # Try reading from Streamlit secrets or environment variables
        # Try reading from Streamlit secrets, fallback to environment variables
        t1 = os.environ.get("CF_TOKEN_1", "")
        a1 = os.environ.get("CF_ACC_1", "05880c19ce2705172c0da63b18d1d4a6")
        t2 = os.environ.get("CF_TOKEN_2", "")
        a2 = os.environ.get("CF_ACC_2", "3f9803220e451c20dbc1ce0fcf2e843e")
        t3 = os.environ.get("CF_TOKEN_3", "")
        a3 = os.environ.get("CF_ACC_3", "42f06fdf78972d3e1be8dabe2c0174ba")
        
        try:
            import streamlit as st
            t1 = st.secrets.get("CF_TOKEN_1", t1)
            a1 = st.secrets.get("CF_ACC_1", a1)
            t2 = st.secrets.get("CF_TOKEN_2", t2)
            a2 = st.secrets.get("CF_ACC_2", a2)
            t3 = st.secrets.get("CF_TOKEN_3", t3)
            a3 = st.secrets.get("CF_ACC_3", a3)
        except Exception:
            pass

        if t1: creds.append({"acc_id": a1, "token": t1, "model": "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"})
        if t2: creds.append({"acc_id": a2, "token": t2, "model": "@cf/qwen/qwen1.5-14b-chat-awq"})
        if t3: creds.append({"acc_id": a3, "token": t3, "model": "@cf/meta/llama-3.1-8b-instruct"})

    return creds


def call_cf_workers_ai(prompt: str, model_index: int = 0, system_prompt: str = "") -> str:
    """Call Cloudflare Workers AI using the active project account credentials."""
    cf_credentials = get_cf_credentials()
    if not cf_credentials:
        logger.warning("No Cloudflare credentials available.")
        return ""
    cred = cf_credentials[model_index % len(cf_credentials)]
    url = f"https://api.cloudflare.com/client/v4/accounts/{cred['acc_id']}/ai/run/{cred['model']}"
    headers = {
        "Authorization": f"Bearer {cred['token']}",
        "Content-Type": "application/json"
    }
    
    sys_p = system_prompt or "أنت أقوى وأخطر عقلية أمن سيبراني ومدقق أنظمة مؤسسي في العالم."
    payload = {
        "messages": [
            {"role": "system", "content": sys_p},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        import requests
        r = requests.post(url, headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            res = r.json().get("result", {})
            txt = res.get("response") or (res.get("choices", [{}])[0].get("message", {}).get("content", ""))
            txt = txt.strip()
            if "<think>" in txt and "</think>" in txt:
                txt = txt.split("</think>")[-1].strip()
            if txt:
                return txt
    except Exception as e:
        logger.error(f"Cloudflare Workers AI call failed for account #{model_index}: {e}")

    return ""

def call_llm(prompt: str, model: str = MODEL_FALLBACK, max_tokens: int = 512, system_prompt: str = "") -> str:
    """Call Cloudflare Workers AI."""
    model_idx = 0 if "deepseek" in model.lower() else 1
    cf_res = call_cf_workers_ai(prompt, model_index=model_idx, system_prompt=system_prompt)
    if cf_res:
        return cf_res
    return "⚠️ AI Analysis Failed: Cloudflare Workers AI is unreachable or returned an error."

