from unittest.mock import MagicMock, Mock

import pytest

import database
from audit_fixtures import audited_app, log_file
from partner_history_service import get_partner_history
from partner_service import get_partner_with_discount, read_partners, save_partner
from partner_validation import PartnerNotFoundError


def connection_spy():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (42,)
    cursor.fetchall.return_value = []
    return connection, cursor


@pytest.mark.parametrize("partner_id", [None, 42])
def test_create_and_update_send_text_separately_from_sql(partner_id):
    connection, cursor = connection_spy()
    payload = "Компания'); DROP TABLE partners; --"
    values = {"company_name": payload, "partner_type": "ООО", "rating": "0",
              "address": payload, "director_name": payload, "phone": "",
              "contact_email": "test@example.ru", "inn": "1234567890"}
    assert save_partner(connection, values, partner_id) == 42
    query, parameters = cursor.execute.call_args.args
    assert payload not in query
    assert parameters.count(payload) == 3
    assert query.count("%s") == len(parameters)
    if partner_id is not None:
        assert parameters[-1] == partner_id


def test_lookup_binds_id_instead_of_interpolating_it():
    connection, cursor = connection_spy()
    payload = "1 OR 1=1; DROP TABLE partners; --"
    read_partners(connection, payload)
    query, parameters = cursor.execute.call_args.args
    assert payload not in query
    assert parameters == (payload,)
    assert "WHERE p.partner_id = %s" in query


def test_history_binds_both_id_parameters():
    connection, cursor = connection_spy()
    with pytest.raises(PartnerNotFoundError):
        get_partner_history(connection, 42)
    query, parameters = cursor.execute.call_args.args
    assert parameters == (42, 42)
    assert query.count("%s") == 2


@pytest.mark.parametrize("reader", [get_partner_with_discount, get_partner_history])
def test_public_readers_reject_injected_id_before_sql(reader):
    connection, cursor = connection_spy()
    with pytest.raises(ValueError):
        reader(connection, "1 OR 1=1")
    cursor.execute.assert_not_called()


def test_password_is_a_driver_argument_not_sql_or_dsn(monkeypatch):
    connect = Mock(return_value=object())
    monkeypatch.setattr(database.psycopg, "connect", connect)
    payload = "x' OR '1'='1 dbname=other password=changed"
    database.connect_database(payload)
    assert connect.call_args.args == ()
    assert connect.call_args.kwargs["password"] == payload
    assert connect.call_args.kwargs["dbname"] != "other"


def test_search_treats_sql_text_as_plain_substring(audited_app):
    application, errors, loader, _ = audited_app
    application.partners = [{"partner_id": 1, "company_name": "Обычный партнёр", "discount_percent": 0,
                             "total_quantity": 0, "rating": 0, "phone": None}]
    application.search_text.set("' OR 1=1 --")
    assert application.cards == []
    loader.assert_not_called()
    errors.assert_not_called()
