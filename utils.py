def parse_prompts(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return lines


def parse_verdict(text):
    if "UNSAFE" in text:
        return "UNSAFE"
    return "SAFE"
