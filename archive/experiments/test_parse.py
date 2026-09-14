from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_data(self):
        return ''.join(self.text)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data().strip()

data = {"de":[{"partOfSpeech":"Noun","language":"German","definitions":[{"definition":"<a rel=\"mw:WikiLink\" href=\"/wiki/house_cat\" title=\"house cat\">house cat</a>, <span class=\"biota\"><i>Felis silvestris catus</i></span>"},{"definition":"female <a href=\"/wiki/house_cat\">house cat</a>"}]}]}

lines = []
for entry in data.get("de", []):
    pos = entry.get("partOfSpeech", "Definition")
    lines.append(f"[{pos}]")
    for i, d in enumerate(entry.get("definitions", []), 1):
        clean_def = strip_tags(d.get("definition", ""))
        lines.append(f"  {i}. {clean_def}")

print("\n".join(lines))
