"""Unit-level detector classification (no Graph, no DB writes)."""

from ww_core import db as core_db

from ww_engine import detector


def _send(conn, lead_id, conv, marker):
    conn.execute(
        "INSERT INTO sends (id, lead_id, subject, body_text, sent_at, "
        "conversation_id, marker_token) VALUES (?,?,?,?,CURRENT_TIMESTAMP,?,?)",
        (f"s_{lead_id}", lead_id, "s", "b", conv, marker))
    conn.commit()


def test_classify_reply_by_conversation(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _send(conn, "lead0", "CONV1", "MK1")
        msg = {"id": "m1", "conversation_id": "CONV1", "from_addr": "x@y.com",
               "headers": {}, "body": "interested", "refs": []}
        assert detector.classify(conn, msg) == ("replied", "lead0")
    finally:
        conn.close()


def test_classify_bounce_by_marker_in_ndr(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _send(conn, "lead1", "CONV2", "MK2")
        msg = {"id": "b1", "conversation_id": "nomatch",
               "from_addr": "postmaster@srv.com", "headers": {},
               "body": "delivery failed ref MK2", "refs": []}
        assert detector.classify(conn, msg) == ("bounced", "lead1")
    finally:
        conn.close()


def test_autoreply_and_unmatched_return_none(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _send(conn, "lead2", "CONV3", "MK3")
        auto = {"id": "a", "conversation_id": "CONV3", "from_addr": "x@y.com",
                "headers": {"auto-submitted": "auto-replied"}, "body": "OOO",
                "refs": []}
        unmatched = {"id": "u", "conversation_id": "ZZZ", "from_addr": "x@y.com",
                     "headers": {}, "body": "who?", "refs": []}
        assert detector.classify(conn, auto) is None
        assert detector.classify(conn, unmatched) is None
    finally:
        conn.close()
