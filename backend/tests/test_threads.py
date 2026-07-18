import pytest
from fastapi import HTTPException

from app.models import Thread
from app.threads import RATE_LIMIT, _check_rate_limit, _recent_sends


@pytest.fixture()
def thread(db_session, user):
    t = Thread(user_id=user.id, model="kimi-k2", title="test chat")
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


def test_soft_delete_hides_thread_but_keeps_stats(client, user, thread):
    assert client.delete(f"/threads/{thread.id}").status_code == 204

    listed = client.get("/threads").json()
    assert all(t["id"] != thread.id for t in listed)

    stats_row = next(r for r in client.get("/stats").json() if r["thread_id"] == thread.id)
    assert "(deleted)" in stats_row["title"]

    assert client.post(f"/threads/{thread.id}/messages", json={"content": "hi"}).status_code == 404


def test_delete_other_users_thread_is_404(client, user, db_session, thread):
    from app.models import User

    other = User(email="other@example.com", provider="google")
    db_session.add(other)
    db_session.commit()
    thread.user_id = other.id
    db_session.commit()

    assert client.delete(f"/threads/{thread.id}").status_code == 404


def test_rate_limit_allows_burst_then_429():
    _recent_sends.clear()
    for _ in range(RATE_LIMIT):
        _check_rate_limit("u1")
    with pytest.raises(HTTPException) as exc:
        _check_rate_limit("u1")
    assert exc.value.status_code == 429
    _check_rate_limit("u2")  # other users unaffected
    _recent_sends.clear()


def test_pdf_export_handles_long_urls_and_unicode(client, user, thread, db_session):
    from app.models import Message

    content = (
        "# Report\n\n"
        "Some finding [1] with unicode — em-dash and “quotes”.\n\n"
        "- bullet point\n\n"
        "## Sources\n\n"
        "1. https://example.com/" + "a" * 300 + "\n"
    )
    msg = Message(thread_id=thread.id, role="assistant", content=content)
    db_session.add(msg)
    db_session.commit()

    res = client.get(f"/threads/{thread.id}/messages/{msg.id}/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
