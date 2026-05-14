from retrace import check_ledger_report
from retrace.checks import (
    check_accum_monotone,
    check_defect_conservation,
    check_defect_tally,
    check_row_sequence,
    summarize_defects,
)


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


def test_check_ledger_report_duplicate_consecutive_step_fails():
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
                "step": "drop_a",
                "complexity_before": 15,
                "complexity_after": 10,
                "defect": 5,
                "accumulated_defect": 10,
                "ledger": 20,
            },
        ]
    )

    assert conserved is False
    assert "duplicate consecutive step name" in reasons[0]


def test_check_ledger_report_defect_conservation_fails():
    conserved, reasons = check_ledger_report(
        [
            {
                "step": "drop_a",
                "complexity_before": 20,
                "complexity_after": 18,
                "defect": 2,
                "accumulated_defect": 2,
                "ledger": 20,
            },
            {
                "step": "drop_b",
                "complexity_before": 18,
                "complexity_after": 14,
                "defect": 3,
                "accumulated_defect": 6,
                "ledger": 20,
            },
        ]
    )

    assert conserved is False
    assert "ledger drift detected" in reasons[0]


def test_check_ledger_report_accumulated_defect_decrease_fails():
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
                "complexity_after": 16,
                "defect": -1,
                "accumulated_defect": 4,
                "ledger": 20,
            },
        ]
    )

    assert conserved is False
    assert "accumulated_defect decreased" in reasons[0]


def test_check_ledger_report_defect_tally_mismatch_fails():
    conserved, reasons = check_ledger_report(
        [
            {
                "step": "drop_a",
                "complexity_before": 20,
                "complexity_after": 18,
                "defect": 2,
                "accumulated_defect": 2,
                "ledger": 20,
            },
            {
                "step": "drop_b",
                "complexity_before": 18,
                "complexity_after": 16,
                "defect": 3,
                "accumulated_defect": 4,
                "ledger": 20,
            },
            {
                "step": "drop_c",
                "complexity_before": 16,
                "complexity_after": 14,
                "defect": 1,
                "accumulated_defect": 6,
                "ledger": 20,
            },
        ]
    )

    assert conserved is False
    assert "running defect total != accumulated_defect" in reasons[0]


def test_summarize_defects_groups_by_step_without_mutating_rows():
    rows = [
        {"step": "drop_a", "defect": 2, "accumulated_defect": 2},
        {"step": "drop_b", "defect": 3, "accumulated_defect": 5},
        {"step": "drop_a", "defect": 4, "accumulated_defect": 9},
    ]
    expected_rows = [
        {"step": "drop_a", "defect": 2, "accumulated_defect": 2},
        {"step": "drop_b", "defect": 3, "accumulated_defect": 5},
        {"step": "drop_a", "defect": 4, "accumulated_defect": 9},
    ]

    totals = summarize_defects(rows)

    assert totals == {"drop_a": 6, "drop_b": 3}
    assert rows == expected_rows


def test_check_defect_conservation_valid_rows_pass():
    rows = [
        {"step": "drop_a", "defect": 2, "accumulated_defect": 2},
        {"step": "drop_b", "defect": 3, "accumulated_defect": 5},
    ]

    reasons = check_defect_conservation(rows)

    assert reasons == []


def test_check_defect_conservation_object_instead_of_list_fails():
    reasons = check_defect_conservation({"ledger": []})

    assert "malformed report" in reasons[0]


def test_check_defect_conservation_empty_list_fails():
    reasons = check_defect_conservation([])

    assert "empty ledger report" in reasons[0]


def test_check_defect_conservation_missing_required_field_fails():
    reasons = check_defect_conservation(
        [{"step": "drop_a", "defect": 2}]
    )

    assert "missing required field" in reasons[0]


def test_check_defect_conservation_non_numeric_defect_fails():
    reasons = check_defect_conservation(
        [{"step": "drop_a", "defect": "2", "accumulated_defect": 2}]
    )

    assert "identity violated" in reasons[0]


def test_check_defect_conservation_sum_mismatch_fails():
    rows = [
        {"step": "drop_a", "defect": 2, "accumulated_defect": 2},
        {"step": "drop_b", "defect": 3, "accumulated_defect": 6},
    ]

    reasons = check_defect_conservation(rows)

    assert any("ledger drift detected" in reason for reason in reasons)


def test_check_accum_monotone_valid_rows_pass():
    rows = [
        {"step": "drop_a", "defect": 2, "accumulated_defect": 2},
        {"step": "drop_b", "defect": 0, "accumulated_defect": 2},
        {"step": "drop_c", "defect": 3, "accumulated_defect": 5},
    ]

    reasons = check_accum_monotone(rows)

    assert reasons == []


def test_check_accum_monotone_decreasing_pair_fails():
    rows = [
        {"step": "drop_a", "defect": 5, "accumulated_defect": 5},
        {"step": "drop_b", "defect": 0, "accumulated_defect": 4},
        {"step": "drop_c", "defect": 2, "accumulated_defect": 6},
    ]

    reasons = check_accum_monotone(rows)

    assert len(reasons) == 1
    assert "ledger drift detected" in reasons[0]


def test_check_accum_monotone_missing_accumulated_defect_fails():
    reasons = check_accum_monotone(
        [{"step": "drop_a", "defect": 2}]
    )

    assert "missing required field" in reasons[0]


def test_check_accum_monotone_non_numeric_accumulated_defect_fails():
    reasons = check_accum_monotone(
        [{"step": "drop_a", "defect": 2, "accumulated_defect": "2"}]
    )

    assert "identity violated" in reasons[0]


def test_check_defect_tally_valid_rows_pass():
    rows = [
        {"step": "drop_a", "defect": 2, "accumulated_defect": 2},
        {"step": "drop_b", "defect": 0, "accumulated_defect": 2},
        {"step": "drop_c", "defect": 3, "accumulated_defect": 5},
    ]

    reasons = check_defect_tally(rows)

    assert reasons == []


def test_check_defect_tally_later_mismatch_fails():
    rows = [
        {"step": "drop_a", "defect": 2, "accumulated_defect": 2},
        {"step": "drop_b", "defect": 3, "accumulated_defect": 4},
        {"step": "drop_c", "defect": 1, "accumulated_defect": 6},
    ]

    reasons = check_defect_tally(rows)

    assert len(reasons) == 1
    assert "ledger drift detected" in reasons[0]


def test_check_defect_tally_missing_defect_fails():
    reasons = check_defect_tally(
        [{"step": "drop_a", "accumulated_defect": 2}]
    )

    assert "missing required field" in reasons[0]


def test_check_defect_tally_non_numeric_defect_fails():
    reasons = check_defect_tally(
        [{"step": "drop_a", "defect": "2", "accumulated_defect": 2}]
    )

    assert "identity violated" in reasons[0]


def test_check_row_sequence_valid_rows_pass():
    rows = [
        {"step": "drop_a"},
        {"step": "drop_b"},
        {"step": "drop_a"},
    ]

    reasons = check_row_sequence(rows)

    assert reasons == []


def test_check_row_sequence_empty_list_fails():
    reasons = check_row_sequence([])

    assert "empty ledger report" in reasons[0]


def test_check_row_sequence_non_dict_row_fails():
    reasons = check_row_sequence([{"step": "drop_a"}, "drop_b"])

    assert "malformed report" in reasons[0]


def test_check_row_sequence_duplicate_consecutive_step_name_fails():
    rows = [
        {"step": "drop_a"},
        {"step": "drop_a"},
        {"step": "drop_b"},
    ]

    reasons = check_row_sequence(rows)

    assert len(reasons) == 1
    assert "ledger drift detected" in reasons[0]


def test_check_row_sequence_empty_step_name_fails():
    reasons = check_row_sequence([{"step": ""}])

    assert "malformed report" in reasons[0]
