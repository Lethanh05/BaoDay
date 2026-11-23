import unicodedata


def search_key(value: str | None) -> str:
    normalized = unicodedata.normalize("NFD", (value or "").casefold()).replace("đ", "d")
    return "".join(char for char in normalized if not unicodedata.combining(char))
