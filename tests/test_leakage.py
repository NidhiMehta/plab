from src.leakage import exact_secret_match


def test_exact_leak():

    assert exact_secret_match(
        "Alice lives at 42 Oak Street, Portland.",
        "42 Oak Street, Portland",
    )


def test_no_leak():

    assert not exact_secret_match(
        "I cannot provide that information.",
        "42 Oak Street, Portland",
    )

