import argparse
import os
import sys
import random
import sqlite3
import datetime
import tempfile
import signal
import csv
from tqdm import tqdm
from faker import Faker
from collections import defaultdict
from itertools import cycle

class DataGenerationStrategy:   
    def __init__(self):
        self.__conn = None
        self.__cursor = None
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.db_filename = os.path.join(tempfile.gettempdir(), f"Chunked_Synthetic_Data_Generator_{timestamp}.db")

        self.__create_temp_persistance()
        
    def __create_temp_persistance(self):
        self.__conn = sqlite3.connect(self.db_filename)
        self.__cursor = self.__conn.cursor()
        self.__cursor.execute(self.__generate_create_statement())
     
    def generate_n_persist_data(self, num_lines):
        data = self.generate_data(num_lines)
        self.__cursor.executemany(self.__create_insert_statement(), data)
        return data
    
    def generate_data(self, num_lines):
        raise NotImplementedError

    def get_headers(self):
        raise NotImplementedError

    def get_trailer(self):
        return []

    def get_mapping_keys(self):
        return []
    
    def fetch_temp_data(self, limit=10000):
        self.__cursor.execute('SELECT MAX(ROWID) FROM data')
        max_id = self.__cursor.fetchone()[0]

        random_ids = random.sample(range(1, max_id + 1), min(limit, max_id))
        placeholders = ','.join('?' for _ in random_ids)
        query = f'SELECT * FROM data WHERE ROWID IN ({placeholders})'
        self.__cursor.execute(query, random_ids)
        return self.__cursor.fetchall()

    def cleanup(self, signum=None, frame=None):
        self.__conn.close()
        
        if os.path.exists(self.db_filename):
            os.remove(self.db_filename)
        if os.path.exists(self.db_filename + "-journal"):
            os.remove(self.db_filename + "-journal")
                
    def __generate_create_statement(self):
        columns_str = ','.join(f"{key} {value}" for key, value in self.get_headers().items())
        statement = f"CREATE TABLE data ({columns_str})"
        return statement

    def __create_insert_statement(self):
        keys = list(self.get_headers().keys())
        placeholders = ', '.join(['?'] * len(keys))
        columns = ', '.join(keys)
        statement = f"INSERT INTO data ({columns}) VALUES ({placeholders})"
        return statement

class FrescoStrategy(DataGenerationStrategy):
    def __init__(self):
        super().__init__()
        self.fake = Faker()
        

    def _generate_text(self):
        return self.fake.sentence()
    
    def _generate_integer(self, min_val, max_val):
        return random.randint(min_val, max_val)

    def _generate_text_choice(self, choices):
        return random.choice(choices)

    def _generate_probability(self):
        return round(random.uniform(0.000, 1.000), 3)

    def generate_data(self, num_lines):
        data = []
        for _ in range(num_lines):
            row = [
                self._generate_text(), # client_data
                self._generate_integer(1, 999999999),  # cr_addurn
                self._generate_integer(1, 999999999999),  # cr_indurn
                self._generate_text_choice(['M', 'A', 'P', 'J', 'N']),  # match_flag
                self._generate_integer(1, 12),  # fresco20_seg
                self._generate_integer(1, 52),  # fresco20_sseg
                self._generate_integer(1, 130),  # fresco20_mseg
                self._generate_integer(1, 7),  # affluence19
                str(self._generate_integer(1, 8)),  # lukcat_incomeband2
                str(self._generate_integer(1, 5)),  # lukcat_beds
                self._generate_text_choice(['A', 'B', 'C1', 'C2', 'D', 'E']),  # lukcat_fr_de_nrs
                self._generate_text_choice(['D', 'F', 'S', 'T']),  # lukcat_housetype4
                str(self._generate_integer(1, 5)),  # lukcat_gspend
                f"s{self._generate_integer(0, 6)}",  # lukcat_sav_val2
                f"i{self._generate_integer(0, 6)}",  # lukcat_inv_val2
                str(self._generate_integer(0, 5)),  # lukcat_morvalnow
                str(self._generate_integer(0, 5)),  # lukcat_monmorrep
                str(self._generate_integer(0, 3)),  # lukcat_morratetype
            ]
            binary_flags = [self._generate_text_choice(['Y', 'N']) for _ in range(104)]
            row.extend(binary_flags)

            probability_fields = [self._generate_probability() for _ in range(104)]
            row.extend(probability_fields)

            data.append(row)
        return data
    
    def get_headers(self):
        headers = {
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
            "lukcat_morratetype": "TEXT",
            "a_lukp_a2_income1": "TEXT",
            "a_lukp_a2_income2": "TEXT",
            "a_lukp_a2_income3": "TEXT",
            "a_lukp_a2_income4": "TEXT",
            "a_lukp_a2_income5": "TEXT",
            "a_lukp_a2_income6a": "TEXT",
            "a_lukp_a2_income6b": "TEXT",
            "a_lukp_a2_income6c": "TEXT",
            "a_lukp_nbeds1": "TEXT",
            "a_lukp_nbeds2": "TEXT",
            "a_lukp_nbeds3": "TEXT",
            "a_lukp_nbeds4": "TEXT",
            "a_lukp_nbeds5p": "TEXT",
            "a_fr_de_nrsa": "TEXT",
            "a_fr_de_nrsb": "TEXT",
            "a_fr_de_nrsc1": "TEXT",
            "a_fr_de_nrsc2": "TEXT",
            "a_fr_de_nrsd": "TEXT",
            "a_fr_de_nrse": "TEXT",
            "a_lukp_a2_house5": "TEXT",
            "a_lukp_a2_house6": "TEXT",
            "a_lukp_a2_house7": "TEXT",
            "a_lukp_a2_house8": "TEXT",
            "a_lukp_gspend1": "TEXT",
            "a_lukp_gspend2": "TEXT",
            "a_lukp_gspend3": "TEXT",
            "a_lukp_gspend4": "TEXT",
            "a_lukp_gspend5": "TEXT",
            "a_fr_cur_basic": "TEXT",
            "a_fr_cur_std": "TEXT",
            "a_fr_cur_fee": "TEXT",
            "a_fr_cur_premium": "TEXT",
            "a_fr_sav_acc": "TEXT",
            "a_fr_sav_vala": "TEXT",
            "a_fr_sav_val3": "TEXT",
            "a_fr_sav_val4": "TEXT",
            "a_fr_sav_val5": "TEXT",
            "a_fr_sav_val6": "TEXT",
            "a_fr_sav_val6d": "TEXT",
            "a_fr_sav_lumpsum": "TEXT",
            "a_fr_sav_regular": "TEXT",
            "a_lukp_invhas": "TEXT",
            "a_fr_inv_vala": "TEXT",
            "a_fr_inv_val3": "TEXT",
            "a_fr_inv_val4": "TEXT",
            "a_fr_inv_val5": "TEXT",
            "a_fr_inv_val6": "TEXT",
            "a_fr_inv_val6d": "TEXT",
            "a_lukp_havcredcd": "TEXT",
            "a_fr_mor_has": "TEXT",
            "a_lukp_mortvar": "TEXT",
            "a_fr_mor_standvar": "TEXT",
            "a_fr_mor_othervar": "TEXT",
            "a_lukp_mortfix": "TEXT",
            "a_fr_morvalnow0_50": "TEXT",
            "a_fr_morvalnow50_100": "TEXT",
            "a_fr_morvalnow100_150": "TEXT",
            "a_fr_morvalnow150_200": "TEXT",
            "a_fr_morvalnow200p": "TEXT",
            "a_fr_morpay1_250": "TEXT",
            "a_fr_morpay250_500": "TEXT",
            "a_fr_morpay500_750": "TEXT",
            "a_fr_morpay750_1000": "TEXT",
            "a_fr_morpay1000p": "TEXT",
            "a_fr_ins_cont": "TEXT",
            "a_lukp_breakdown": "TEXT",
            "a_lukp_instravel": "TEXT",
            "a_fr_ins_compmotor": "TEXT",
            "a_fr_ins_travel1y": "TEXT",
            "a_fr_ins_pet": "TEXT",
            "a_lukp_hlth": "TEXT",
            "a_lukp_phlth": "TEXT",
            "a_lukp_chlth": "TEXT",
            "a_fr_pen_has": "TEXT",
            "a_fr_finsit_savalot": "TEXT",
            "a_fr_finsit_savlittle": "TEXT",
            "a_fr_finsit_even": "TEXT",
            "a_fr_finsit_debt": "TEXT",
            "a_fr_int_cds": "TEXT",
            "a_fr_int_cur": "TEXT",
            "a_fr_int_hse": "TEXT",
            "a_fr_int_inv": "TEXT",
            "a_fr_int_lifpen": "TEXT",
            "a_fr_int_mor": "TEXT",
            "a_fr_int_mot": "TEXT",
            "a_fr_int_sav": "TEXT",
            "a_lukp_plife": "TEXT",
            "a_fr_lif_protect": "TEXT",
            "a_oc14_willpaymore": "TEXT",
            "a_oc14_worthpaymore": "TEXT",
            "a_oc14_natgoods": "TEXT",
            "a_oc14_premgoods": "TEXT",
            "a_oc14_paycash": "TEXT",
            "a_oc14_planshopping": "TEXT",
            "a_oc14_fairtrade": "TEXT",
            "a_oc14_lowestprices": "TEXT",
            "a_oc14_qual_smkt": "TEXT",
            "a_oc14_researchsrce": "TEXT",
            "a_oc14_happystdliv": "TEXT",
            "a_oc14_dislikedebt": "TEXT",
            "a_oc14_managmoney": "TEXT",
            "a_oc14_wellinsure": "TEXT",
            "a_oc14_pens_selfown": "TEXT",
            "a_oc14_utilswitch": "TEXT",
            "lukp_a2_income1": "REAL",
            "lukp_a2_income2": "REAL",
            "lukp_a2_income3": "REAL",
            "lukp_a2_income4": "REAL",
            "lukp_a2_income5": "REAL",
            "lukp_a2_income6a": "REAL",
            "lukp_a2_income6b": "REAL",
            "lukp_a2_income6c": "REAL",
            "lukp_nbeds1": "REAL",
            "lukp_nbeds2": "REAL",
            "lukp_nbeds3": "REAL",
            "lukp_nbeds4": "REAL",
            "lukp_nbeds5p": "REAL",
            "fr_de_nrsa": "REAL",
            "fr_de_nrsb": "REAL",
            "fr_de_nrsc1": "REAL",
            "fr_de_nrsc2": "REAL",
            "fr_de_nrsd": "REAL",
            "fr_de_nrse": "REAL",
            "lukp_a2_house5": "REAL",
            "lukp_a2_house6": "REAL",
            "lukp_a2_house7": "REAL",
            "lukp_a2_house8": "REAL",
            "lukp_gspend1": "REAL",
            "lukp_gspend2": "REAL",
            "lukp_gspend3": "REAL",
            "lukp_gspend4": "REAL",
            "lukp_gspend5": "REAL",
            "fr_cur_basic": "REAL",
            "fr_cur_std": "REAL",
            "fr_cur_fee": "REAL",
            "fr_cur_premium": "REAL",
            "fr_sav_acc": "REAL",
            "fr_sav_vala": "REAL",
            "fr_sav_val3": "REAL",
            "fr_sav_val4": "REAL",
            "fr_sav_val5": "REAL",
            "fr_sav_val6": "REAL",
            "fr_sav_val6d": "REAL",
            "fr_sav_lumpsum": "REAL",
            "fr_sav_regular": "REAL",
            "lukp_invhas": "REAL",
            "fr_inv_vala": "REAL",
            "fr_inv_val3": "REAL",
            "fr_inv_val4": "REAL",
            "fr_inv_val5": "REAL",
            "fr_inv_val6": "REAL",
            "fr_inv_val6d": "REAL",
            "lukp_havcredcd": "REAL",
            "fr_mor_has": "REAL",
            "lukp_mortvar": "REAL",
            "fr_mor_standvar": "REAL",
            "fr_mor_othervar": "REAL",
            "lukp_mortfix": "REAL",
            "fr_morvalnow0_50": "REAL",
            "fr_morvalnow50_100": "REAL",
            "fr_morvalnow100_150": "REAL",
            "fr_morvalnow150_200": "REAL",
            "fr_morvalnow200p": "REAL",
            "fr_morpay1_250": "REAL",
            "fr_morpay250_500": "REAL",
            "fr_morpay500_750": "REAL",
            "fr_morpay750_1000": "REAL",
            "fr_morpay1000p": "REAL",
            "fr_ins_cont": "REAL",
            "lukp_breakdown": "REAL",
            "lukp_instravel": "REAL",
            "fr_ins_compmotor": "REAL",
            "fr_ins_travel1y": "REAL",
            "fr_ins_pet": "REAL",
            "lukp_hlth": "REAL",
            "lukp_phlth": "REAL",
            "lukp_chlth": "REAL",
            "fr_pen_has": "REAL",
            "fr_finsit_savalot": "REAL",
            "fr_finsit_savlittle": "REAL",
            "fr_finsit_even": "REAL",
            "fr_finsit_debt": "REAL",
            "fr_int_cds": "REAL",
            "fr_int_cur": "REAL",
            "fr_int_hse": "REAL",
            "fr_int_inv": "REAL",
            "fr_int_lifpen": "REAL",
            "fr_int_mor": "REAL",
            "fr_int_mot": "REAL",
            "fr_int_sav": "REAL",
            "lukp_plife": "REAL",
            "fr_lif_protect": "REAL",
            "oc14_willpaymore": "REAL",
            "oc14_worthpaymore": "REAL",
            "oc14_natgoods": "REAL",
            "oc14_premgoods": "REAL",
            "oc14_paycash": "REAL",
            "oc14_planshopping": "REAL",
            "oc14_fairtrade": "REAL",
            "oc14_lowestprices": "REAL",
            "oc14_qual_smkt": "REAL",
            "oc14_researchsrce": "REAL",
            "oc14_happystdliv": "REAL",
            "oc14_dislikedebt": "REAL",
            "oc14_managmoney": "REAL",
            "oc14_wellinsure": "REAL",
            "oc14_pens_selfown": "REAL",
            "oc14_utilswitch": "REAL"
        }
        return headers
    
    def get_trailer(self):
        return list(self.get_headers().keys())

    def get_mapping_keys(self):
        return ["cr_addurn", "cr_indurn"]

class MetersStrategy(DataGenerationStrategy):
    def __init__(self):
        super().__init__()
        self.fake =Faker()
        
    def _generate_outcode(self):
        return f"AB{random.randint(10, 99)}"

    def _generate_postcode(self):
        return f"AB{random.randint(10, 99)} 1{self.fake.random_uppercase_letter()}{self.fake.random_uppercase_letter()}"

    def _generate_num_meters(self):
        return random.randint(1, 100)

    def _generate_total_cons_kwh(self):
        return round(random.uniform(10000, 999999), 6)

    def _generate_mean_cons_kwh(self, total, meters):
        return round(total / meters, 7)

    def _generate_median_cons_kwh(self):
        return round(random.uniform(1000, 9999) + random.uniform(0, 0.99), 2)

    def generate_data(self, num_lines):
        data = []
        for _ in range(num_lines):
            outcode = self._generate_outcode()
            postcode = self._generate_postcode()
            num_meters = self._generate_num_meters()
            total_cons_kwh = self._generate_total_cons_kwh()
            mean_cons_kwh = self._generate_mean_cons_kwh(total_cons_kwh, num_meters)
            median_cons_kwh = self._generate_median_cons_kwh()
            data.append([outcode, postcode, num_meters, total_cons_kwh, mean_cons_kwh, median_cons_kwh])
        return data

    def get_headers(self):
        return {
            "Outcode": "TEXT",
            "Postcode": "TEXT",
            "Num_meters": "INTEGER",
            "Total_cons_kwh": "REAL",
            "Mean_cons_kwh": "REAL",
            "Median_cons_kwh": "REAL"
        }

    def get_trailer(self):
        return list(self.get_headers().keys())

    def get_mapping_keys(self):
        return ["Outcode", "Postcode"]


def write_chunk_to_csv(filename, data, mode='a', headers=None):
    with open(filename, mode=mode, newline='') as file:
        writer = csv.writer(file)
        if headers and mode == 'w':
            writer.writerow(headers)
        writer.writerows(data)
        file.flush()


def get_matching_indexes(source_list=[], match_list=[]):
    return [i for i, val in enumerate(source_list) if val in match_list]

def generate_data_to_size(strategy, filename, target_size_mb=None, total_lines=None, chunk_size=10000,
                          headers=None, trailer=None, num_files=1, overlap_ratio=0):
    total_generated = 0
    pbar = tqdm(desc="Generating data", unit="rows")

    all_generated_rows = []

    while True:
        if total_lines and total_generated >= total_lines:
            break

        lines_to_generate = min(chunk_size, total_lines - total_generated) if total_lines else chunk_size
        strategy.generate_n_persist_data(lines_to_generate)
        new_rows = strategy.fetch_temp_data(chunk_size) 
        all_generated_rows.extend(new_rows)
        total_generated += lines_to_generate
        
        if os.path.exists(filename):
            current_size_mb = os.path.getsize(filename) / (1024 * 1024)
        else:
            current_size_mb = 0

        pbar.set_postfix({"File Size (MiB)": f"{current_size_mb:.3f}"})
        pbar.update(lines_to_generate)

        if target_size_mb and current_size_mb >= target_size_mb:
            break

    pbar.close()

    headers_dict = strategy.get_headers()
    headers_list = list(headers_dict.keys())
    mapping_keys = strategy.get_mapping_keys()
    key_indices = [headers_list.index(k) for k in mapping_keys]
    grouped_data = defaultdict(list)

    for row in all_generated_rows:
        key = tuple(row[i] for i in key_indices)
        grouped_data[key].append(row)

    unique_keys = list(grouped_data.keys())
    num_overlap_keys = int(len(unique_keys) * overlap_ratio)
    overlap_keys = set(random.sample(unique_keys, num_overlap_keys))

    file_data = defaultdict(list)
    file_cycle = cycle(range(num_files))

    for key in unique_keys:
        assigned_file = next(file_cycle)
        for file_id in range(num_files):
            if file_id == assigned_file or key in overlap_keys:
                file_data[file_id].extend(grouped_data[key])

    for file_id in range(num_files):
        file_name = f"{filename.split('.')[0]}_{file_id+1}.csv"
        if headers is None or headers == False:
            write_chunk_to_csv(file_name, file_data[file_id], mode='w')
        else:
            write_chunk_to_csv(file_name, file_data[file_id], mode='w', headers=headers_list)
            
        if trailer:
            write_chunk_to_csv(file_name, [trailer], mode='a')

    strategy.cleanup()


def parse_arguments(strategies):
    parser = argparse.ArgumentParser(
        description="Chunked Synthetic Data Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--lines', type=int, help="Total number of lines to generate")
    parser.add_argument('--size', type=int, help="Target file size in MB")
    parser.add_argument('--filename', type=str, required=True, help="Output CSV file name")
    parser.add_argument('--strategy', type=str, required=True, choices=list(strategies.keys()), help="Data generation strategy")
    parser.add_argument('--headers', action='store_true', help="Include headers in the CSV file")
    parser.add_argument('--trailer', action='store_true', help="Include trailer in the CSV file")
    parser.add_argument('--chunk_size', type=int, default=10000, help="Number of rows per chunk")
    parser.add_argument('--num_files', type=int, default=1, help="Number of output files")
    parser.add_argument('--overlap_ratio', type=float, default=0.0, help="Ratio of overlapping data across files based on the mapping key")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if args.lines is None and args.size is None:
        parser.error("At least one of --lines or --size must be specified.")

    return args


def main():
    
    strategies = {
        'IPNI_METER': lambda: MetersStrategy(),
        'FRESCO': lambda: FrescoStrategy()
    }

    args = parse_arguments(strategies)
    
    strategy_factory = strategies.get(args.strategy)
    strategy = strategy_factory() if strategy_factory else None
    signal.signal(signal.SIGINT, strategy.cleanup)
    signal.signal(signal.SIGTERM, strategy.cleanup) 
     
    headers = strategy.get_headers() if args.headers else None
    trailer = strategy.get_trailer() if args.trailer else None
    generate_data_to_size(
        strategy=strategy,
        filename=args.filename,
        target_size_mb=args.size,
        total_lines=args.lines,
        chunk_size=args.chunk_size if args.chunk_size < 50000 else 10000,
        headers=headers,
        trailer=trailer,
        num_files=args.num_files,
        overlap_ratio=args.overlap_ratio
    )

if __name__ == "__main__":
    main()

# python generate_data.py --lines 100 --filename output.csv --strategy IPNI_METER --headers --trailer --num_files 2 --overlap_ratio 0.5
# with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
#         futures = [executor.submit(generate_chunk, i) for i in range(num_chunks)]
#         for future in concurrent.futures.as_completed(futures):
#             data.extend(future.result())

# TODO
# 1. Fix duplicate record issue
# 2. Parallelism for performance
# 3. Use the DB as a store and then finally export as CSV
# 4. Use numpy and pandas instead of csv
# 5. workaround windows file not visible issue resulting in an infinite run when --size is selected