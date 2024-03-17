import os
import hashlib
from fastapi import FastAPI, File, UploadFile, HTTPException
import subprocess
import sys
from fastapi.responses import FileResponse
from PIL import Image

def is_image_less_than_768x768(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            return width < 768 or height < 768
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

def calculate_sha256(file_content):
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    return sha256_hash.hexdigest()

async def call_script(filename):
    out_filename = filename
    try:
        subprocess.run([".\\venv\\Scripts\\python.exe", "launch.py", "--disable-nan-check", "--opt-sub-quad-attention", os.path.join(UPLOAD_FOLDER, filename), os.path.join(DOWNLOAD_FOLDER, out_filename)], check=True)
        return out_filename
    except subprocess.CalledProcessError as e:
        return {"error": f"Error executing script: {e}"}
    
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
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
    
    return {"filename": sha256_hash, "status": "uploaded"}

@app.get("/status/{id}")
async def check_upload_status(id: str):
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
            return {"filename": filename, "status": "uploaded"}
    return {"id": id, "status": "not found"}

@app.get("/process/{id}")
async def check_process_status(id: str):
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
            return {"filename": filename, "status": "processed"}
    return {"id": id, "status": "not found"}

def is_image_filename(filename):
    return filename.lower().endswith(('.png', '.jpg', '.jpeg'))

@app.get("/run/{id}")
async def get_hash(id: str):
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
            if is_image_less_than_768x768(os.path.join(UPLOAD_FOLDER, filename)) and is_image_filename(os.path.join(UPLOAD_FOLDER, filename)):
                try:
                    out_filename = await call_script(filename)
                    return {"file": out_filename}
                except Exception as e:
                    return {"error": str(e)}
    return {"error": "could not process" }

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_FOLDER, filename)  # Replace "your_directory" with the directory containing your files
    return FileResponse(file_path, filename=filename)