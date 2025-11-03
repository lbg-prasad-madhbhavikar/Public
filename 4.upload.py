import os 
import requests 
import pathlib
 
directory_path = "dump"
url = "https://registration.lcap.ap-bld.oncp.dev/foundation-api/v1/contract/upload" 
# url = "https://registration.lcap.ap-int.oncp.group/foundation-api/v1/contract/upload" 
 
jwt_token = "eyJraWQiOiJsYmdKd3RUb2tlbklkMDEiLCJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJMQ0FQLUFWQVRBUiIsInN1YiI6ImF2YXRhcnxiYzgyZTFmZi1mOWJiLTQ2NTYtOTAyOS1hZjdmMDk0MTlhNTJ8MTIzMjMiLCJhdWQiOlsiNjFkOGVmNzUtN2U4OC00MTVlLWI1MWEtYzY3Mzc5M2Q3ZWQ3IiwiYzQxMmE3MGUtYjk4Yi00MjMzLWEwYmItYmU4ZmEwZTkwOWQxIl0sImlhdCI6MTc2MTYwNTA5MCwiZXhwIjoxNzYxNjA1MzkwLCJnaXZlbl9uYW1lIjoiYXZhdGFyIiwiZmFtaWx5X25hbWUiOiJhZG1pbjEiLCJlbWFpbCI6ImF2YXRhci1hZG1pbkBsbG95ZHNiYW5raW5nLmNvbSIsInBpY3R1cmUiOiJodHRwOi8vZXhhbXBsZS5jb20vamFuZWRvZS9tZS5qcGciLCJyb2xlIjoiQURNSU4iLCJwZXJtaXNzaW9ucyI6WyJ2aWV3IiwiZWRpdCIsImNyZWF0ZSIsInVwZGF0ZSIsImRlbGV0ZSJdfQ.tDzEChlDKphhc4IftlAdZ6Op3-xavm2VJjWbY8BP9TMq0MAmtvG3xVnTpWCS0Mq_clLdltC2UpQmOwN9bLr1og" 
 
# Prepare headers with JWT 
headers = {
    "Authorization": f"Bearer JWT {jwt_token}", 
    "x-tenant-id": "avatar", 
    "content-type": "multipart/form-data", 
    "x-correlation-id": "something test" 
} 

location = pathlib.Path(directory_path)
for filename in location.iterdir():
    if filename.is_file() and filename.name.endswith(".contract.json"):
        print(f"Found contract file: {filename.name}...")
        asset_id = filename.name.split(".")[0]
        part_size = 1000 * 1024  # 1000 KB in bytes
        upload_dir = pathlib.Path(f"{directory_path}/upload/{asset_id}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(filename, "rb") as f:
            data = f.read()
            num_parts = (len(data) + part_size - 1) // part_size
            for i in range(num_parts):
                part_data = data[i * part_size : (i + 1) * part_size]
                part_filename = upload_dir / f"{filename.name}.part{i+1}"
                with open(part_filename, "wb") as pf:
                    pf.write(part_data)
                    print(f"Created part file: {part_filename.name}")
        
        # Load from upload/{asset_id} location
        part_files = sorted(upload_dir.glob(f"{filename.name}.part*"))
        total_parts = len(part_files)
        for idx, part_file in enumerate(part_files, start=1):
            part_number = idx
            print(f"Asset ID: {asset_id}, Part Number: {part_number}, Total Parts: {total_parts}, Part File: {part_file.name}")
        
            print(f"Uploading {part_file}...")
            # with open(part_file, "rb") as f:
            #     files = {"file": f} 
            #     response = requests.post(url,  
            #                             headers={ 
            #                                 "Authorization": f"Bearer {jwt_token}", 
            #                                 "x-tenant-id": "avatar", 
            #                                 "content-type": "multipart/form-data", 
            #                                 "x-correlation-id": f"{part_file.name.split(".")[0]}-{part_number}""  
            #                             },
            #                             files=files, 
            #                             verify=False 
            #                             ) 
    
            # if response.status_code == 201: 
            #     print(f"{filename} uploaded successfully!") 
            # else: 
            #     print(f"Failed to upload {filename}. Status code: {response.status_code}, Response: {response.text}")