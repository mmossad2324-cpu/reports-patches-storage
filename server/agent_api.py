import os
import sys
import json
import logging
from typing import Dict, Any

# Ensure core modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_client import call_cf_workers_ai
from core.sast_agent import SASTAgent
from core.remediation_agent import RemediationAgent
from dashboard import run_full_real_scan

logger = logging.getLogger("CloudAgentOrchestrator")

class CloudAgentOrchestrator:
    """Intelligent Cloud Agent Orchestrator running natively in a FastAPI environment.
    Designed to mimic professional MCP (Model Context Protocol) architectures.
    """

    def __init__(self):
        self.available_tools = {
            "run_sast": {
                "name": "run_sast",
                "description": "Run Static Application Security Testing (SAST) on provided source code to find vulnerabilities.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "The source code to analyze."}
                    },
                    "required": ["code"]
                }
            },
            "run_dast": {
                "name": "run_dast",
                "description": "Run Dynamic Application Security Testing (DAST) to inspect HTTP headers and API security.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_url": {"type": "string", "description": "The URL of the target application."}
                    },
                    "required": ["target_url"]
                }
            },
            "generate_patch": {
                "name": "generate_patch",
                "description": "Generate a secure code patch and WAF rules for a identified vulnerability.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_description": {"type": "string", "description": "Description of the vulnerability."}
                    },
                    "required": ["issue_description"]
                }
            }
        }

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute the requested tool cleanly in the cloud backend."""
        logger.info(f"Agent executing tool: {tool_name}")
        
        if tool_name == "run_sast":
            code = arguments.get("code", "")
            if not code: return "Error: No code provided."
            res = SASTAgent().analyze_source_code(code)
            return json.dumps(res, ensure_ascii=False)
            
        elif tool_name == "run_dast":
            target_url = arguments.get("target_url", "")
            if not target_url: return "Error: No target_url provided."
            res = run_full_real_scan(target_url, "cloud-agent-session")
            return f"DAST execution completed. Findings: {len(res.get('enriched_findings', []))}"
            
        elif tool_name == "generate_patch":
            issue = arguments.get("issue_description", "")
            res = RemediationAgent().generate_patch({"cwe": "Unknown", "severity": "High", "file": "unknown", "snippet": issue})
            return res.get("patch_code", "Failed to generate patch.")
            
        else:
            return f"Error: Tool {tool_name} not found."

    def process_intent(self, user_prompt: str, context: str = "") -> str:
        """Process user intent via ReAct / Tool Calling Loop over WebSockets/API."""
        tools_desc = json.dumps(list(self.available_tools.values()), ensure_ascii=False, indent=2)
        
        system_prompt = f"""أنت وكيل ذكي مستقل يعمل عبر السحابة (Cloud Autonomous Security Agent).
لديك إمكانية الوصول إلى الأدوات التالية:
{tools_desc}

يجب عليك تحليل طلب المستخدم، وإذا كان الطلب يتطلب استخدام أداة، قم بإرجاع JSON فقط يحتوي على استدعاء الأداة المطلوبة بهذا التنسيق:
```json
{{"action": "tool_name", "arguments": {{"arg_name": "arg_value"}}}}
```
وإذا كان الطلب مجرد استفسار أو لا يتطلب أداة، أجب باللغة العربية مباشرة بمهنية كخبير أمني.
"""
        
        # Step 1: LLM determines if a tool is needed
        response = call_cf_workers_ai(user_prompt, model_index=0, system_prompt=system_prompt)
        
        # Step 2: Parse and Execute
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            else:
                json_str = response
                
            action_req = json.loads(json_str)
            if "action" in action_req and "arguments" in action_req:
                tool_name = action_req["action"]
                tool_args = action_req["arguments"]
                
                # Execute Tool
                tool_result = self._execute_tool(tool_name, tool_args)
                
                # Final Summary
                final_prompt = f"المستخدم طلب: {user_prompt}\nنتيجة الأداة ({tool_name}): {tool_result[:1000]}\nقم بصياغة رد نهائي احترافي باللغة العربية."
                final_answer = call_cf_workers_ai(final_prompt, model_index=1, system_prompt="أنت خبير أمني يعمل في بيئة Cloud SOC.")
                return f"🛠️ **[Cloud Agent Action]:** استدعاء الأداة `{tool_name}`.\n\n{final_answer}"
                
        except Exception:
            # Not a tool call, return natural response
            pass
            
        return response
