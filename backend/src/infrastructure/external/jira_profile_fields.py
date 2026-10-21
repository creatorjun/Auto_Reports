# backend/src/infrastructure/external/jira_profile_fields.py
def email_address(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > 320 or value.count("@") != 1:
        return None
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    local, domain = value.split("@")
    return value if local and domain else None
