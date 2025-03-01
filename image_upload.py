import os
import time
import mimetypes
import boto3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# AWS Credentials and S3 Bucket Configuration
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""
S3_BUCKET_NAME = "cement-live"
S3_FOLDER = "stipa/"  # Folder inside S3 bucket (optional)

# Folder to monitor (including subfolders)
FOLDER_TO_WATCH = r"C:\!Data_S_HD\2025"

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

class ImageUploadHandler(FileSystemEventHandler):
    def on_created(self, event):
        """Triggered when a new file is created anywhere in the folder structure."""
        if event.is_directory:
            return  # Skip new directories

        # Only process image files
        if event.src_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            self.wait_for_stable_file(event.src_path)
            self.upload_to_s3(event.src_path)

    def wait_for_stable_file(self, file_path, timeout=10, interval=1):
        """Waits until the file size is stable before uploading."""
        previous_size = -1
        elapsed_time = 0

        while elapsed_time < timeout:
            try:
                # Get the current file size
                current_size = os.path.getsize(file_path)

                if current_size == previous_size:
                    return  # File size is stable, proceed
                previous_size = current_size

            except FileNotFoundError:
                pass  # Ignore if the file is temporarily unavailable

            time.sleep(interval)
            elapsed_time += interval

    def upload_to_s3(self, file_path):
        """Uploads the image to S3 while keeping the subfolder structure."""
        try:
            # Extract relative path from main folder
            relative_path = os.path.relpath(file_path, FOLDER_TO_WATCH)
            s3_key = f"{S3_FOLDER}{relative_path.replace('\\', '/')}"

            print(f"Uploading {relative_path} to S3...")

            # Detect correct Content-Type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "image/jpeg"  # Default to JPEG if unknown

            # Upload file without ACL
            s3_client.upload_file(
                file_path, 
                S3_BUCKET_NAME, 
                s3_key,
                ExtraArgs={"ContentType": content_type}  # No ACL!
            )

            print(f"Uploaded {relative_path} successfully with Content-Type: {content_type}")

        except Exception as e:
            print(f"Error uploading {relative_path}: {e}")

if __name__ == "__main__":
    event_handler = ImageUploadHandler()
    observer = Observer()
    observer.schedule(event_handler, FOLDER_TO_WATCH, recursive=True)  # ✅ Recursive mode enabled

    print(f"Monitoring folder (including subfolders): {FOLDER_TO_WATCH}")
    
    observer.start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()