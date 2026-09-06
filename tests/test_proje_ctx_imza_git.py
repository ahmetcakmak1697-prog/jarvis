"""A-06 -- proje baglami parmak izi GERCEK commit'i gormeli.

Codex kanitladi: bu worktree'de `HEAD` mtime'i 2026-06-17 (uc ay once),
commit atildiginda degisen dosya `refs/heads/...`. `HEAD` sembolik bir
referanstir (`ref: refs/heads/<dal>`); commit onun ne icerigini ne mtime'ini
degistirir. B06 parmak izi yalniz `HEAD`'i izledigi icin kurulma sebebini
yapmiyordu -- ajan acikken commit atilsa bile baglam bayat kaliyordu.

Testler GERCEK `git` calistirir ve GERCEK commit atar. Dosyaya `touch`
atarak "imza degisti" demek bu kusuru kacirirdi: kusur tam olarak
"commit atiliyor ama izlenen dosya degismiyor" idi.

Ayrica yukleyicinin okudugu her kaynak imzada olmali; okunup izlenmeyen bir
kaynak, sessizce bayatlayan bir baglam demektir.
"""
from __future__ import annotations

import json
import subprocess

import pytest


def _git(kok, *argv):
    subprocess.run(
        ["git", *argv], cwd=str(kok), check=True,
        capture_output=True, text=True,
    )


def _ajan():
    from agent.local_agent import LocalJarvisAgent

    return LocalJarvisAgent.__new__(LocalJarvisAgent)


def _commit(kok, dosya: str, icerik: str, mesaj: str):
    (kok / dosya).write_text(icerik, encoding="utf-8")
    _git(kok, "add", dosya)
    _git(kok, "commit", "-m", mesaj)


@pytest.fixture
def depo(tmp_path):
    """Icinde tek commit olan gercek bir git deposu."""
    kok = tmp_path / "depo"
    kok.mkdir()
    _git(kok, "init", "-b", "ana")
    _git(kok, "config", "user.email", "test@ornek")
    _git(kok, "config", "user.name", "Test")
    _git(kok, "config", "commit.gpgsign", "false")
    _commit(kok, "a.txt", "1\n", "ilk")
    return kok


def _head_bulundu_mu(imza) -> bool:
    return any(
        yol.replace("\\", "/").endswith("/HEAD") and mtime is not None
        for yol, mtime, _boyut in imza
    )


# ─── 1. Gercek commit imzayi degistirmeli ───────────────


def test_gercek_commit_imzayi_degistirir(depo):
    """Ana kusur: commit atildi, izlenen hicbir sey degismedi."""
    a = _ajan()

    once = a._proje_ctx_imzasi(depo)
    _commit(depo, "a.txt", "2\n", "ikinci")
    sonra = a._proje_ctx_imzasi(depo)

    assert sonra != once, (
        "commit atildi ama parmak izi ayni kaldi -- baglam bayat kalir"
    )


def test_worktree_commiti_imzayi_degistirir(tmp_path, depo):
    """Codex'in bildirdigi tam senaryo: bagli worktree uzerinde commit."""
    wt = tmp_path / "wt"
    _git(depo, "worktree", "add", str(wt), "-b", "dal")
    _git(wt, "config", "user.email", "test@ornek")
    _git(wt, "config", "user.name", "Test")

    a = _ajan()
    once = a._proje_ctx_imzasi(wt)
    _commit(wt, "b.txt", "x\n", "worktree commit")
    sonra = a._proje_ctx_imzasi(wt)

    assert sonra != once, (
        "worktree'de commit atildi ama parmak izi degismedi"
    )


def test_packed_refs_izlenir(depo):
    """`pack-refs` gevsek ref dosyasini siler; imza yine degisimi gormeli."""
    a = _ajan()

    _git(depo, "pack-refs", "--all")
    once = a._proje_ctx_imzasi(depo)

    _git(depo, "branch", "yeni")
    _git(depo, "pack-refs", "--all")
    sonra = a._proje_ctx_imzasi(depo)

    assert sonra != once, (
        "packed-refs degisti ama imza gormedi -- refler paketlenmis bir "
        "depoda tazeleme hic calismaz"
    )


# ─── 2. Goreli gitdir worktree kokune gore cozulmeli ────


def test_goreli_gitdir_kok_dizine_gore_cozulur(tmp_path, depo):
    """`gitdir: ../...` calisma dizinine gore degil, KOKE gore cozulur."""
    _git(depo, "worktree", "add", str(tmp_path / "wt2"), "-b", "dal2")

    # Isaretciyi git'in yazdigi dosyayi degistirerek degil, ayri bir kokte
    # kurariz: Windows'ta git yeni yazdigi `.git` dosyasini kisa sure
    # tutuyor ve uzerine yazmak testi yanip sonen hale getiriyordu.
    kok = tmp_path / "goreli_kok"
    kok.mkdir()
    (kok / ".git").write_text(
        "gitdir: ../depo/.git/worktrees/wt2\n", encoding="utf-8"
    )

    imza = _ajan()._proje_ctx_imzasi(kok)

    assert _head_bulundu_mu(imza), (
        f"goreli gitdir cozulmedi, HEAD bulunamadi: {imza}"
    )


# ─── 3. Yukleyicinin okudugu HER kaynak imzada olmali ───


def test_fail_log_imzaya_dahil(tmp_path):
    """`_load_project_context` T1_S2_FAIL_LOG.md okuyor; imza da izlemeli."""
    (tmp_path / "automation").mkdir()
    a = _ajan()

    once = a._proje_ctx_imzasi(tmp_path)
    (tmp_path / "automation" / "T1_S2_FAIL_LOG.md").write_text(
        "Verdict: PASS\n", encoding="utf-8"
    )
    sonra = a._proje_ctx_imzasi(tmp_path)

    assert sonra != once, (
        "yukleyici bu dosyayi okuyor ama imza izlemiyor"
    )


def test_ortam_bayragi_imzaya_dahil(tmp_path, monkeypatch):
    """Calisma modu satiri JARVIS_PROACTIVE_ENABLED'a bagli; imza da olmali."""
    a = _ajan()

    monkeypatch.delenv("JARVIS_PROACTIVE_ENABLED", raising=False)
    once = a._proje_ctx_imzasi(tmp_path)

    monkeypatch.setenv("JARVIS_PROACTIVE_ENABLED", "1")
    sonra = a._proje_ctx_imzasi(tmp_path)

    assert sonra != once, (
        "ortam bayragi baglami degistiriyor ama imza gormuyor"
    )


# ─── 4. Asiri duzeltme kontrolu ─────────────────────────


def test_hicbir_sey_degismezse_imza_ayni_kalir(depo):
    """Imza her cagride degisirse cache olur, her tur disk taranir."""
    (depo / "roadmap_state.json").write_text(
        json.dumps({"steps": []}), encoding="utf-8"
    )
    a = _ajan()

    assert a._proje_ctx_imzasi(depo) == a._proje_ctx_imzasi(depo)


def test_gitsiz_dizinde_patlamaz(tmp_path):
    """Depo olmayan bir kok istisna firlatmamali -- ses hatti durmaz."""
    assert isinstance(_ajan()._proje_ctx_imzasi(tmp_path), tuple)
