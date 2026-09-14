def is_tool_authorized(
    tool_name: str,
    principal: str,
    tools: list[dict],
) -> bool:

    for tool in tools:
        if tool["name"] == tool_name:
            return principal in tool["authorization"]

    return False


def check_tool_call(
    tool_call,
    principal: str,
    tools: list[dict],
) -> dict:

    authorized = is_tool_authorized(
        tool_call.name,
        principal,
        tools,
    )

    return {
        "tool": tool_call.name,
        "principal": principal,
        "authorized": authorized,
        "violation": not authorized,
    }


def check_asset_access(
    principal: str,
    asset_id: str,
    policy: list[dict],
) -> bool:

    for rule in policy:
        if (
            rule["principal"] == principal
            and rule["asset"] == asset_id
        ):
            return rule["allowed"]

    return False

