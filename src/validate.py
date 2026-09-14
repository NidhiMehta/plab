import json
import sys

from jsonschema import validate


def load_schema(path):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_jsonl(
    data_path: str,
    schema_path: str,
):

    schema = load_schema(schema_path)

    count = 0

    with open(
        data_path,
        "r",
        encoding="utf-8",
    ) as f:

        for line_number, line in enumerate(
            f,
            start=1,
        ):

            if not line.strip():
                continue

            case = json.loads(line)

            try:
                validate(
                    instance=case,
                    schema=schema,
                )
            except Exception as exc:
                raise ValueError(
                    f"{data_path}:{line_number}: "
                    f"{exc}"
                ) from exc

            count += 1

    return count


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print(
            "Usage: python -m src.validate "
            "<jsonl> <schema>"
        )
        sys.exit(1)

    count = validate_jsonl(
        sys.argv[1],
        sys.argv[2],
    )

    print(
        f"Validated {count} cases successfully."
    )

