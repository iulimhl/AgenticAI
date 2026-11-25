from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=6, initial_delay=2.0)
    )
)

class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class LogAnalysis(BaseModel):
    severity: SeverityLevel = Field(description="Security risk level")
    error_code: int = Field(description="Error code from the log or -1 if missing")
    is_compromised: bool = Field(description="True if unauthorized access succeeded, false otherwise")
    summary: str = Field(description="One sentence describing the event")
    recommended_fix: list[str] = Field(description="Steps to fix the security problem")

SYSTEM_PROMPT = """
You are a cybersecurity analyst.
Analyze server logs and identify security problems.

Rules:
-Choose a severity level based on the security risk
-Extract the error code or use -1 if there is none
-Set is_compromised to true if unauthorized access succeeded
-Write a short summary of the event
-Suggest steps to fix the problem
"""

def parse_server_log(raw_log: str) -> LogAnalysis:
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"Analyze the following raw server log:\n{raw_log}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=LogAnalysis,
        ),
    )
    return LogAnalysis.model_validate_json(response.text)

if __name__ == "__main__":
    sample = (
        "2026-10-15 02:11:44 [ALERT] sshd[9012]: Accepted password for root "
        "from 198.51.100.77 port 44122 ssh2 (ErrorCode=401 bypassed via PAM bug)"
    )
    print(parse_server_log(sample).model_dump_json(indent=2))

def test_ssh_breach_log_parsing():
    sample_log = (
        "2026-10-15 02:11:44 [ALERT] sshd[9012]: Accepted password for root "
        "from 198.51.100.77 port 44122 ssh2 (ErrorCode=401 bypassed via PAM bug)"
    )
    result = parse_server_log(sample_log)

    assert result.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
    assert result.error_code == 401
    assert result.is_compromised is True
    assert len(result.recommended_fix) >= 1
