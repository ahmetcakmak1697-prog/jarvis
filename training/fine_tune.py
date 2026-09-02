"""
JARVIS Fine-Tuning Pipeline v2
Gerçek eğitim — Unsloth + LoRA + RTX 3070
Gece 02:00'da otomatik çalışır
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


CONV_FILE = Path("memory/conversations.json")
LOG_FILE  = Path("logs/fine_tune_log.txt")
DATA_FILE = Path("training/train_data.jsonl")
MIN_QUALITY = 6
MIN_SAMPLES = 10


# ─────────────────────────────────────────────
# 1) VERİ HAZIRLA
# ─────────────────────────────────────────────

def prepare_data() -> list:
    if not CONV_FILE.exists():
        print("❌ conversations.json yok — önce JARVIS ile konuş!")
        return []

    with open(CONV_FILE, 'r', encoding='utf-8') as f:
        convs = json.load(f)

    good = [c for c in convs
            if c.get('metadata', {}).get('quality_score', 5) >= MIN_QUALITY]

    print(f"📊 Toplam: {len(convs)} | Kaliteli (>={MIN_QUALITY}): {len(good)}")
    return good


def export_jsonl(data: list):
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        for item in data:
            msgs = item['messages']
            user = next((m['content'] for m in msgs if m['role'] == 'user'), '')
            asst = next((m['content'] for m in msgs if m['role'] == 'assistant'), '')
            if user and asst:
                row = {
                    "text": (
                        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                        f"Sen JARVIS'sin. Tony Stark'in Türkçe konuşan AI asistanısın."
                        f"<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
                        f"{user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
                        f"{asst}<|eot_id|>"
                    )
                }
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f"✅ {len(data)} satır → {DATA_FILE}")


# ─────────────────────────────────────────────
# 2) UNSLOTH KURULUM KONTROLÜ
# ─────────────────────────────────────────────

def check_and_install():
    pkgs = ["unsloth", "torch", "transformers", "datasets", "trl"]
    missing = []
    for pkg in pkgs:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"📦 Kuruluyor: {missing}")
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "unsloth[colab-new]", "trl", "datasets",
            "-q", "--break-system-packages"
        ], check=False)


# ─────────────────────────────────────────────
# 3) GERÇEK EĞİTİM
# ─────────────────────────────────────────────

def train(data: list):
    try:
        from unsloth import FastLanguageModel
        from datasets import Dataset
        from trl import SFTTrainer
        from transformers import TrainingArguments
    except ImportError as e:
        print(f"❌ Kütüphane eksik: {e}")
        print("   Çalıştır: pip install unsloth[colab-new] trl datasets")
        return False

    print("\n🔧 Model yükleniyor (RTX 3070 — 4bit)...")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/llama-3.1-8b-instruct-bnb-4bit",
        max_seq_length=2048,
        dtype=None,           # Otomatik — RTX 3070 için float16
        load_in_4bit=True,    # VRAM tasarrufu
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # Veriyi yükle
    rows = [json.loads(l) for l in open(DATA_FILE, encoding='utf-8')]
    dataset = Dataset.from_list(rows)

    output_dir = f"training/jarvis-lora-{datetime.now().strftime('%Y%m%d')}"

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        args=TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=3,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            learning_rate=2e-4,
            fp16=True,
            logging_steps=10,
            save_strategy="epoch",
            report_to="none",
        ),
    )

    print("🚀 Eğitim başlıyor...\n")
    trainer.train()

    # Ollama için GGUF kaydet
    gguf_path = f"{output_dir}/jarvis-finetuned.gguf"
    model.save_pretrained_gguf(gguf_path, tokenizer, quantization_method="q4_k_m")
    print(f"\n✅ Model kaydedildi: {gguf_path}")

    # Modelfile oluştur (Ollama için)
    modelfile = Path(f"{output_dir}/Modelfile")
    modelfile.write_text(
        f'FROM {gguf_path}\n'
        f'SYSTEM "Sen JARVIS\'sin. Tony Stark\'ın Türkçe AI asistanısın."\n'
        f'PARAMETER temperature 0.5\n'
        f'PARAMETER num_ctx 4096\n'
    )
    print(f"📄 Modelfile: {modelfile}")
    print(f"\n▶️  Ollama\'ya yükle:")
    print(f"   ollama create jarvis-ft -f {modelfile}")
    print(f"   Sonra jarvis_brain.py → MODEL = 'jarvis-ft'")

    _log(len(data), output_dir)
    return True


# ─────────────────────────────────────────────
# 4) LOG
# ─────────────────────────────────────────────

def _log(sample_count, output_dir):
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(
            f"\n{'='*50}\n"
            f"{datetime.now().isoformat()}\n"
            f"Konuşma: {sample_count}\n"
            f"Çıktı: {output_dir}\n"
        )


# ─────────────────────────────────────────────
# 5) SCHEDULER (Gece Öğrenimi)
# ─────────────────────────────────────────────

def schedule_nightly():
    """Her gece 02:00'da fine-tuning çalıştır"""
    import schedule
    import time

    def job():
        print(f"\n⏰ Gece eğitimi başlıyor — {datetime.now()}")
        fine_tune()

    schedule.every().day.at("02:00").do(job)
    print("✅ Gece öğrenimi aktif — her gece 02:00'da çalışacak")
    print("   Durdurmak için Ctrl+C\n")

    while True:
        schedule.run_pending()
        time.sleep(60)


# ─────────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────────

def fine_tune():
    print("\n" + "="*60)
    print("🧠 JARVIS FINE-TUNING PIPELINE v2")
    print("="*60 + "\n")

    data = prepare_data()

    if len(data) < MIN_SAMPLES:
        print(f"\n⚠️  Yeterli veri yok: {len(data)}/{MIN_SAMPLES}")
        print("   JARVIS ile daha fazla konuş, veri biriksin.")
        print(f"   Şu an kaç konuşma var: {len(data)}")
        return

    export_jsonl(data)
    check_and_install()
    train(data)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--now",      action="store_true", help="Hemen eğit")
    parser.add_argument("--schedule", action="store_true", help="Gece 02:00 scheduler")
    parser.add_argument("--status",   action="store_true", help="Veri durumunu göster")
    args = parser.parse_args()

    if args.status:
        data = prepare_data()
        print(f"\n📊 Fine-tuning durumu:")
        print(f"   Toplam konuşma : {len(data)}")
        print(f"   Eğitime hazır  : {'✅ Evet' if len(data) >= MIN_SAMPLES else f'❌ Hayır ({MIN_SAMPLES - len(data)} daha gerekli)'}")
    elif args.schedule:
        schedule_nightly()
    else:
        fine_tune()   # --now veya argümansız = hemen çalıştır
