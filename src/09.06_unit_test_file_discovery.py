import os
import hashlib
import tempfile
import unittest
import pandas as pd

SUPPORTED_EXTENSIONS = {".csv"}
REQUIRED_MIN_COLUMNS = 2

def compute_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def discover_and_route_files(folder_path):
    routes = {
        "valid": [],
        "unsupported": [],
        "missing_or_empty": [],
        "duplicate": [],
        "malformed": []
    }

    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        routes["missing_or_empty"].append(folder_path)
        return routes

    seen_hashes = set()

    for filename in sorted(os.listdir(folder_path)):
        filepath = os.path.join(folder_path, filename)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()

        # 1. Unsupported extension check
        if ext not in SUPPORTED_EXTENSIONS:
            routes["unsupported"].append(filename)
            continue

        # 2. Missing / zero-byte empty file check
        if os.path.getsize(filepath) == 0:
            routes["missing_or_empty"].append(filename)
            continue

        # 3. Duplicate file content check via SHA-256
        file_hash = compute_file_hash(filepath)
        if file_hash in seen_hashes:
            routes["duplicate"].append(filename)
            continue
        seen_hashes.add(file_hash)

        # 4. Malformed CSV structure check
        try:
            df = pd.read_csv(filepath)
            if len(df.columns) < REQUIRED_MIN_COLUMNS or df.empty:
                routes["malformed"].append(filename)
                continue
        except Exception:
            routes["malformed"].append(filename)
            continue

        # 5. Valid file routed for ingestion
        routes["valid"].append(filename)

    return routes


class TestFileDiscoveryRouting(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.base_path = self.test_dir.name

        # 1. Valid CSV file
        self.valid_file = os.path.join(self.base_path, "sales_2026-01.csv")
        with open(self.valid_file, "w", encoding="utf-8") as f:
            f.write("transaction_id,store_id,quantity,unit_selling_price\nTXN001,STR01,2,499.00\n")

        # 2. Unsupported file (.txt)
        self.unsupported_file = os.path.join(self.base_path, "readme_notes.txt")
        with open(self.unsupported_file, "w", encoding="utf-8") as f:
            f.write("Unsupported text file")

        # 3. Empty / 0-byte file
        self.empty_file = os.path.join(self.base_path, "sales_empty.csv")
        open(self.empty_file, "w", encoding="utf-8").close()

        # 4. Duplicate CSV file (exact duplicate content of valid_file)
        self.dup_file = os.path.join(self.base_path, "sales_2026-01_copy.csv")
        with open(self.dup_file, "w", encoding="utf-8") as f:
            f.write("transaction_id,store_id,quantity,unit_selling_price\nTXN001,STR01,2,499.00\n")

        # 5. Malformed CSV file (unclosed quote / broken structure)
        self.malformed_file = os.path.join(self.base_path, "sales_corrupt.csv")
        with open(self.malformed_file, "w", encoding="utf-8") as f:
            f.write('transaction_id,store_id\n"UNCLOSED_QUOTE_ROW,STR01\nBAD\x00BINARY')

    def tearDown(self):
        self.test_dir.cleanup()

    def test_valid_file_routing(self):
        routes = discover_and_route_files(self.base_path)
        self.assertEqual(routes["valid"], ["sales_2026-01.csv"])

    def test_unsupported_file_routing(self):
        routes = discover_and_route_files(self.base_path)
        self.assertEqual(routes["unsupported"], ["readme_notes.txt"])

    def test_missing_or_empty_file_routing(self):
        routes = discover_and_route_files(self.base_path)
        self.assertEqual(routes["missing_or_empty"], ["sales_empty.csv"])
        missing_routes = discover_and_route_files(os.path.join(self.base_path, "non_existent_folder"))
        self.assertEqual(len(missing_routes["missing_or_empty"]), 1)

    def test_duplicate_file_routing(self):
        routes = discover_and_route_files(self.base_path)
        self.assertEqual(routes["duplicate"], ["sales_2026-01_copy.csv"])

    def test_malformed_file_routing(self):
        routes = discover_and_route_files(self.base_path)
        self.assertEqual(routes["malformed"], ["sales_corrupt.csv"])


if __name__ == "__main__":
    print("=" * 75)
    print("STEP 09.06: UNIT-TEST FILE DISCOVERY & INPUT ROUTING")
    print("=" * 75)
    unittest.main(verbosity=2)
