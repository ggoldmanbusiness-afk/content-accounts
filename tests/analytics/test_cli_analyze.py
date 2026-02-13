import pytest
from cli.analyze import build_parser, load_all_platform_profiles


def test_parser_account_flag():
    parser = build_parser()
    args = parser.parse_args(["--account", "dreamtimelullabies"])
    assert args.account == "dreamtimelullabies"


def test_parser_all_flag():
    parser = build_parser()
    args = parser.parse_args(["--all"])
    assert args.all is True


def test_parser_dashboard_flag():
    parser = build_parser()
    args = parser.parse_args(["--account", "test", "--dashboard"])
    assert args.dashboard is True


def test_parser_focus_flag():
    parser = build_parser()
    args = parser.parse_args(["--account", "test", "--focus", "formats"])
    assert args.focus == "formats"


def test_parser_scrape_flag():
    parser = build_parser()
    args = parser.parse_args(["--scrape"])
    assert args.scrape is True
