import pytest
from agnostic_llm.employees import (
    EmployeeRoster,
    create_alex,
    create_morgan,
    create_taylor,
    create_elena,
    create_supervisor,
    create_jack,
)
from agnostic_llm.providers.mock import MockLLM
from agnostic_llm.macos import MacOSStore
from agnostic_llm.types import LLMResponse, ToolCall


@pytest.fixture
def store(tmp_path):
    return MacOSStore(db_path=tmp_path / "test.db")


def test_alex_day_planner_tools(store):
    alex = create_alex(store)
    tool_map = {t.name: t for t in alex.tools}

    # Test create_task
    res = tool_map["create_task"].fn(title="Review Q4 Goals", priority="high", category="Planning")
    assert "Task #" in res and "Review Q4 Goals" in res

    # Test list_tasks
    tasks_res = tool_map["list_tasks"].fn()
    assert "Review Q4 Goals" in tasks_res

    # Test complete_task
    comp_res = tool_map["complete_task"].fn("Review Q4 Goals")
    assert "completed" in comp_res

    # Test schedule_meeting
    meet_res = tool_map["schedule_meeting"].fn(title="Client Sync", start_time="2026-11-12 11:00", duration_minutes=30)
    assert "Client Sync" in meet_res

    # Test get_daily_agenda
    agenda = tool_map["get_daily_agenda"].fn("2026-11-12")
    assert "Client Sync" in agenda


def test_morgan_freelance_hunter_tools(store):
    morgan = create_morgan(store)
    tool_map = {t.name: t for t in morgan.tools}

    # Test add_lead
    lead_res = tool_map["add_lead"].fn(client_name="Starlight Labs", company="Starlight", project_scope="AI Agents", estimated_value="$12,000")
    assert "Starlight Labs" in lead_res and "$12,000" in lead_res

    # Test list_leads
    leads_res = tool_map["list_leads"].fn()
    assert "Starlight Labs" in leads_res

    # Test calculate_rate_quote
    quote_res = tool_map["calculate_rate_quote"].fn(hourly_rate=150.0, estimated_hours=40.0, value_markup_percentage=30.0)
    assert "$6,000.00" in quote_res
    assert "$7,800.00" in quote_res

    # Test draft_pitch_proposal
    pitch_res = tool_map["draft_pitch_proposal"].fn(
        client_name="Sarah",
        client_pain_point="slow content delivery",
        proposed_solution="an automated agent workflow",
        pricing="$9,500"
    )
    assert "Sarah" in pitch_res and "$9,500" in pitch_res


def test_taylor_marketing_tools(store):
    taylor = create_taylor(store)
    tool_map = {t.name: t for t in taylor.tools}

    # Test generate_social_campaign
    camp_res = tool_map["generate_social_campaign"].fn(topic="AI pair programming", target_audience="Founders")
    assert "AI pair programming" in camp_res

    # Test analyze_hook
    hook_res = tool_map["analyze_hook"].fn(hook_text="How we scaled from 0 to 10k users without spending on ads")
    assert "Hook Analysis" in hook_res

    # Test build_content_calendar
    cal_res = tool_map["build_content_calendar"].fn(niche="Solo Entrepreneurship", days_ahead=5)
    assert "Content Cadence" in cal_res


def test_elena_empathy_and_manuscript_tools(store):
    elena = create_elena(store)
    tool_map = {t.name: t for t in elena.tools}

    # Test refine_empathetic_tone
    refined = tool_map["refine_empathetic_tone"].fn(text="We need to delay your project by two days.")
    assert "Empathetic Calibration" in refined

    # Test outline_book
    outline = tool_map["outline_book"].fn(theme="The Calm Machine", premise="Leveraging AI without burnout", target_reader="Knowledge workers")
    assert "The Calm Machine" in outline
    assert "Chapter 1" in outline

    # Test analyze_sentiment_and_intent
    analysis = tool_map["analyze_sentiment_and_intent"].fn(incoming_message="Why is this taking so long? We need it now.")
    assert "Emotional Intelligence Breakdown" in analysis


def test_supervisor_standup_and_delegation(store):
    roster = EmployeeRoster(store=store)
    supervisor = roster.get("supervisor")
    morgan = roster.get("morgan")

    # Morgan has a mock LLM
    morgan.set_llm(MockLLM(["Morgan: Here is the customized pitch for $15,000."]))

    # Supervisor delegates to Morgan
    supervisor.set_llm(MockLLM([
        LLMResponse(
            tool_calls=[ToolCall("call-1", "delegate_task", {"target_employee": "Morgan", "instruction": "Draft $15k pitch"})],
            stop_reason="tool_calls"
        ),
        "Supervisor: Morgan has finalized the $15,000 pitch."
    ]))

    res = supervisor.chat("Get me a $15,000 proposal from Morgan")
    assert "Morgan has finalized the $15,000 pitch" in res.text


def test_jack_coding_employee(store):
    jack = create_jack(store)
    assert jack.name == "Jack"
    assert jack.route == "copilot"
    assert {tool.name for tool in jack.tools} >= {
        "inspect_repository",
        "run_project_tests",
        "delegate_task",
    }


def test_config_preserves_specialized_employees(store):
    roster = EmployeeRoster.from_config("config.yaml", store=store)
    jack = roster.get("jack")
    assert jack is not None
    assert jack.route == "copilot"
    assert "run_project_tests" in {tool.name for tool in jack.tools}

