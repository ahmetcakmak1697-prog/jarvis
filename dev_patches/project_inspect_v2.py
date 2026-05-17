"""JARVIS Project Inspector v2 — Faz 1 sonrası tam durum raporu

Yenilikler (v1'e göre):
- Faz 1 özelliklerini OTOMATİK tespit eder (10 madde checklist)
- conversations.json, skills.json, briefings.json'dan veri özeti
- Çalışma logları analizi
- Hangi tool çalışıyor / hangisi devre dışı

Kullanım:
  python project_inspect.py --save   → snapshot.txt
"""
import os
import hashlib
import argparse
import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter


EXCLUDE_DIRS = {'venv', '__pycache__', '.git', 'chroma_db',
                'node_modules', '.vscode', 'logs', 'outputs',
                'uploads', '.backup'}
EXCLUDE_EXT = {'.pyc', '.db', '.log', '.zip', '.gz', '.tar',
               '.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4',
               '.wav', '.ogg', '.bin', '.exe'}
MAX_FILE_SIZE = 100_000


def should_skip(path: Path) -> bool:
    for p in path.parts:
        if p in EXCLUDE_DIRS:
            return True
    return path.suffix.lower() in EXCLUDE_EXT


def file_hash(path: Path) -> str:
    try:
        h = hashlib.md5()
        with open(path, 'rb') as f:
            h.update(f.read())
        return h.hexdigest()[:8]
    except:
        return "??"


def faz1_checklist(root: Path) -> dict:
    """Faz 1'in 10 özelliğinin durumunu kontrol et"""
    checks = {}

    # A) WebSocket Streaming
    server = root / "jarvis_server.py"
    a_ok = False
    if server.exists():
        c = server.read_text(encoding='utf-8', errors='ignore')
        a_ok = "/ws/chat" in c or "WebSocket" in c or "websocket" in c
    checks["A_WebSocket_Streaming"] = "✅" if a_ok else "❌"

    # B) Semantic Router
    sr = root / "agents/semantic_router.py"
    checks["B_Semantic_Router"] = "✅" if sr.exists() else "❌"

    # C) Cross-Check
    brain = root / "jarvis_brain.py"
    c_ok = False
    if brain.exists():
        c = brain.read_text(encoding='utf-8', errors='ignore')
        c_ok = "_cross_check" in c or "cross_check" in c.lower()
    checks["C_Cross_Check"] = "✅" if c_ok else "❌"

    # D) WakeWord
    ww = root / "tools/wake_word.py"
    checks["D_WakeWord"] = "✅" if ww.exists() else "❌"

    # E) Skill Auto-Discovery
    e_ok = False
    if brain.exists():
        c = brain.read_text(encoding='utf-8', errors='ignore')
        e_ok = "_detect_skill_pattern" in c or "_recent_patterns" in c
    checks["E_Skill_Auto_Discovery"] = "✅" if e_ok else "❌"

    # F) Memory Scoring
    ms = root / "agents/memory_scorer.py"
    f_ok = ms.exists()
    if brain.exists() and f_ok:
        c = brain.read_text(encoding='utf-8', errors='ignore')
        f_ok = "MemoryScorer" in c or "self.scorer" in c
    checks["F_Memory_Scoring"] = "✅" if f_ok else ("⚠️ dosya var ama brain'e entegre değil" if ms.exists() else "❌")

    # G) Daily Digest
    dd = root / "agents/daily_digest.py"
    checks["G_Daily_Digest"] = "✅" if dd.exists() else "❌"

    # H) Multi-LLM Orchestrator
    orch = root / "agents/orchestrator.py"
    checks["H_Multi_LLM_Orchestrator"] = "✅" if orch.exists() else "❌"

    # I) Tool Discovery
    i_ok = False
    if server.exists():
        c = server.read_text(encoding='utf-8', errors='ignore')
        i_ok = "/tools/list" in c
    checks["I_Tool_Discovery"] = "✅" if i_ok else "❌"

    # J) GitHub Auto-Update
    au = root / "agents/auto_updater.py"
    checks["J_GitHub_AutoUpdate"] = "✅" if au.exists() else "❌"

    return checks


def memory_stats(root: Path) -> dict:
    """Hafıza dosyalarından istatistik çıkar"""
    stats = {}

    # conversations.json
    cp = root / "memory/conversations.json"
    if cp.exists():
        try:
            convs = json.loads(cp.read_text(encoding='utf-8'))
            scores = [c.get("metadata", {}).get("quality_score", 0) for c in convs]
            evals = sum(1 for s in scores if s > 0)
            researched = sum(1 for c in convs
                             if c.get("metadata", {}).get("researched"))
            importance = [c.get("metadata", {}).get("importance", 0) for c in convs]
            stats["conversations"] = {
                "total":         len(convs),
                "evaluated":     evals,
                "researched":    researched,
                "avg_score":     round(sum(scores) / len(scores), 1) if scores else 0,
                "high_quality":  sum(1 for s in scores if s >= 7),
                "max_importance": max(importance) if importance else 0,
            }
            # Son 5 konuşmadan başlık
            recent = []
            for c in convs[-5:]:
                u = next((m["content"] for m in c.get("messages", [])
                          if m["role"] == "user"), "")[:60]
                if u:
                    recent.append(u)
            stats["recent_topics"] = recent
        except Exception as e:
            stats["conversations"] = {"error": str(e)[:80]}

    # skills.json
    sp = root / "memory/skills.json"
    if sp.exists():
        try:
            skills = json.loads(sp.read_text(encoding='utf-8'))
            auto_learned = [n for n, s in skills.items()
                            if "auto-learned" in s.get("tags", [])]
            stats["skills"] = {
                "total":        len(skills),
                "auto_learned": len(auto_learned),
                "names":        list(skills.keys())[:10],
            }
        except:
            pass

    # briefings.json / digests.json
    bp = root / "memory/briefings.json"
    dp = root / "memory/digests.json"
    if bp.exists():
        try:
            bs = json.loads(bp.read_text(encoding='utf-8'))
            stats["briefings_count"] = len(bs)
        except:
            pass
    if dp.exists():
        try:
            ds = json.loads(dp.read_text(encoding='utf-8'))
            stats["daily_digests"] = len(ds)
            if ds:
                stats["latest_digest_date"] = ds[-1].get("date", "?")
        except:
            pass

    # user_profile.json
    up = root / "memory/user_profile.json"
    if up.exists():
        try:
            p = json.loads(up.read_text(encoding='utf-8'))
            stats["user_profile"] = {k: v for k, v in p.items()
                                     if v and (not isinstance(v, list) or len(v) > 0)}
        except:
            pass

    # improvements.json
    ip = root / "memory/improvements.json"
    if ip.exists():
        try:
            ins = json.loads(ip.read_text(encoding='utf-8'))
            stats["improvements"] = {
                "count": len(ins),
                "latest_weakness": ins[-1].get("analysis", {}).get("ana_zayıflık", "")
                                   if ins else "",
            }
        except:
            pass

    # reminders.json
    rp = root / "memory/reminders.json"
    if rp.exists():
        try:
            rs = json.loads(rp.read_text(encoding='utf-8'))
            pending = sum(1 for r in rs if not r.get("done"))
            stats["reminders"] = {"total": len(rs), "pending": pending}
        except:
            pass

    # vector memory
    cdb = root / "memory/chroma_db"
    if cdb.exists():
        files = list(cdb.rglob("*"))
        size = sum(f.stat().st_size for f in files if f.is_file())
        stats["vector_db"] = {"size_mb": round(size / 1024 / 1024, 2)}

    return stats


def logs_summary(root: Path) -> dict:
    """logs/ klasöründen özet"""
    out = {}
    logs = root / "logs"
    if not logs.exists():
        return out

    # auto_runner.log
    arl = logs / "auto_runner.log"
    if arl.exists():
        try:
            lines = arl.read_text(encoding='utf-8', errors='ignore').splitlines()
            out["auto_runner_lines"] = len(lines)
            recent_errors = [l for l in lines[-200:] if "❌" in l or "ERROR" in l][-10:]
            out["recent_errors"] = recent_errors
            last_lines = lines[-15:]
            out["last_15"] = last_lines
        except:
            pass

    # improvement reports
    ir = logs / "improvement_reports"
    if ir.exists():
        reports = list(ir.glob("*.json"))
        out["improvement_reports"] = len(reports)

    return out


def inspect(root="."):
    root_path = Path(root).resolve()
    out = []
    out.append("="*70)
    out.append("🔍 JARVIS PROJECT SNAPSHOT v2 (Faz 1 sonrası)")
    out.append(f"📅 {datetime.now().isoformat()}")
    out.append(f"📁 {root_path}")
    out.append("="*70)

    # ✅ FAZ 1 CHECKLIST
    out.append("\n## 🎯 FAZ 1 ENTEGRASYON KONTROLÜ\n")
    checks = faz1_checklist(root_path)
    for k, v in checks.items():
        out.append(f"  {v}  {k.replace('_', ' ')}")

    ok = sum(1 for v in checks.values() if v == "✅")
    total = len(checks)
    out.append(f"\n  Sonuç: **{ok}/{total}** özellik aktif")

    # 📊 MEMORY DURUMU
    out.append("\n\n## 📊 HAFIZA & VERİ DURUMU\n")
    ms = memory_stats(root_path)
    out.append(f"```json\n{json.dumps(ms, ensure_ascii=False, indent=2)}\n```")

    # 📜 LOG ÖZETİ
    out.append("\n## 📜 LOG ÖZETİ\n")
    ls = logs_summary(root_path)
    if ls:
        out.append(f"```json\n{json.dumps(ls, ensure_ascii=False, indent=2)}\n```")
    else:
        out.append("Log yok (henüz auto_runner çalıştırılmamış)")

    # 📂 DİZİN YAPISI
    out.append("\n\n## 📂 KLASÖR YAPISI\n```")
    for p in sorted(root_path.rglob("*")):
        rel = p.relative_to(root_path)
        if should_skip(rel):
            continue
        depth = len(rel.parts) - 1
        indent = "  " * depth
        if p.is_dir():
            out.append(f"{indent}📁 {p.name}/")
        else:
            try:
                size = p.stat().st_size
                out.append(f"{indent}📄 {p.name} ({size}B, {file_hash(p)})")
            except:
                out.append(f"{indent}📄 {p.name}")
    out.append("```\n")

    # 📝 DOSYA İÇERİKLERİ
    out.append("\n## 📝 PYTHON DOSYA İÇERİKLERİ\n")
    for p in sorted(root_path.rglob("*.py")):
        rel = p.relative_to(root_path)
        if should_skip(rel):
            continue
        out.append(f"\n{'='*70}")
        out.append(f"### 📄 {rel}")
        out.append(f"### Boyut: {p.stat().st_size}B | Hash: {file_hash(p)}")
        out.append("="*70)
        try:
            c = p.read_text(encoding='utf-8', errors='ignore')
            if len(c) > MAX_FILE_SIZE:
                out.append(f"```python\n{c[:MAX_FILE_SIZE]}\n"
                           f"\n... [{len(c)-MAX_FILE_SIZE}B truncated] ...\n```")
            else:
                out.append(f"```python\n{c}\n```")
        except Exception as e:
            out.append(f"<okuma hatası: {e}>")

    # Diğer önemli dosyalar
    for pattern in ["requirements.txt", "README.md", "*.json"]:
        for p in sorted(root_path.rglob(pattern)):
            rel = p.relative_to(root_path)
            if should_skip(rel):
                continue
            if p.stat().st_size > 30_000:
                continue
            # JSON'ların hepsini değil, ana olanları al
            if p.suffix == ".json":
                allowed = ["user_profile", "skills", "improvements", "reminders"]
                if not any(a in p.name for a in allowed):
                    continue
            out.append(f"\n{'='*70}")
            out.append(f"### 📄 {rel}")
            out.append("="*70)
            try:
                c = p.read_text(encoding='utf-8', errors='ignore')
                if len(c) > 15_000:
                    c = c[:15_000] + "\n... [truncated]"
                lang = "json" if p.suffix == ".json" else "text"
                out.append(f"```{lang}\n{c}\n```")
            except:
                pass

    # ÖZET
    out.append(f"\n\n{'='*70}")
    out.append("## 📊 ÖZET")
    py_files = [p for p in root_path.rglob("*.py")
                if not should_skip(p.relative_to(root_path))]
    total_lines = 0
    for p in py_files:
        try:
            total_lines += len(p.read_text(encoding='utf-8',
                                            errors='ignore').splitlines())
        except:
            pass
    out.append(f"- Python dosyası: {len(py_files)}")
    out.append(f"- Toplam satır: {total_lines}")
    out.append(f"- Faz 1 entegrasyon: {ok}/{total}")
    out.append("="*70)

    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    report = inspect(args.root)

    if args.save:
        Path("snapshot.txt").write_text(report, encoding='utf-8')
        print(f"✅ snapshot.txt kaydedildi ({len(report)} karakter)")
        print(f"   Dosyayı Claude'a sürükle!")
    else:
        print(report)
