from app.logging_config import scrub_event


def test_scrub_event_redacts_nested_payload() -> None:
    event = {
        "event": "request from student@vinuni.edu.vn",
        "payload": {
            "message_preview": "card 4111 1111 1111 1111",
            "nested": {"contact": "phone 0987 654 321"},
        },
        "details": ["passport: B1234567"],
    }

    out = scrub_event(None, "info", event)

    assert "student@" not in out["event"]
    assert "4111" not in out["payload"]["message_preview"]
    assert "0987" not in out["payload"]["nested"]["contact"]
    assert "B1234567" not in out["details"][0]
