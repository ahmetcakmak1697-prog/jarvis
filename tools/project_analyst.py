import os

class ProjectAnalyst:
    def __init__(self, project_root="Jarvis/"):
        self.project_root = project_root

    def list_project_structure(self):
        """Tüm proje klasör yapısını ağaç şeklinde çıkarır."""
        structure = "--- PROJE KLASÖR YAPISI ---\n"
        for root, dirs, files in os.walk(self.project_root):
            # Gereksiz klasörleri gizleyelim (cache, venv vb.)
            if "pycache" in root or "vector_db" in root:
                continue
            level = root.replace(self.project_root, '').count(os.sep)
            indent = ' ' * 4 * level
            structure += f"{indent}[{os.path.basename(root)}/]\n"
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                structure += f"{sub_indent}- {f}\n"
        return structure

    def read_source_code(self, file_name):
        """İstediği kendi kaynak kodunu okur."""
        # Güvenlik ve yol kontrolü
        for root, dirs, files in os.walk(self.project_root):
            if file_name in files:
                full_path = os.path.join(root, file_name)
                with open(full_path, "r", encoding="utf-8") as f:
                    return f"--- {file_name} KAYNAK KODU ---\n{f.read()}"
        return f"Hata: {file_name} adlı dosya proje içinde bulunamadı."