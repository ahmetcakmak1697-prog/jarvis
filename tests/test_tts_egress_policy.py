"""B05 -- ses cikisi veri sinifini denetlemeli.

Codex basmuhendis denetimi (2026-09-06): `VoiceIO.say` metni bicimsel olarak
temizleyip dogrudan sentezleyiciye veriyordu. Adaptor yalnizca acma bayragini
ve bos metni kontrol ediyor, ICERIK SINIFINI bilmiyor. Bayrak acikken
`parola=FAKE_AUDIT_MARKER` metni aynen sentezleyiciye ulasti.

Neden onemli: **Edge TTS cevrimici bir servistir.** Seslendirilen her cumle
Microsoft'un sunucusuna gider. "Ollama kullaniyoruz, veri disari cikmiyor"
ifadesi bu yol icin dogru degil.

Varsayilan kapali olmasi olumlu bir koruma ama yeterli degil: TTS'i genel
olarak acmak, her hassas cumlenin de disari cikmasina izin vermekle ayni sey
degildir (Codex'in kendi ifadesi).

Yerel bir sentezleyici (ornegin Piper) bu sorunu tasimaz. O yuzden kapi
`speaker.is_local` bayragina bakar: yerel oldugunu BEYAN eden bir adaptor
hassas metni de seslendirebilir. Piper cephesini yeniden acmak bu duzeltmenin
onkosulu degildir (Codex) -- bayrak yalnizca kapinin dogru yerde durmasini
saglar, yeni bir cephe acmaz.
"""
from __future__ import annotations

#: Sentetik isaretci -- gercek bir sir degil. `RedactionGuard` bu bicimi
#: (`parola=...`) hassas sayiyor; olculdu 2026-09-06.
HASSAS = "parola=FAKE_AUDIT_MARKER_7719"
NORMAL = "Bugun hava guzel efendim."


class _SahteSentezleyici:
    """Gercek TTS yerine gecer; ne aldigini ve kac kez cagrildigini tutar."""

    is_local = False   # varsayilan: bulut sentezleyici gibi davran

    def __init__(self) -> None:
        self.cagri_sayisi = 0
        self.duyulan: list[str] = []

    def speak(self, text: str):
        self.cagri_sayisi += 1
        self.duyulan.append(text)
        return None


class _YerelSentezleyici(_SahteSentezleyici):
    """Makineden ayrilmayan bir sentezleyici (ornegin Piper)."""

    is_local = True


def _voice_io(speaker):
    from voice.voice_loop import VoiceIO

    duyurular: list[str] = []
    vio = VoiceIO(
        listener=None,
        speaker=speaker,
        keyboard=lambda _p: "",
        notify=duyurular.append,
        enabled=True,
    )
    return vio, duyurular


def test_hassas_metin_bulut_sentezleyiciye_gitmez():
    """`parola=...` iceren cevap Edge TTS'e gonderilmez."""
    sp = _SahteSentezleyici()
    vio, duyurular = _voice_io(sp)

    vio.say(f"Efendim, {HASSAS} olarak kayitli.")

    assert sp.cagri_sayisi == 0, "hassas metin bulut sentezleyiciye ulasti"
    assert any(duyurular), "engel sessiz olmamali -- kullaniciya soylenmeli"


def test_ham_sir_hicbir_sekilde_sentezleyiciye_ulasmaz():
    """Engellendiginde bile ham isaretci sentezleyiciye sizmamali."""
    sp = _SahteSentezleyici()
    vio, _ = _voice_io(sp)

    vio.say(f"Efendim, {HASSAS} olarak kayitli.")

    for metin in sp.duyulan:
        assert "FAKE_AUDIT_MARKER_7719" not in metin, (
            f"ham isaretci sentezleyiciye ulasti: {metin!r}"
        )


def test_normal_metin_hala_seslendirilir():
    """Kapi her seyi kesmemeli -- gunluk kullanim bozulmamali."""
    sp = _SahteSentezleyici()
    vio, _ = _voice_io(sp)

    vio.say(NORMAL)

    assert sp.cagri_sayisi == 1, "normal metin seslendirilmedi"
    assert NORMAL in sp.duyulan[0]


def test_yerel_sentezleyici_hassas_metni_de_seslendirir():
    """Makineden cikis yoksa kisitlamaya da gerek yok."""
    sp = _YerelSentezleyici()
    vio, _ = _voice_io(sp)

    vio.say(f"Efendim, {HASSAS} olarak kayitli.")

    assert sp.cagri_sayisi == 1, (
        "yerel sentezleyicide kisitlama gereksiz; kapi fazla genis"
    )


def test_guard_arizasinda_seslendirme_KAPANIR(monkeypatch):
    """Sinif belirlenemiyorsa metin disari CIKMAZ.

    Codex B10 router'da bunun tersini buldu: redaction hatasi `except: pass`
    ile geciliyor ve dis cagri yine de yapiliyordu. Ariza durumunda dogru
    davranis kapatmaktir, acmak degil.
    """
    import voice.voice_loop as vl

    def _patlayan(*_a, **_k):
        raise RuntimeError("guard bozuk")

    monkeypatch.setattr(vl, "_hassas_mi", _patlayan, raising=False)

    sp = _SahteSentezleyici()
    vio, duyurular = _voice_io(sp)
    vio.say(NORMAL)

    assert sp.cagri_sayisi == 0, "guard arizasinda yine de seslendirdi"
    assert any(duyurular), "ariza sessiz gecmemeli"


def test_kapi_speech_text_SONRASI_calisir():
    """Sinif denetimi, sentezleyiciye giden NIHAI metin uzerinde olmali.

    `speech_text()` markdown'i temizliyor; kod bloklarini "(kod blogu ekranda)"
    ile degistiriyor. Denetim ondan once yapilirsa, temizlik sirasinda ortaya
    cikan bir icerik denetimsiz kalabilir.
    """
    sp = _SahteSentezleyici()
    vio, _ = _voice_io(sp)

    # Kod blogu icindeki sir -- speech_text onu zaten ayikliyor.
    vio.say(f"Sonuc:\n\n```\n{HASSAS}\n```\n\nTamamdir efendim.")

    for metin in sp.duyulan:
        assert "FAKE_AUDIT_MARKER_7719" not in metin
