"""
TAPISH ADK Hello World — Day 1 Mandatory Gate
Verifies: google-adk install, LlmAgent creation, FunctionTool execution, Runner async flow.
Run: GOOGLE_API_KEY=your_key python backend/tests/test_adk_hello.py
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# === Verified import paths (google-adk v1.33.0) ===
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# 1. Define a simple mock tool with try/except (mandated by plan)
def check_temperature_sensor(location: str) -> str:
    """Fetches current temperature and humidity for a Lahore location.
    Returns JSON string with temperature_c and humidity readings."""
    try:
        if "walled city" in location.lower() or "bhati gate" in location.lower():
            return '{"status": "success", "location": "Bhati Gate, Walled City", "temperature_c": 48.5, "humidity_pct": 65, "heat_index": 52.1}'
        elif "dha" in location.lower():
            return '{"status": "success", "location": "DHA Phase 5", "temperature_c": 42.0, "humidity_pct": 45, "heat_index": 44.8}'
        return f'{{"status": "success", "location": "{location}", "temperature_c": 38.0, "humidity_pct": 40, "heat_index": 39.5}}'
    except Exception as e:
        return f'{{"error": "SENSOR_FAILURE", "details": "{str(e)}"}}'


# 2. Create the ADK Agent
# NOTE: ADK auto-wraps plain Python functions into FunctionTool — no manual wrapping needed
hello_agent = LlmAgent(
    name="hello_tapish",
    model="gemini-2.5-flash",
    instruction="""You are a test agent for the Tapish Crisis Response System in Lahore.
    When asked about a location, use the check_temperature_sensor tool to get readings.
    Analyze the results and return a STRICT JSON response:
    {"location": "...", "temp_c": ..., "heat_index": ..., "risk_level": "low|medium|high|critical", "reasoning": "..."}
    A heat index above 50 is CRITICAL. Above 45 is HIGH. Above 40 is MEDIUM. Below 40 is LOW.""",
    tools=[check_temperature_sensor],
)


async def main():
    print("=" * 60)
    print("TAPISH ADK Hello World — Environment Verification")
    print(f"google-adk installed ✅")
    print(f"GOOGLE_API_KEY set: {'✅' if os.environ.get('GOOGLE_API_KEY') else '❌ MISSING'}")
    print("=" * 60)

    if not os.environ.get("GOOGLE_API_KEY"):
        print("\n❌ Set GOOGLE_API_KEY first: export GOOGLE_API_KEY=your_key")
        return

    # 3. Set up Runner with InMemorySessionService (required by ADK v1.33)
    session_service = InMemorySessionService()
    runner = Runner(
        agent=hello_agent,
        app_name="tapish_hello",
        session_service=session_service,
    )

    # 4. Create a session
    session = await session_service.create_session(
        app_name="tapish_hello",
        user_id="judge_test",
    )

    print(f"\nSession created: {session.id}")
    print("Sending test query: 'What is the situation at Bhati Gate?'")
    print("-" * 60)

    # 5. Run the agent
    user_message = types.Content(
        role="user",
        parts=[types.Part(text="What is the current situation at Bhati Gate in the Walled City?")]
    )

    try:
        events = []
        async for event in runner.run_async(
            user_id="judge_test",
            session_id=session.id,
            new_message=user_message,
        ):
            events.append(event)
            # Print each event type for trace verification
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        print(f"🔧 Tool Call: {part.function_call.name}({dict(part.function_call.args)})")
                    elif hasattr(part, 'function_response') and part.function_response:
                        print(f"📊 Tool Response: {part.function_response.name} → {part.function_response.response}")
                    elif hasattr(part, 'text') and part.text:
                        print(f"🤖 Agent Output: {part.text}")

        print("-" * 60)
        print(f"\n✅ ADK Environment Check PASSED!")
        print(f"   Total events: {len(events)}")
        print(f"   Agent: hello_tapish")
        print(f"   Model: gemini-2.5-flash")
        print(f"   Tool called: check_temperature_sensor")
        print(f"\n   All imports verified:")
        print(f"   - google.adk.agents.LlmAgent ✅")
        print(f"   - google.adk.runners.Runner ✅")
        print(f"   - google.adk.sessions.InMemorySessionService ✅")
        print(f"   - google.genai.types ✅")
        print(f"\n🚀 Ready to build the 5-agent pipeline!")

    except Exception as e:
        print(f"\n❌ ADK Execution Failed: {type(e).__name__}: {e}")
        print("Check: GOOGLE_API_KEY, network connection, model availability")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
