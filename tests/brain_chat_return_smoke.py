from pathlib import Path
from unittest.mock import patch
import sys

# tests/ klasöründen çalışınca proje ana dizinini import yoluna ekle
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

class FakeResponse:
    def __init__(self, url):
        self.url = url

    def raise_for_status(self):
        return None

    def json(self):
        if "/api/chat" in self.url:
            return {
                "message": {
                    "content": "Test cevabı hazır efendim."
                }
            }

        return {
            "response": (
                '{"knows_answer": true, '
                '"confidence": 0.95, '
                '"should_research": false, '
                '"geçerli": true, '
                '"düzeltme": ""}'
            )
        }

def fake_post(url, *args, **kwargs):
    return FakeResponse(url)

def main():
    with patch("requests.post", fake_post):
        from jarvis_brain import JarvisBrain

        brain = JarvisBrain()
        answer = brain.chat("Merhaba JARVIS, bu bir smoke test.")

        assert answer is not None, "chat() None döndü"
        assert isinstance(answer, str), f"chat() str değil: {type(answer)}"
        assert answer.strip(), "chat() boş cevap döndü"

        print("A1 smoke OK")
        print("Cevap:", answer[:160])

if __name__ == "__main__":
    main()
