import boto3
import json
import os
import urllib.parse  # ✅ For URL encoding

# AWS Profile
AWS_PROFILE = "NEWAWSACCOUNT"
os.environ["AWS_PROFILE"] = AWS_PROFILE

# Initialize AWS session
session = boto3.Session(profile_name=AWS_PROFILE)
s3 = session.client("s3")

# Configuration
BUCKET_NAME = "cement-live"
PREFIX = "stipa/"  # ✅ Root folder where images are stored
IMAGE_LIST_PATH = "stipa/image-list.json"  # ✅ Now inside `stipa/`
MAX_IMAGES = 36
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

def list_all_images():
    """ Recursively list all images inside subfolders. """
    all_images = []
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
        if "Contents" in page:
            for obj in page["Contents"]:
                file_key = obj["Key"]
                # Check if file is an image
                if file_key.split(".")[-1].lower() in ALLOWED_EXTENSIONS:
                    all_images.append(file_key)

    # Sort images by filename (assuming timestamps are in filenames)
    all_images.sort(reverse=True, key=lambda x: x.split("/")[-1])  # Latest files first
    return all_images

def update_image_list():
    """ Fetch existing JSON file, add only new images while keeping the latest MAX_IMAGES. """
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=IMAGE_LIST_PATH)
        existing_data = json.loads(response["Body"].read().decode("utf-8"))
        existing_images = existing_data.get("images", [])
    except s3.exceptions.NoSuchKey:
        print("No existing image-list.json found, creating a new one.")
        existing_images = []

    # Get all images from subfolders
    new_images = list_all_images()

    # Only add new images to the list
    for img in new_images:
        encoded_img = urllib.parse.quote(img, safe="/")  # ✅ Encode special characters
        if encoded_img not in existing_images:
            existing_images.insert(0, encoded_img)

    # Keep only the latest MAX_IMAGES
    existing_images = existing_images[:MAX_IMAGES]

    # Save updated list to JSON
    json_data = json.dumps({"images": existing_images}, indent=2)

    # Upload updated image list to S3 inside `stipa/`
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=IMAGE_LIST_PATH,
        Body=json_data,
        ContentType="application/json"
    )

    print(f"✅ Updated {IMAGE_LIST_PATH} with {len(existing_images)} images.")

if __name__ == "__main__":
    update_image_list()