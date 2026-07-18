from sqlalchemy import update

from app.models import Payment, User


def test_coupon_redeem_grants_five_credits(client, user):
    resp = client.post("/billing/coupon", json={"code": "SID_DRDROID"})
    assert resp.status_code == 200
    assert resp.json()["credits"] == 5


def test_coupon_wrong_code_rejected(client, user):
    resp = client.post("/billing/coupon", json={"code": "WRONG"})
    assert resp.status_code == 400


def test_coupon_cannot_be_redeemed_twice(client, user):
    first = client.post("/billing/coupon", json={"code": "SID_DRDROID"})
    assert first.status_code == 200

    second = client.post("/billing/coupon", json={"code": "SID_DRDROID"})
    assert second.status_code == 400

    # credits granted exactly once, not twice
    assert client.get("/me").json()["credits"] == 5


def test_atomic_credit_decrement_refuses_when_zero(db_session, user):
    """Mirrors the guard used before every agent run in threads.send_message."""
    assert user.credits == 0

    result = db_session.execute(update(User).where(User.id == user.id, User.credits > 0).values(credits=User.credits - 1))
    db_session.commit()

    assert result.rowcount == 0
    assert db_session.get(User, user.id).credits == 0


def test_atomic_credit_decrement_succeeds_when_positive(db_session, user):
    user.credits = 1
    db_session.commit()

    result = db_session.execute(update(User).where(User.id == user.id, User.credits > 0).values(credits=User.credits - 1))
    db_session.commit()

    assert result.rowcount == 1
    assert db_session.get(User, user.id).credits == 0


def test_webhook_is_idempotent_on_duplicate_session(client, db_session, user, monkeypatch):
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test_123", "amount_total": 500, "metadata": {"user_id": user.id}}},
    }
    monkeypatch.setattr("app.billing.stripe.Webhook.construct_event", lambda *a, **k: event)

    first = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "sig"})
    second = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "sig"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert db_session.get(User, user.id).credits == 5  # not 10
    assert db_session.query(Payment).filter(Payment.stripe_session_id == "cs_test_123").count() == 1
