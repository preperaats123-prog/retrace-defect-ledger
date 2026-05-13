from retrace import check_ledger_report


def test_check_ledger_report_valid_rows_pass():
    rows = [
        {
            "step": "drop_a",
            "complexity_before": 20,
            "complexity_after": 15,
            "defect": 5,
            "accumulated_defect": 5,
            "ledger": 20,
        },
        {
            "step": "drop_b",
            "complexity_before": 15,
            "complexity_after": 10,
            "defect": 5,
            "accumulated_defect": 10,
            "ledger": 20,
        },
    ]

    conserved, reasons = check_ledger_report(rows)

    assert conserved is True
    assert reasons == []


def test_check_ledger_report_object_instead_of_list_fails():
    conserved, reasons = check_ledger_report({"ledger": []})

    assert conserved is False
    assert "malformed report" in reasons[0]


def test_check_ledger_report_empty_list_fails():
    conserved, reasons = check_ledger_report([])

    assert conserved is False
    assert "empty ledger report" in reasons[0]


def test_check_ledger_report_missing_required_field_fails():
    conserved, reasons = check_ledger_report(
        [
            {
                "step": "drop_a",
                "complexity_before": 20,
                "complexity_after": 15,
                "defect": 5,
                "ledger": 20,
            }
        ]
    )

    assert conserved is False
    assert "missing required field" in reasons[0]


def test_check_ledger_report_identity_violation_fails():
    conserved, reasons = check_ledger_report(
        [
            {
                "step": "drop_a",
                "complexity_before": 20,
                "complexity_after": 15,
                "defect": 5,
                "accumulated_defect": 4,
                "ledger": 20,
            }
        ]
    )

    assert conserved is False
    assert "identity violated" in reasons[0]


def test_check_ledger_report_ledger_drift_fails():
    conserved, reasons = check_ledger_report(
        [
            {
                "step": "drop_a",
                "complexity_before": 20,
                "complexity_after": 15,
                "defect": 5,
                "accumulated_defect": 5,
                "ledger": 20,
            },
            {
                "step": "drop_b",
                "complexity_before": 15,
                "complexity_after": 11,
                "defect": 4,
                "accumulated_defect": 10,
                "ledger": 21,
            },
        ]
    )

    assert conserved is False
    assert any("ledger drift detected" in reason for reason in reasons)
