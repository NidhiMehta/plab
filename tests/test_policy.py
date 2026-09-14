from src.policy import is_tool_authorized


def test_authorized_tool():

    tools = [
        {
            "name": "private_lookup",
            "description": "Private lookup",
            "authorization": ["alice"]
        }
    ]

    assert is_tool_authorized(
        "private_lookup",
        "alice",
        tools,
    )


def test_unauthorized_tool():

    tools = [
        {
            "name": "private_lookup",
            "description": "Private lookup",
            "authorization": ["alice"]
        }
    ]

    assert not is_tool_authorized(
        "private_lookup",
        "attacker",
        tools,
    )

