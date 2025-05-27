import argparse
import os
import csv
import random
import sys
from collections import defaultdict
from tqdm import tqdm
from faker import Faker

# pip install pandas pyarrow

class NormalizedDataStrategy:
    def get_table_names(self) -> list[str]:
        raise NotImplementedError

    def get_table_schema(self, table_name: str) -> dict:
        raise NotImplementedError

    def get_relationship_schema(self) -> dict:
        raise NotImplementedError

    def generate_table_data(self, table_name: str, count: int, fk_values: dict = None) -> list[dict]:
        raise NotImplementedError

class EnergyMetersStrategy(NormalizedDataStrategy):
    def __init__(self):
        self.fake = Faker()
        self.location_pool = []  # shared outcode/postcode values

    def get_table_names(self):
        return ["electricity_meters", "gas_meters"]

    def get_table_schema(self, table_name):
        return self.get_relationship_schema()["tables"][table_name]["columns"]

    def get_relationship_schema(self):
        schema = {
            "Outcode": {"type": "TEXT"},
            "Postcode": {"type": "TEXT"},
            "Num_meters": {"type": "INTEGER"},
            "Total_cons_kwh": {"type": "REAL"},
            "Mean_cons_kwh": {"type": "REAL"},
            "Median_cons_kwh": {"type": "REAL"}
        }
        return {
            "tables": {
                "electricity_meters": {"columns": schema},
                "gas_meters": {"columns": schema}
            }
        }

    def generate_table_data(self, table_name, count, fk_values=None):
        rows = []

        # Generate the shared location pool if not already populated
        if not self.location_pool:
            self._generate_location_pool(count)

        # Cycle through location pool to assign same postcode/outcode per row
        for i in range(count):
            outcode, postcode = self.location_pool[i % len(self.location_pool)]
            num_meters = self._generate_num_meters()
            total = self._generate_total_cons_kwh()
            mean = self._generate_mean_cons_kwh(total, num_meters)
            median = self._generate_median_cons_kwh()
            rows.append({
                "Outcode": outcode,
                "Postcode": postcode,
                "Num_meters": num_meters,
                "Total_cons_kwh": total,
                "Mean_cons_kwh": mean,
                "Median_cons_kwh": median
            })
        return rows

    def _generate_location_pool(self, count):
        self.location_pool = []
        for _ in range(count):
            outcode = self._generate_outcode()
            postcode = self._generate_postcode(outcode)
            self.location_pool.append((outcode, postcode))

    def _generate_outcode(self):
        return f"AB{random.randint(10, 99)}"

    def _generate_postcode(self, outcode):
        return f"{outcode} {random.randint(1, 9)}{self.fake.random_uppercase_letter()}{self.fake.random_uppercase_letter()}"

    def _generate_num_meters(self):
        return random.randint(1, 10)

    def _generate_total_cons_kwh(self):
        return round(random.uniform(500.0, 10000.0), 2)

    def _generate_mean_cons_kwh(self, total, num):
        return round(total / num, 2)

    def _generate_median_cons_kwh(self):
        return round(random.uniform(250.0, 3000.0), 2)


class FrescoStrategy(NormalizedDataStrategy):
    def __init__(self):
        self.fake = Faker()

    def get_table_names(self):
        return ["Fresco"]

    def get_table_schema(self, table_name):
        return self.get_relationship_schema()["tables"][table_name]["columns"]

    def get_relationship_schema(self):
        return {
            "tables": {
                "Fresco": {
                    "columns": self._get_columns()
                }
            }
        }

    def _get_columns(self):
        columns = {
            "client_data": "TEXT",
            "cr_addurn": "INTEGER",
            "cr_indurn": "INTEGER",
            "match_flag": "TEXT",
            "fresco20_seg": "INTEGER",
            "fresco20_sseg": "INTEGER",
            "fresco20_mseg": "INTEGER",
            "affluence19": "INTEGER",
            "lukcat_incomeband2": "TEXT",
            "lukcat_beds": "TEXT",
            "lukcat_fr_de_nrs": "TEXT",
            "lukcat_housetype4": "TEXT",
            "lukcat_gspend": "TEXT",
            "lukcat_sav_val2": "TEXT",
            "lukcat_inv_val2": "TEXT",
            "lukcat_morvalnow": "TEXT",
            "lukcat_monmorrep": "TEXT",
            "lukcat_morratetype": "TEXT"
        }

        # Additional TEXT and REAL columns based on provided schema
        for suffix in [
            "a_lukp_a2_income", "a_lukp_nbeds", "a_fr_de_nrs", "a_lukp_a2_house",
            "a_lukp_gspend", "a_fr_cur", "a_fr_sav_val", "a_fr_sav_val6d",
            "a_fr_sav_lumpsum", "a_fr_sav_regular", "a_lukp_invhas", "a_fr_inv_val",
            "a_fr_inv_val6d", "a_lukp_havcredcd", "a_fr_mor_has", "a_lukp_mortvar",
            "a_fr_mor_standvar", "a_fr_mor_othervar", "a_lukp_mortfix", "a_fr_morvalnow",
            "a_fr_morpay", "a_fr_ins", "a_lukp_breakdown", "a_lukp_instravel",
            "a_lukp_hlth", "a_lukp_phlth", "a_lukp_chlth", "a_fr_pen_has",
            "a_fr_finsit", "a_fr_int", "a_lukp_plife", "a_fr_lif_protect",
            "a_oc14_", "lukp_a2_income", "lukp_nbeds", "fr_de_nrs", "lukp_a2_house",
            "lukp_gspend", "fr_cur", "fr_sav", "lukp_invhas", "fr_inv",
            "lukp_havcredcd", "fr_mor", "lukp_mort", "fr_ins", "lukp_", "oc14_"
        ]:
            for i in range(1, 7):
                col = f"{suffix}{i}"
                if col not in columns:
                    columns[col] = "TEXT"

        # Manually adding a few remaining known columns
        extra = [
            "a_fr_inv_val6d", "a_fr_morvalnow0_50", "a_fr_morvalnow50_100",
            "a_fr_morvalnow100_150", "a_fr_morvalnow150_200", "a_fr_morvalnow200p",
            "a_fr_morpay1_250", "a_fr_morpay250_500", "a_fr_morpay500_750",
            "a_fr_morpay750_1000", "a_fr_morpay1000p", "fr_morvalnow0_50",
            "fr_morvalnow200p", "fr_morpay1000p", "fr_ins_travel1y", "fr_ins_pet",
            "fr_pen_has", "fr_inv_val6d", "fr_lif_protect", "oc14_willpaymore",
            "oc14_utilswitch"
        ]
        for col in extra:
            columns[col] = "TEXT"

        return columns

    def generate_table_data(self, table_name, count, fk_values=None):
        schema = self._get_columns()
        rows = []

        for _ in range(count):
            row = {}

            row["client_data"] = self.fake.sentence()
            row["cr_addurn"] = random.randint(1, 999999999)
            row["cr_indurn"] = random.randint(1, 999999999999)
            row["match_flag"] = random.choice(['M', 'A', 'P', 'J', 'N'])
            row["fresco20_seg"] = random.randint(1, 12)
            row["fresco20_sseg"] = random.randint(1, 52)
            row["fresco20_mseg"] = random.randint(1, 130)
            row["affluence19"] = random.randint(1, 7)
            row["lukcat_incomeband2"] = str(random.randint(1, 8))
            row["lukcat_beds"] = str(random.randint(1, 5))
            row["lukcat_fr_de_nrs"] = random.choice(['A', 'B', 'C1', 'C2', 'D', 'E'])
            row["lukcat_housetype4"] = random.choice(['D', 'F', 'S', 'T'])
            row["lukcat_gspend"] = str(random.randint(1, 5))
            row["lukcat_sav_val2"] = f"s{random.randint(0, 6)}"
            row["lukcat_inv_val2"] = f"i{random.randint(0, 6)}"
            row["lukcat_morvalnow"] = str(random.randint(0, 5))
            row["lukcat_monmorrep"] = str(random.randint(0, 5))
            row["lukcat_morratetype"] = str(random.randint(0, 3))

            for col, dtype in schema.items():
                if col in row:
                    continue
                if dtype == "REAL":
                    row[col] = round(random.uniform(0.000, 1.000), 3)
                else:
                    row[col] = random.choice(["Y", "N"])

            rows.append(row)

        return rows



class DataOrchestrator:
    def __init__(self, strategy, output_dir="output", show_progress=False, output_format="csv"):
        self.strategy = strategy
        self.output_dir = output_dir
        self.show_progress = show_progress
        self.output_format = output_format
        self.relationships = strategy.get_relationship_schema()
        self.schemas = {t: d["columns"] for t, d in self.relationships["tables"].items()}
        self.generated_data = defaultdict(int)
        self.parquet_index = defaultdict(int)  # for unique filenames

    def _write_rows(self, table_name, rows, mode='a'):
        os.makedirs(self.output_dir, exist_ok=True)

        if self.output_format == "csv":
            file_path = os.path.join(self.output_dir, f"{table_name}.csv")
            with open(file_path, mode=mode, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.schemas[table_name].keys())
                if mode == 'w':
                    writer.writeheader()
                writer.writerows(rows)
                f.flush()

        elif self.output_format == "parquet":
            import pandas as pd
            table_dir = os.path.join(self.output_dir, table_name)
            os.makedirs(table_dir, exist_ok=True)
            self.parquet_index[table_name] += 1
            file_name = f"{table_name}_{self.parquet_index[table_name]:04d}.parquet"
            file_path = os.path.join(table_dir, file_name)
            df = pd.DataFrame(rows)
            df.to_parquet(file_path, index=False, compression='snappy')

    def _extract_fk_specs(self, column_info):
        return {
            col: info["foreign_key"]
            for col, info in column_info.items()
            if "foreign_key" in info
        }

    def _resolve_order(self, tables, fk_deps):
        ordered, visited = [], set()
        def visit(t):
            if t in visited:
                return
            for dep in fk_deps.get(t, []):
                visit(dep)
            visited.add(t)
            ordered.append(t)
        for t in tables:
            visit(t)
        return ordered

    def _get_output_dir_size_mb(self):
        total = 0
        for dirpath, _, filenames in os.walk(self.output_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
        return total / (1024 * 1024)

    def run_generation(self, base_counts: dict[str, int], target_size_mb=None):
        fk_deps = {}
        for table, cols in self.schemas.items():
            for col, info in cols.items():
                if "foreign_key" in info:
                    parent = info["foreign_key"]["ref_table"]
                    fk_deps.setdefault(table, []).append(parent)

        ordered_tables = self._resolve_order(list(self.schemas.keys()), fk_deps)
        generated_keys = {}

        for table in ordered_tables:
            cols = self.schemas[table]
            fk_specs = self._extract_fk_specs(cols)
            target_count = base_counts.get(table, 100)
            count = 0
            batch_size = 1000

            if not fk_specs:
                while True:
                    if base_counts and count >= target_count:
                        break
                    if target_size_mb and self._get_output_dir_size_mb() >= target_size_mb:
                        break
                    rows = self.strategy.generate_table_data(table, batch_size)
                    self._write_rows(table, rows, mode='a' if count else 'w')
                    generated_keys[table] = [row[k] for row in rows for k, v in cols.items() if "primary_key" in v]
                    count += len(rows)
            else:
                parent_table = list(fk_specs.values())[0]["ref_table"]
                fk_col = list(fk_specs.keys())[0]
                fk_values = generated_keys.get(parent_table, [])

                if not fk_values:
                    raise RuntimeError(f"No foreign keys found from parent table: {parent_table}")

                iterator = tqdm(fk_values, disable=not self.show_progress, desc=f"{table}")
                for fk_val in iterator:
                    if base_counts and count >= target_count:
                        break
                    if target_size_mb and self._get_output_dir_size_mb() >= target_size_mb:
                        break
                    rows = self.strategy.generate_table_data(table, 1, fk_values={fk_col: fk_val})
                    self._write_rows(table, rows, mode='a' if count else 'w')
                    count += 1

        print("\n✅ Generation complete:")
        for table in ordered_tables:
            print(f"  - {table}: {count} rows written")

def parse_arguments(strategies):
    parser = argparse.ArgumentParser(description="Normalized Synthetic Data Generator")
    parser.add_argument('--strategy', required=True, choices=strategies.keys(), help="Strategy name")
    parser.add_argument('--lines', type=str, help="Row counts: Table1=100,Table2=500")
    parser.add_argument('--size', type=str, help="Target output size: 10MB or 1GB")
    parser.add_argument('--output_dir', default="output", help="Output directory")
    parser.add_argument('--format', choices=["csv", "parquet"], default="csv", help="Output format")
    parser.add_argument('--show_progress', action='store_true', help="Show progress bars")
    args = parser.parse_args()

    row_counts = {}
    if args.lines:
        try:
            row_counts = {kv.split("=")[0]: int(kv.split("=")[1]) for kv in args.lines.split(",")}
        except:
            parser.error("Invalid format for --lines. Use: Table1=100,Table2=200")

    size_limit_mb = None
    if args.size:
        size_str = args.size.upper().strip()
        if size_str.endswith("GB"):
            size_limit_mb = float(size_str[:-2]) * 1024
        elif size_str.endswith("MB"):
            size_limit_mb = float(size_str[:-2])
        else:
            parser.error("Size must end with MB or GB (e.g., 10MB, 1GB)")

    if not row_counts and not size_limit_mb:
        parser.error("Must specify either --lines or --size")

    return args, row_counts, size_limit_mb


def main():
    strategies = {
        "fresco": lambda: FrescoStrategy()
    }


    args, row_counts, size_limit_mb = parse_arguments(strategies)

    strategy = strategies[args.strategy]()
    orchestrator = DataOrchestrator(
        strategy=strategy,
        output_dir=args.output_dir,
        show_progress=args.show_progress,
        output_format=args.format
    )
    orchestrator.run_generation(row_counts, target_size_mb=size_limit_mb)


if __name__ == "__main__":
    main()

#python data_generator.py --strategy meters --size 10GB --format parquet --output_dir ./out --show_progress
#python data_generator.py --strategy meters --lines Locations=10000,Meters=50000 --format csv --output_dir ./out
