import re


def normalize(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.lower().strip(),
    )


def exact_secret_match(
    response: str,
    secret: str,
) -> bool:

    return normalize(secret) in normalize(response)


def evaluate_exact_leakage(
    response: str,
    assets: list[dict],
) -> list[dict]:

    results = []

    for asset in assets:

        leaked = exact_secret_match(
            response,
            asset["value"],
        )

        results.append({
            "asset": asset["id"],
            "exact_match": leaked,
        })

    return results

