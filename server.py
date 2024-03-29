import os
import hashlib
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
import subprocess
import sys
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
import uuid
from pydantic import BaseModel
import asyncio
from fastapi.middleware.cors import CORSMiddleware

def is_image_less_than_1024x1024(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            return width <= 1024 or height <= 1024
    except Exception as e:
        print(f"Error: {e}")
        return False
    
python_path = sys.executable
print("Python interpreter path:", python_path)

app = FastAPI()

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def log_message(message):
    with open('log.txt', 'a+') as log_file:
        log_file.write(message + '\n')

def calculate_sha256(file_content):
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    return sha256_hash.hexdigest()

all_tasks = []
tasks = []
task_id = ""
ip_request_count = {}
credit_dict = {}
credit_dict["0c74fad5-7ae9-487b-8b49-8800ca511e50"] = 99
max_default_credits = 50
max_ip_requests = 250

def get_and_remove_first_task(tasks_array):
    if tasks_array:
        return tasks_array.pop(0)  # Removes and returns the first element from the array
    else:
        return None
    
async def call_script(filename, token, background_tasks: BackgroundTasks):
    global task_id

    print("task id: " + task_id + ", filename: " + filename)

    processed_filename = check_if_run_full_filename(task_id)
    tasks.append(filename)

    if task_id == "" or processed_filename != None: 
        try:
            # Get and remove the first task from the array
            first_task = get_and_remove_first_task(tasks)
            if first_task:
                all_tasks.append(filename)
                out_filename = filename
                task_id = filename

                # Asynchronously execute the subprocess
                process = await asyncio.create_subprocess_exec(
                    "python", "esr.py", os.path.join(UPLOAD_FOLDER, filename), os.path.join(DOWNLOAD_FOLDER, out_filename),
                    stdout=asyncio.subprocess.PIPE  # Capture stdout
                )

                # Wait for the subprocess to complete
                stdout, _ = await process.communicate()

                # Decode the captured stdout
                stdout_str = stdout.decode().strip()

                if stdout_str.endswith('upscaled: ' + os.path.join(DOWNLOAD_FOLDER, out_filename)) == False:
                    if get_credit_count(token) < max_default_credits or token == "0c74fad5-7ae9-487b-8b49-8800ca511e50":
                        increment_credit_count(token)

                    task_id = ""
            
                print(stdout_str)

            return {"status": "processing"}
        except subprocess.CalledProcessError as e:
            return {"error": "could not process"}
        finally:
            # Asynchronously execute the subprocess
            process = await asyncio.create_subprocess_exec(
                "sleep", "5"
            )

            # Wait for the subprocess to complete
            await process.wait()

            # Get and remove the first task from the array
            first_task = get_and_remove_first_task(tasks)
            if first_task:
                background_tasks.add_task(call_script, first_task, token, background_tasks)
            else:
                print("No task to add")
    else:
        # Asynchronously execute the subprocess
        process = await asyncio.create_subprocess_exec(
            "sleep", "5"
        )

        # Wait for the subprocess to complete
        await process.wait()

        # Get and remove the first task from the array
        first_task = get_and_remove_first_task(tasks)
        if first_task:
            background_tasks.add_task(call_script, first_task, token, background_tasks)
        else:
            print("No task to add")

# Function to increment request count for an IP
def increment_request_count(ip):
    if ip in ip_request_count:
        ip_request_count[ip] += 1
    else:
        ip_request_count[ip] = 1

def get_request_count(ip): 
    if ip in ip_request_count:
        return ip_request_count[ip]
    else:
        return 0

def get_ip(request: Request):
    return request.client.host

def get_credit_count(uuid): 
    if uuid in credit_dict:
        return credit_dict[uuid]
    else:
        return 0
    
def decrement_credit_count(uuid):
    if uuid in credit_dict:
        credit_dict[uuid] -= 1
        log_message(uuid + ' credits: ' + str(credit_dict[uuid]))

def increment_credit_count(uuid):
    if uuid in credit_dict:
        credit_dict[uuid] += 1
        log_message(uuid + ' credits: ' + str(credit_dict[uuid]))

@app.middleware("http")
async def check_request_limit(request: Request, call_next):
    if request.url.scheme == 'http':
        return JSONResponse(status_code=400, content={"status": "https only"})
    
    global max_ip_requests

    # Check if the request path starts with '/status'
    if not request.url.path.startswith('/status') and not request.url.path.startswith('/refund') and not request.url.path.startswith('/process') and not request.url.path.startswith('/purchase') and not request.url.path.startswith('/credits'):
        ip = get_ip(request)
        count = get_request_count(ip)
        if count > max_ip_requests:
            return JSONResponse(status_code=429, content={"detail":"Too many requests"})
        else:
            increment_request_count(ip)
            response = await call_next(request)
            return response
    else:
        response = await call_next(request)
        return response

# Allow requests from all origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise JSONResponse(status_code=400, content={"detail":"No file provided"})
    
    # Read file content
    file_content = await file.read()
    
    # Calculate SHA256 hash
    sha256_hash = calculate_sha256(file_content)
    
    # Append hash to filename
    filename, ext = os.path.splitext(file.filename)
    hashed_filename = f"{filename}_{sha256_hash}{ext}"
    
    # Save file with hashed filename
    with open(os.path.join(UPLOAD_FOLDER, hashed_filename), "wb") as f:
        f.write(file_content)
    
    return {"status": "uploaded", "filename": sha256_hash}

def check_if_uploaded(id: str):
    files = os.listdir(UPLOAD_FOLDER)
    for filename in files:
        # Find the index of the last occurrence of "_"
        last_underscore_index = filename.rfind("_")

        # Find the index of the first occurrence of "." after the last "_"
        first_dot_index_after_last_underscore = filename.find(".", last_underscore_index)

        if first_dot_index_after_last_underscore != -1:
            # Split the filename at the first dot after the last underscore
            filename_parts = [filename[:first_dot_index_after_last_underscore], filename[first_dot_index_after_last_underscore:]]
        else:
            # If no dot found after the last underscore, consider the whole filename as the first part
            filename_parts = [filename]

        if filename_parts[0].endswith(id):
            return filename
    
    return False

@app.get("/status/{id}")
async def check_upload_status(id: str):
    filename = check_if_uploaded(id)
    if filename:  
        return {"status": "uploaded"} 
    else:
        return {"status": "not found"}

@app.get("/refund/{id}/{token}")
async def check_upload_status(id: str, token: str):
    filename = check_if_run(id)
    
    global max_default_credits

    if filename:    
        return {"status": "uploaded", "filename": filename}
    else:
        try:
            # Get the index of the string
            index = tasks.index(id)

            return {"status": "processing", "priority": index}
        except ValueError:
            # Find the index of the last occurrence of "_"
            last_underscore_index = task_id.rfind("_")

            # Find the index of the first occurrence of "." after the last "_"
            first_dot_index_after_last_underscore = task_id.find(".", last_underscore_index)

            if first_dot_index_after_last_underscore != -1:
                # Split the filename at the first dot after the last underscore
                filename_parts = [task_id[:first_dot_index_after_last_underscore], task_id[first_dot_index_after_last_underscore:]]
            else:
                # If no dot found after the last underscore, consider the whole filename as the first part
                filename_parts = [task_id]

            if filename_parts[0].endswith(id):
                return {"status": "processing"}
            else:
                try:
                    # Get the index of the string
                    index = all_tasks.index(id)

                    if get_credit_count(token) < max_default_credits:
                        increment_credit_count(token)

                    return {"status": "refunded"}
                except ValueError:
                    return {"status": "not found"}
        
def check_if_run(id: str):
    files = os.listdir(DOWNLOAD_FOLDER)
    for filename in files:
        # Find the index of the last occurrence of "_"
        last_underscore_index = filename.rfind("_")

        # Find the index of the first occurrence of "." after the last "_"
        first_dot_index_after_last_underscore = filename.find(".", last_underscore_index)

        if first_dot_index_after_last_underscore != -1:
            # Split the filename at the first dot after the last underscore
            filename_parts = [filename[:first_dot_index_after_last_underscore], filename[first_dot_index_after_last_underscore:]]
        else:
            # If no dot found after the last underscore, consider the whole filename as the first part
            filename_parts = [filename]

        if filename_parts[0].endswith(id):
            return filename
    return None

def check_if_run_full_filename(id: str):
    files = os.listdir(DOWNLOAD_FOLDER)
    for filename in files:
        if filename == id:
            return filename
    return None

@app.get("/process/{id}")
async def check_process_status(id: str):
    has_run = check_if_run(id)

    files = os.listdir(UPLOAD_FOLDER)
    for filename in files:
        # Find the index of the last occurrence of "_"
        last_underscore_index = filename.rfind("_")

        # Find the index of the first occurrence of "." after the last "_"
        first_dot_index_after_last_underscore = filename.find(".", last_underscore_index)

        if first_dot_index_after_last_underscore != -1:
            # Split the filename at the first dot after the last underscore
            filename_parts = [filename[:first_dot_index_after_last_underscore], filename[first_dot_index_after_last_underscore:]]
        else:
            # If no dot found after the last underscore, consider the whole filename as the first part
            filename_parts = [filename]
        
        if filename_parts[0].endswith(id):
            try:
                # Get the index of the string
                index = tasks.index(filename)

                if has_run != None:
                    return {"status": "processed"}
                else:
                    return {"status": "processing", "priority": index}
            except ValueError:
                if has_run != None:
                    return {"status": "processed"}

    # Find the index of the last occurrence of "_"
    last_underscore_index = task_id.rfind("_")

    # Find the index of the first occurrence of "." after the last "_"
    first_dot_index_after_last_underscore = task_id.find(".", last_underscore_index)

    if first_dot_index_after_last_underscore != -1:
        # Split the filename at the first dot after the last underscore
        filename_parts = [task_id[:first_dot_index_after_last_underscore], task_id[first_dot_index_after_last_underscore:]]
    else:
        # If no dot found after the last underscore, consider the whole filename as the first part
        filename_parts = [task_id]

    if has_run != None:
        return {"status": "processed"}
    elif filename_parts[0].endswith(id):
        return {"status": "processing"}
    else:
        return {"status": "not found"}

def is_image_filename(filename):
    return filename.lower().endswith(('.png', '.jpg', '.jpeg'))

class ProcessRequest(BaseModel):
    id: str
    token: str

@app.post("/run")
async def get_hash(process_request: ProcessRequest, background_tasks: BackgroundTasks):
    if get_credit_count(process_request.token) == 0:
        return {"error": "not enough credits" }
        
    files = os.listdir(UPLOAD_FOLDER)
    for filename in files:
        # Find the index of the last occurrence of "_"
        last_underscore_index = filename.rfind("_")

        # Find the index of the first occurrence of "." after the last "_"
        first_dot_index_after_last_underscore = filename.find(".", last_underscore_index)

        if first_dot_index_after_last_underscore != -1:
            # Split the filename at the first dot after the last underscore
            filename_parts = [filename[:first_dot_index_after_last_underscore], filename[first_dot_index_after_last_underscore:]]
        else:
            # If no dot found after the last underscore, consider the whole filename as the first part
            filename_parts = [filename]

        id = process_request.id

        if filename_parts[0].endswith(id):
            processed_filename = check_if_run_full_filename(filename)

            if processed_filename == None and is_image_less_than_1024x1024(os.path.join(UPLOAD_FOLDER, filename)) and is_image_filename(os.path.join(UPLOAD_FOLDER, filename)):
                try:
                    # Get the index of the string
                    index = tasks.index(filename)

                    if index >= 0:
                        return {"status": "already submitted"}
                    else:
                        {"error": "could not process; may be submitted" }
                except ValueError:
                    if task_id != filename:
                        try:
                            background_tasks.add_task(call_script, filename, process_request.token, background_tasks)

                            decrement_credit_count(process_request.token)
        
                            return {"status": "submitted"}
                        except Exception as e:
                            return {"error": "could not process; try again later"}
                    else:
                        return {"status": "already submitted"}
            elif processed_filename:
                return {"status": "done"}
    return {"error": "could not process"}

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)  # Replace "your_directory" with the directory containing your files
    return FileResponse(file_path, filename=filename)

class PurchaseRequest(BaseModel):
    credit_card_number: str
    pin: str

@app.post("/purchase")
async def process_purchase(purchase_request: PurchaseRequest):
    # Access credit card number and pin from the request body
    credit_card_number = purchase_request.credit_card_number
    pin = purchase_request.pin

    new_uuid = uuid.uuid4()

    while str(new_uuid) == "0c74fad5-7ae9-487b-8b49-8800ca511e50":
        new_uuid = uuid.uuid4()

    credit_dict[str(new_uuid)] = 5
    log_message(str(new_uuid) + ' credits: ' + str(credit_dict[str(new_uuid)]))
    
    return {"status": "success", "token": new_uuid}

@app.get("/credits/{token}")
async def process_purchase(token: str):
    if token in credit_dict:
        return {"credits": credit_dict[token], "token": token}
    else:
        return {"credits": 0}
