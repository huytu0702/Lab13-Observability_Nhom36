from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_phone_vn() -> None:
    out = scrub_text("Call me at 0987 654 321")
    assert "0987" not in out
    assert "REDACTED_PHONE_VN" in out


def test_scrub_credit_card() -> None:
    out = scrub_text("My card is 4111 1111 1111 1111")
    assert "4111" not in out
    assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport_and_address() -> None:
    out = scrub_text("passport: B1234567; dia chi: 12 duong Nguyen Van Cu, Q5")
    assert "B1234567" not in out
    assert "REDACTED_PASSPORT" in out
    assert "duong Nguyen Van Cu" not in out
    assert "REDACTED_ADDRESS" in out
