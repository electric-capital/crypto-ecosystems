"""Shell-like lexer for parsing migration command arguments."""


def split(line: str) -> list[str]:
    """
    Split a line into tokens, handling quotes and escapes.

    Rules:
    - Whitespace separates tokens
    - Single quotes (') and double quotes (") group tokens
    - Backslash (\\) escapes the next character
    - Quotes are removed from tokens
    - Escaped characters have backslash removed

    Args:
        line: The line to split

    Returns:
        List of parsed tokens

    Raises:
        ValueError: If quotes are unterminated
    """
    tokens = []
    i = 0
    line_len = len(line)

    while i < line_len:
        # Skip whitespace
        while i < line_len and line[i].isspace():
            i += 1

        if i >= line_len:
            break

        # Start of a token
        if line[i] in ('"', "'"):
            # Quoted token
            quote = line[i]
            start = i
            i += 1
            token_chars = []

            while i < line_len and line[i] != quote:
                if line[i] == "\\" and i + 1 < line_len:
                    # Escape next character
                    i += 1
                    token_chars.append(line[i])
                else:
                    token_chars.append(line[i])
                i += 1

            if i >= line_len:
                raise ValueError("Unterminated quote")

            tokens.append("".join(token_chars))
            i += 1  # Skip closing quote
        else:
            # Unquoted token
            token_chars = []

            while i < line_len and not line[i].isspace():
                if line[i] == "\\" and i + 1 < line_len:
                    # Escape next character
                    i += 1
                    token_chars.append(line[i])
                else:
                    token_chars.append(line[i])
                i += 1

            tokens.append("".join(token_chars))

    return tokens
