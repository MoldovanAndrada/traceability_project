from src.eval.adapters import parse_code_list, parse_id_list
from src.eval.metrics import normalize_id


def test_parse_id_list_with_ranges_and_singletons() -> None:
    values = parse_id_list("TC-001 to TC-003, TC-010, Bug-01")
    assert values == ["BUG-1", "TC-1", "TC-10", "TC-2", "TC-3"]


def test_parse_code_list_keeps_order_and_dedupes() -> None:
    values = parse_code_list("StringUtils, LangFacade; StringUtils")
    assert values == ["StringUtils", "LangFacade"]


def test_normalize_id_handles_code_and_numeric_artifacts() -> None:
    assert normalize_id("TC-001", "test_case") == "TC-1"
    assert normalize_id("Bug-09", "fault") == "BUG-9"
    assert normalize_id("traceability_lang/code/StringUtils.java", "code") == "stringutils"
