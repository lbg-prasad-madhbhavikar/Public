from enum import Enum
import os
import requests
import orjson as json
import base64
import time
from tqdm import tqdm
import pathlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import json

def extract_href(data):
    if data:
        match = re.search(r'href="(.*?)"', data)
        return match.group(1).strip() if match else data.strip()
    return data.strip()

def extract_last_value(data, separator=">"):
    if data:
        parts = data.split(separator)
        return parts[-1].strip() if parts else data.strip()
    return data.strip()

def iso_timestamp(epoch):
    if epoch:
        result = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(epoch/1000))
    else:
        result = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    return result

def toJson(obj, *, indent=None):
    result = json.dumps(obj, indent=indent, default=str)
    return result
# user_name = os.getenv('COLLIBRA_USERNAME')
# user_password = os.getenv('COLLIBRA_PASSWORD')

user_name = "LcapAvatarServices"
user_password = "eKsEnSus2j2S"

collibra_config = {
    "url": "https://lloyds.collibra.com",
    "paths": {
        "assets": "rest/2.0/assets/{asset_id}",
        "attributes": "rest/2.0/attributes?assetId={asset_id}",
        "asset_types": "rest/2.0/attributeTypes?assetTypeId={asset_type_id}",
        "roles": "rest/2.0/roles",
        "relations_from_source": "rest/2.0/relations?sourceId={asset_id}",
        "relations_from_target": "rest/2.0/relations?targetId={asset_id}",
        "relation_types": "rest/2.0/relationTypes/{relation_type_id}",
        "domains": "rest/2.0/domains/{domain_id}"
    },
}

asset_types_meta = {}
asset_types = {}
collibra_targetted_roles = [
    "Data Product Owner",
    "Data Steward",
    "Ownership Delegated Authority",
]
collibra_roles = {}


def get_authorization():
    credentials = f"{user_name}:{user_password}"
    return "Basic " + base64.b64encode(credentials.encode()).decode()


def get_headers():
    return {
        "Authorization": get_authorization(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def collibra_fetcher(
    url,
    headers,
    limit=100,
    offset=0,
    description="Fetcher",
    method="GET",
    payload=None,
    is_paginated=True,
    debug=False
):
    if method == "GET":
        response = requests.get(
            url, headers=headers, params={"offset": offset, "limit": limit}
        )
    elif method == "POST":
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            params={"offset": offset, "limit": limit},
        )
    else:
        print(f"Unsupported HTTP method {method}")
        raise ValueError("Unsupported HTTP method")

    try:
        if response.status_code != 200:
            print(f"Unexpected status code: {response.status_code}")
            print(f"Response content: {response.content}")
            raise ValueError(f"Unexpected status code: {response.status_code}")
        data = response.json()
    except ValueError:
        if debug:
            print(
                f"{description} - Failed to decode JSON response. Status code: {response.status_code}"
            )
        raise ValueError("Failed to decode JSON response")

    total = data.get("total", 0)
    results = data.get("results", []) if is_paginated else data

    if debug:
        print(
            f"{description} - Fetched {len(results)} items with Offset {offset} and Limit {limit}"
        )
    return total, results, description


def extract_collibra_data(
    id,
    fetcher_function,
    collector_function,
    limit=100,
    offset=0,
    show_progress=False,
    is_paginated=True,
    return_collection="DICT",
    parallelism_count=1
):
    if return_collection == "DICT":
        collected = {}
    else:
        collected = []

    total = None
    pbar = None

    if parallelism_count <= 1:
        while True:
            total, results, extractor = fetcher_function(
                id, limit, offset, is_paginated=is_paginated
            )
            if total is not None and show_progress and pbar is None:
                
                pbar = tqdm(
                    total=total if total > 0 else 1,
                    desc=(
                        f"{extractor} Downloading data for {id}"
                        if id
                        else f"{extractor} Downloading data"
                    ),
                    unit=" documents",
                )
            if not results:
                break
            if isinstance(results, list):
                for result in results:
                    key, extracted = collector_function(result)
                    if return_collection == "DICT":
                        collected[key] = extracted
                    else:
                        collected.append(extracted)
            else:
                key, extracted = collector_function(results)
                if return_collection == "DICT":
                    collected[key] = extracted
                else:
                    collected.append(extracted)
            if pbar:
                pbar.update(len(results) if isinstance(results, list) else 1)
            offset += limit
            if total is not None and offset >= total:
                break
        if pbar:
            pbar.close()
    else:
        total, results, extractor = fetcher_function(
                id, limit, offset, is_paginated=is_paginated
            )
        if isinstance(results, list):
            for result in results:
                key, extracted = collector_function(result)
                if return_collection == "DICT":
                    collected[key] = extracted
                else:
                    collected.append(extracted)
        else:
            key, extracted = collector_function(results)
            if return_collection == "DICT":
                collected[key] = extracted
            else:
                collected.append(extracted)
                
        # Parallel fetching logic for parallelism_count > 1
        import concurrent.futures

        if total is None:
            total = 1
        results_len = len(results) if isinstance(results, list) else 1
        remaining = total - results_len
        chunk_size = remaining // parallelism_count
        remainder = remaining % parallelism_count

        offsets = []
        start_offset = offset + results_len
        for i in range(parallelism_count):
            size = chunk_size + (1 if i < remainder else 0)
            if size > 0:
                offsets.append((start_offset, size))
            start_offset += size

        def parallel_fetch(offset, size):
            local_collected = {} if return_collection == "DICT" else []
            local_total, local_results, extractor = fetcher_function(
                id, size, offset, is_paginated=is_paginated
                )
            if isinstance(local_results, list):
                for result in local_results:
                    key, extracted = collector_function(result)
                    if return_collection == "DICT":
                        local_collected[key] = extracted
                    else:
                        local_collected.append(extracted)
            else:
                key, extracted = collector_function(local_results)
                if return_collection == "DICT":
                    local_collected[key] = extracted
                else:
                    local_collected.append(extracted)
            return local_collected, len(local_results) if isinstance(local_results, list) else 1

        if show_progress:
            pbar = tqdm(total=total if total > 0 else 1, desc=f"Parallelized {extractor}", unit=" documents")
            pbar.update(results_len)
# Need to revisit this and how a checkpoint can be added
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallelism_count) as executor:
            futures = []
            for offset_val, size_val in offsets:
                futures.append(executor.submit(parallel_fetch, offset_val, size_val))
                
            for future in concurrent.futures.as_completed(futures):
                local_collected, count = future.result()
                if return_collection == "DICT":
                    collected.update(local_collected)
                else:
                    collected.extend(local_collected)
                if show_progress:
                    pbar.update(count)
            if show_progress:
                pbar.close()
    return collected


def roles_collector(role):
    return role.get("name"), {
        "id": role.get("id"),
        "name": role.get("name"),
        "description": role.get("description"),
        "disabled": role.get("disabled"),
    }


def get_roles(limit=100, offset=0, parallelism_count=5):
    def fetcher(id, limit, offset, is_paginated=True):
        return collibra_fetcher(
            f"{collibra_config['url']}/{collibra_config['paths']['roles']}",
            get_headers(),
            limit=limit,
            offset=offset,
            description="Roles Fetcher",
            is_paginated=is_paginated
        )

    return extract_collibra_data(
        None, fetcher, roles_collector, limit=limit, offset=offset, show_progress=True, parallelism_count=parallelism_count
    )


def asset_collector(asset):
    return asset.get("id"), {
        "id": asset.get("id"),
        "data product name": asset.get("name"),
        "data product display name": asset.get("displayName"),
        "domain id": asset.get("domain").get("id"),
        "owning platform": asset.get("domain").get("name"),
        "status": asset.get("status").get("name"),
        # "type id": asset.get("type").get("id")
    }


def get_asset(asset_id):
    def fetcher(asset_id, limit, offset, is_paginated=False):
        return collibra_fetcher(
            f"{collibra_config['url']}/{collibra_config['paths']['assets'].format(asset_id=asset_id)}",
            get_headers(),
            limit=limit,
            offset=offset,
            description="Asset Fetcher",
            is_paginated=is_paginated
        )

    return extract_collibra_data(
        asset_id, fetcher, asset_collector, is_paginated=False, show_progress=True
    )


def domain_collector(domain):
    return domain.get("id"),{
        "id": domain.get("id"),
        "owning platform": domain.get("name"),
        "business domain": domain.get("community").get("name")
    }


def get_domain(domain_id):
    def fetcher(domain_id, limit, offset, is_paginated=False):
        return collibra_fetcher(
            f"{collibra_config['url']}/{collibra_config['paths']['domains'].format(domain_id=domain_id)}",
            get_headers(),
            limit=limit,
            offset=offset,
            description="Domain Fetcher",
            is_paginated=is_paginated
        )

    return extract_collibra_data(
        domain_id, fetcher, domain_collector, is_paginated=False, show_progress=True
    )


def asset_details_collector(detail):
    return detail.get("type").get("name"), {
        "name": detail.get("type").get("name"),
        "value": detail.get("value"),
        "dataType": detail.get("type").get("resourceType"),
    }


def get_asset_details(asset_id, limit=10, offset=0, parallelism_count=5):
    def fetcher(asset_id, limit, offset, is_paginated=True):
        return collibra_fetcher(
            f"{collibra_config['url']}/{collibra_config['paths']['attributes'].format(asset_id=asset_id)}",
            get_headers(),
            limit=limit,
            offset=offset,
            description="Asset Details Fetcher",
            is_paginated=is_paginated
        )

    return extract_collibra_data(
        asset_id,
        fetcher,
        asset_details_collector,
        limit=limit,
        offset=offset,
        is_paginated=True,
        show_progress=True,
        parallelism_count=parallelism_count
    )


def asset_relation_source_collector(relation):
    return relation.get("type").get("id"), {
        "relation_id": relation.get("id"),
        "relation_type_id": relation.get("type").get("id"),
        "relation_incoming_id": relation.get("target").get("id"),
        "relation_incoming_name": relation.get("target").get("name"),
        "relation_outgoing_name": relation.get("source").get("name"),
        "relation_outgoing_id": relation.get("source").get("id"),
    }


def get_outgoing_relations_for(source_id, limit=10, offset=0, parallelism_count=5):
    def fetcher(source_id, limit, offset, is_paginated=True):
        return collibra_fetcher(
            f"{collibra_config['url']}/{collibra_config['paths']['relations_from_source'].format(asset_id=source_id)}",
            get_headers(),
            limit=limit,
            offset=offset,
            description="Asset Relations Source Fetcher",
            is_paginated=is_paginated
        )

    return extract_collibra_data(
        source_id,
        fetcher,
        asset_relation_source_collector,
        limit=limit,
        offset=offset,
        is_paginated=True,
        show_progress=True,
        return_collection="LIST",
        parallelism_count=parallelism_count
    )


def asset_relation_target_collector(relation):
    return relation.get("type").get("id"), {
        "relation_outgoing_id": relation.get("source").get("id"),
        "name": relation.get("source").get("name"),
        "spec": [],
    }


def get_incoming_relations_for(target_id, limit=10, offset=0, parallelism_count=5):
    def fetcher(target_id, limit, offset, is_paginated=True):
        return collibra_fetcher(
            f"{collibra_config['url']}/{collibra_config['paths']['relations_from_target'].format(asset_id=target_id)}",
            get_headers(),
            limit=limit,
            offset=offset,
            description="Asset Relations Target Fetcher",
            is_paginated=is_paginated
        )

    return extract_collibra_data(
        target_id,
        fetcher,
        asset_relation_target_collector,
        limit=limit,
        offset=offset,
        is_paginated=True,
        show_progress=True,
        return_collection="LIST",
        parallelism_count=parallelism_count
    )


# def get_asset_relations_as_target(asset_id, limit=10, offset=0):
#     url = f"{collibra_config['url']}/{collibra_config['paths']['relations_from_target'].format(asset_id=asset_id)}&offset={offset}&limit={limit}"
#     response = requests.get(url, headers=get_headers())
#     print("Fetched asset relations as source for asset id: ", asset_id, " with offset: ", offset)
#     return response.json()


def relation_type_collector(type):
    return type.get("id"), {
        "is_child_of": type.get("role"),
        "is_parent_of": type.get("coRole"),
        "type_outgoing_id": type.get("sourceType").get("id"),
        "type_incoming_id": type.get("targetType").get("id"),
        # "description": type.get("description")
    }


def get_relation_type(relation_type_id):
    def fetcher(relation_type_id, limit, offset, is_paginated=False):
        return collibra_fetcher(
                f"{collibra_config['url']}/{collibra_config['paths']['relation_types'].format(relation_type_id=relation_type_id)}",
                get_headers(),
                limit=limit,
                offset=offset,
                description="Relation Type Fetcher",
                is_paginated=is_paginated
            )

    return extract_collibra_data(
        relation_type_id,
        fetcher,
        relation_type_collector,
        is_paginated=False,
        show_progress=True
    )

def process_relation(asset_relation_source, visited_nodes, visited_nodes_lock, limit=10, parallelism_count=8):
    relation_incoming_id = asset_relation_source.get("relation_incoming_id")
    relation_incoming_name = asset_relation_source.get("relation_incoming_name")
    relation_type_id = asset_relation_source.get("relation_type_id")

    relation_type = get_relation_type(relation_type_id)
    is_child_of = relation_type.get(relation_type_id, {}).get("is_child_of")

    if not is_child_of or not relation_incoming_id:
        return None, None, None

    with visited_nodes_lock:
        if is_child_of not in visited_nodes:    
            visited_nodes[is_child_of] = set()
        
        if relation_incoming_id in visited_nodes[is_child_of]:
            return None, None, None

        visited_nodes[is_child_of].add(relation_incoming_id)

    table_detail = get_table_details(asset_id, relation_incoming_id, relation_incoming_name, is_child_of, limit, parallelism_count)
    
    return is_child_of, table_detail, relation_incoming_id

# def populate_asset_types(asset_type_id, limit=100, offset=0,parallelism_count=5):
#     if len(asset_types_meta) == 0:
#         url = f"{collibra_config['url']}/{collibra_config['paths']['asset_types'].format(asset_type_id=asset_type_id)}"
#         loop = True
#         data_types = set()

#         while loop:
#             response = requests.get(
#                 url + "&offset=" + str(offset) + "&limit=" + str(limit),
#                 headers=get_headers(),
#             )
#             types = response.json().get("results", [])

#             if len(types) == 0:
#                 loop = False
#             else:
#                 for type in types:
#                     asset_types_meta[type.get("name")] = {
#                         "id": type.get("id"),
#                         "description": type.get("description"),
#                     }
#                     asset_types[type.get("name")] = ""
#                     data_types.add(type.get("attributeTypeDiscriminator"))
#                 offset += limit

#         if len(data_types) != 0:
#             print("Found unique data types as below:")
#             for data_type in data_types:
#                 print(4 * " ", data_type)

def process_column(column, asset_id, parallelism_count):
    if column.get("relation_outgoing_id") == asset_id or (len(column.get("name").split(">")) != 5):  # schema has 3 and table has 4 and column has 5
        return None
    
    column_details = get_asset_details(
        column.get("relation_outgoing_id"), parallelism_count=parallelism_count
    )
    detail = {"name": column.get("name"), "specs": []}
    for spec, details in column_details.items():
        detail["specs"].append(
            {
                "name": spec,
                "value": details.get("value"),
                "data_type": details.get("data_type"),
            }
        )
    return detail

def get_columns_for_table(relation_incoming_id, asset_id, limit=10, parallelism_count=5):
    columns_queue = get_incoming_relations_for(
                        relation_incoming_id, limit, 0, parallelism_count=parallelism_count
                    ) 
    if len(columns_queue) > 0:
        chunk_size = len(columns_queue) // parallelism_count
        remainder = len(columns_queue) % parallelism_count
        chunks = []
        start = 0
        for i in range(parallelism_count):
            end = start + chunk_size + (1 if i < remainder else 0)
            if start < end:
                chunks.append(columns_queue[start:end])
            start = end

        details = []
        tasks = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallelism_count) as executor:
            for chunk in chunks:
                for col in chunk:
                    id = f"{relation_incoming_id}{os.sep}{col.get('relation_outgoing_id')}"
                    future = submit_job_if_not_cached(
                        construct_file_name(
                            asset_id, 
                            ASSET_TYPE.COLUMNS, 
                            id
                        ), 
                        ASSET_TYPE.COLUMNS, 
                        executor, 
                        process_column, 
                        col, 
                        asset_id, 
                        parallelism_count
                    )
                    tasks[future] = id
                # futures.append(
                #     executor.submit(
                #         lambda chunk: [
                #             process_column(col, asset_id, parallelism_count)
                #             for col in chunk
                #         ],
                #         chunk,
                #     )
                # )
        for future in concurrent.futures.as_completed(tasks.keys()):
            collect_and_cache_results(
                asset_id,
                ASSET_TYPE.COLUMNS, 
                construct_file_name(
                    asset_id, 
                    ASSET_TYPE.COLUMNS, 
                    tasks[future]
                ),
                future, 
                tasks[future]
            )
    #         for detail in future.result():
    #             if detail is not None:
    #                 details.append(detail)
    
        return details


def get_table_details(asset_id, relation_incoming_id, relation_incoming_name, is_child_of, limit, parallelism_count):
    match is_child_of:
        case "Data Product contains Table":
            details = get_columns_for_table(relation_incoming_id, asset_id, limit, parallelism_count=parallelism_count)
            
            return {
                    "id": relation_incoming_id,
                    "table": relation_incoming_name,
                    "columns": details,
                }
        case _:
            return {"id": relation_incoming_id, "value": relation_incoming_name}


class ASSET_TYPE(Enum):
    ROOT = "root"
    STATS = "stats"
    ASSET = "asset"
    ASSET_DETAILS = "asset_details"
    ASSET_RELATIONS_SOURCE_QUEUE = "asset_relations_source_queue"
    TABLE = "table"
    CONTRACT = "contract"
    DUMP = "dump"
    DOMAIN = "domain"
    COLUMNS = "columns"
    RESPONSIBILITIES = "responsibilities"

def construct_file_name(asset_id=None, type:ASSET_TYPE=ASSET_TYPE.ROOT, id=""):
    if id and " " in id:
        id = id.replace(" ", "_")
    match type:
        case ASSET_TYPE.ROOT:
            file_name = ""
        case ASSET_TYPE.ASSET:
            file_name = f"{asset_id}/asset.json"
        case ASSET_TYPE.ASSET_DETAILS:
            file_name = f"{asset_id}/asset_details.json"
        case ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE:
            file_name = f"{asset_id}/ASSET_RELATIONS_SOURCE_QUEUE/{id}.relation.json"
        case ASSET_TYPE.TABLE:
            file_name = f"{asset_id}/TABLES/{id}.table.json"
        case ASSET_TYPE.COLUMNS:
            file_name = f"{asset_id}/COLUMNS/{id}.column.json"
        case ASSET_TYPE.CONTRACT:
            file_name = f"{asset_id}.contract.json"
        case ASSET_TYPE.DUMP:
            file_name = f"{asset_id}/dump.json"
        case ASSET_TYPE.DOMAIN:
            file_name = f"{asset_id}/domain.json"
        case ASSET_TYPE.RESPONSIBILITIES:
            file_name = f"{asset_id}/responsibility.json"
        case _:
            file_name = f"{asset_id}/{id}.json"
    return f"dump/{file_name}" if len(file_name) > 0 else "dump"
   
def dump_json(asset_id, type:ASSET_TYPE, data, file_name=""):
    file_path = construct_file_name(asset_id, type, file_name)
    path = pathlib.Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    match type:
        case ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE:
            for item in data:
                item_file_path = construct_file_name(asset_id, ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE, item.get("relation_incoming_id"))
                with open(item_file_path, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=2)
                    print(f"Saved data to {item_file_path}")
            with open(construct_file_name(asset_id, ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE, id=asset_id), "w", encoding="utf-8") as f:
                json.dump(item, f, indent=2)
        case _ : 
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                print(f"Saved data to {file_path}")
    return file_path


from jinja2 import Environment, FileSystemLoader

def render_template(asset_id, data_path, template_path):
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    env = Environment(
        loader=FileSystemLoader('.'),
        autoescape=True,
        # filters={
        #     'extract_href': extract_href,
        #     'extract_last_value': extract_last_value,
        #     'iso_timestamp': iso_timestamp
        # },
        extensions=['jinja2.ext.do'],
        trim_blocks=True,
        lstrip_blocks=True
    )
    # Register custom filters
    env.filters['extract_href'] = extract_href
    env.filters['extract_last_value'] = extract_last_value
    env.filters['iso_timestamp'] = iso_timestamp
    env.filters['tojson'] = toJson
    
    template = env.get_template(template_path)
    data = template.render(data=data)
    data = data.replace('\n', '').replace('"', '').replace('&#34;', '"')
    data = re.sub(r'\s\s+', ' ', data)
    # dump_json(asset_id, ASSET_TYPE.CONTRACT, data)
    contract_file = construct_file_name(asset_id, ASSET_TYPE.CONTRACT)
    with open(contract_file, 'w', encoding='utf-8') as f:
        f.write(data)
        print(f"Saved rendered contract to {contract_file}")


def check_and_invoke(asset_id, type:ASSET_TYPE, fn, id, file_name=""):
    file_name = construct_file_name(asset_id, type, id)
    if not pathlib.Path(file_name).exists():
        results = fn(id)
        for item in results:
            result = results.get(item)
            dump_json(asset_id, type, result, file_name)
    else:
        result = json.load(open(file_name, 'r', encoding='utf-8'))
        print(f"Loaded cache from file: {file_name}")
    return result

def submit_job_if_not_cached(file_path, type: ASSET_TYPE, executor, fn, /, *args, **kwargs):
    if type == ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE or type == ASSET_TYPE.TABLE or type == ASSET_TYPE.COLUMNS:
        dir_path = pathlib.Path(file_path).parent
        if dir_path.exists() and any(dir_path.iterdir()) and pathlib.Path(file_path).exists():
            return None
    else:
        if pathlib.Path(file_path).exists():
            return None
    return executor.submit(fn, *args, **kwargs)

def collect_and_cache_results(asset_id, type:ASSET_TYPE, file_path, future, target_file_name=""):
    if future:
        result = future.result()
    else:
        if ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE == type or ASSET_TYPE.TABLE == type and ASSET_TYPE.COLUMNS == type:
            result = []
            dir_path = pathlib.Path(file_path).parent
            for item_file in pathlib.Path(dir_path).iterdir():
                if  item_file.is_dir() or not item_file.name.endswith(".json") or not item_file.name.startswith(f"{asset_id}_"):
                    continue
                with open(item_file, 'r', encoding='utf-8') as f:
                    item_data = json.load(f)
                    print(f"Loaded cache from file: {item_file}")
                    result.append(item_data)
        else:
            result = json.load(open(file_path, 'r', encoding='utf-8'))
            print(f"Loaded cache from file: {file_path}")
    
    if result and future:
        dump_json(asset_id, type, result, target_file_name)
    
    return result

def clear_cache(asset_id, type: ASSET_TYPE, id=""):
    file_name = construct_file_name(asset_id, type, id=id)
    if pathlib.Path(file_name).exists():
        pathlib.Path(file_name).unlink()
        print(f"Cleared cache for {file_name}")

def process_relational_data(asset_id, asset_relations_source_queue, asset_relations, asset_relations_lock, limit=10, parrallelism_count=8):
    # futures = []
    relation_incoming_ids = {}
    
    with ThreadPoolExecutor(max_workers=parallelism_count) as executor:
        for asset_relation_source in asset_relations_source_queue:
            if asset_relation_source:
                relation_incoming_id = asset_relation_source.get("relation_incoming_id")
                future = submit_job_if_not_cached(
                    construct_file_name(asset_id, ASSET_TYPE.TABLE,relation_incoming_id), 
                    ASSET_TYPE.TABLE,
                    executor,
                    process_relation,
                    asset_relation_source,
                    visited_nodes,
                    visited_nodes_lock,
                    limit=limit,
                    parallelism_count=parrallelism_count
                )
                if future:
                    relation_incoming_ids[future] = asset_relation_source.get("relation_incoming_id")

        for future in as_completed(relation_incoming_ids.keys()):
            is_child_of, table_detail, relation_incoming_id = collect_and_cache_results(
                asset_id,
                ASSET_TYPE.TABLE,
                construct_file_name(asset_id, ASSET_TYPE.TABLE, relation_incoming_ids[future]),
                future,
                relation_incoming_ids[future]
            )
                    
                        
def save_asset(asset_id):    
    print(f"Saving asset: {asset_id}")
    if not pathlib.Path(construct_file_name(asset_id, ASSET_TYPE.DUMP, "")).exists():
        output_data = {}
        
        asset_details_file_name= construct_file_name(asset_id, ASSET_TYPE.ASSET_DETAILS)
        with open(asset_details_file_name, 'r', encoding='utf-8') as f:
            asset_details = json.load(f)
        output_data.update({k: v for k, v in asset_details.items()})
        asset_details = None
        
        domain_file_name = construct_file_name(asset_id, ASSET_TYPE.DOMAIN)
        with open(domain_file_name, 'r', encoding='utf-8') as f:
            domain = json.load(f)
        output_data.update({k:v for k, v in domain.items()})
        domain = None
        
        responsibility_file_name = construct_file_name(asset_id, ASSET_TYPE.RESPONSIBILITIES)
        if pathlib.Path(responsibility_file_name).exists():
            with open(responsibility_file_name, 'r', encoding='utf-8') as f:
                responsibility = json.load(f)
            output_data.update({"roles": responsibility.get("roles", [])})
            responsibility = None

        asset_file_name = construct_file_name(asset_id, ASSET_TYPE.ASSET)
        with open(asset_file_name, 'r', encoding='utf-8') as f:
            asset = json.load(f)
        output_data.update({k: v for k, v in asset.get(asset_id).items()})    
        asset = None

        asset_relations_dir = pathlib.Path(construct_file_name(asset_id, ASSET_TYPE.TABLE)).parent
        tables = {}
        for item_file in pathlib.Path(asset_relations_dir).iterdir():
            if item_file.is_dir() or not item_file.name.endswith(".json"):
                continue
            with open(item_file, 'r', encoding='utf-8') as f:
                item_data = json.load(f)
                tables[item_data[0]] = item_data

        for table_id, table_data in tables.items():
            if table_id=="Data Product contains Table":
                column_table_folder = pathlib.Path(construct_file_name(asset_id, ASSET_TYPE.COLUMNS, table_id)).parent
                if not column_table_folder.exists():
                    continue
                for table_folder in pathlib.Path(column_table_folder).iterdir():
                    if table_folder.is_file():
                        continue
                    folder_dir = pathlib.Path(table_folder)
                    if not folder_dir.exists():
                        continue
                    for column_file in folder_dir.iterdir():
                        if column_file.is_dir() or not column_file.name.endswith(".json"):
                            continue
                        with open(column_file, 'r', encoding='utf-8') as f:
                            column_data = json.load(f)
                            # tables[table_id][1]["columns"].append(column_data)
                            table_data[1]["columns"].append(column_data)

        for key, value in tables.items():
            if key not in output_data:
                output_data[key] = []
            output_data[key].append(value[1])
        
        dump_json(asset_id, ASSET_TYPE.DUMP, output_data)

    print(f"Skipped asset processing for dump for asset: {asset_id}")
    render_template(
        asset_id=asset_id,
        data_path=construct_file_name(asset_id, ASSET_TYPE.DUMP),
        template_path='contract.template.v6.json'
    )
    print(f"Done processing the asset [{asset_id}], created contract at [{construct_file_name(asset_id, ASSET_TYPE.CONTRACT)}]")

if __name__ == "__main__":
    # action = "scrape"
    action = "process"
    if(action == "scrape"):
        parallelism_count=8
        limit = 1000
        start_time = time.time()
        targets = []

        scraping_targets = {}
        config_path = pathlib.Path('scraping_targets_config.json')
        if not config_path.exists():
            raise FileNotFoundError("scraping_targets_config.json does not exist. Please provide the file before running the script.")

        with open('scraping_targets_config.json', 'r', encoding='utf-8') as f:
            scraping_targets = json.load(f)

        for target in scraping_targets.get("targets", []):
            targets.append({
                "asset_id": target.get("Data Product Name 3 Link").split("/")[-1],
            })
        
        for target in targets:
            asset_id = target.get("asset_id")
            print(f"Processing asset id: [{asset_id}]")

            asset = {}
            asset_details = {}
            asset_relations_source_queue=[]
            
            asset_file_id = construct_file_name(asset_id, ASSET_TYPE.ASSET)
            asset_details_file_id = construct_file_name(asset_id, ASSET_TYPE.ASSET_DETAILS)
            asset_relations_source_queue_file_id = construct_file_name(asset_id, ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE, id=asset_id)

            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_asset = submit_job_if_not_cached(asset_file_id,ASSET_TYPE.ASSET, executor, get_asset, asset_id)
                future_asset_details = submit_job_if_not_cached(asset_details_file_id,ASSET_TYPE.ASSET_DETAILS, executor, get_asset_details, asset_id, limit, 0, parallelism_count=parallelism_count)
                future_asset_relations_source_queue = submit_job_if_not_cached(asset_relations_source_queue_file_id,ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE, executor, get_outgoing_relations_for, asset_id, limit, 0, parallelism_count=parallelism_count)

                asset = collect_and_cache_results(asset_id, ASSET_TYPE.ASSET, asset_file_id, future_asset)
                asset_details = collect_and_cache_results(asset_id, ASSET_TYPE.ASSET_DETAILS, asset_details_file_id, future_asset_details)
                asset_relations_source_queue = collect_and_cache_results(asset_id, ASSET_TYPE.ASSET_RELATIONS_SOURCE_QUEUE, asset_relations_source_queue_file_id, future_asset_relations_source_queue)

            domain_id = asset.get(asset_id).get("domain id")
            status = asset.get(asset_id).get("status")
            lifecycle = asset_details.get("Data Product Lifecycle", {}).get("value") 
            asset = None
            asset_details = None
            check_and_invoke(asset_id, ASSET_TYPE.DOMAIN, get_domain, domain_id)
        
            # Filtering Criteria
            # if asset.get(asset_id).get("status") not in ["Live", "In Progress"] and asset_details.get("Data Product Lifecycle", {}).get("value") not in ["Published"]:
                # print(f"Skipping asset [{asset_id}] due to status [{asset.get('status')}] and lifecycle [{asset_details.get('Data Product Lifecycle', {}).get('name')}]")
                # continue

            visited_nodes = {}
            # remove this line with refactoring
            asset_relations = {}
            visited_nodes_lock = threading.Lock()
            asset_relations_lock = threading.Lock()

            process_relational_data(asset_id, asset_relations_source_queue, asset_relations,asset_relations_lock, limit=limit, parrallelism_count=parallelism_count)

            seconds = time.time() - start_time
            dump_json(asset_id, ASSET_TYPE.STATS,  {"duration": f"{seconds/60:.2f}m" if seconds > 60 else f"{seconds:.2f}s"}, "runtime.stats")
            
            # save_asset(asset_id, seconds)
        print("Scrapping all assets Complete.")
    else:
        assets_dir = pathlib.Path(construct_file_name())
        for item_file in assets_dir.iterdir():
            if item_file.is_dir():
                asset_id = item_file.name
                save_asset(asset_id)
        print("Processing of all assets complete.")