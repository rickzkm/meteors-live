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

# S3 Configuration
BUCKET_NAME = "cement-live"
PREFIXES = ["stipa/", "WFNE/", "WFSE/", "WFNW/", "WFSW/"]  # ✅ Root folders for different cameras
IMAGE_LIST_PATH = "metadata/image-list.json"  # ✅ Now inside `metadata/`
MAX_IMAGES = 1000
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

def fetch_existing_image_list():
    """ Fetch the existing JSON file from S3. """
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=IMAGE_LIST_PATH)
        existing_data = json.loads(response["Body"].read().decode("utf-8"))
        return existing_data.get("images", [])
    except s3.exceptions.NoSuchKey:
        print("No existing image-list.json found, creating a new one.")
        return []

def list_new_images(existing_images):
    """ Fetch only new images from S3 and return a combined list. """
    all_images = set(existing_images)  # Convert existing list to set for fast lookup
    new_images = []

    paginator = s3.get_paginator("list_objects_v2")

    for prefix in PREFIXES:
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    file_key = obj["Key"]
                    if file_key.split(".")[-1].lower() in ALLOWED_EXTENSIONS:
                        encoded_img = urllib.parse.quote(file_key, safe="/")
                        if encoded_img not in all_images:  # Only add new images
                            new_images.append(encoded_img)

    # Sort to keep latest images first
    new_images.sort(reverse=True)

    # Combine and limit to MAX_IMAGES
    updated_images = new_images + existing_images
    return updated_images[:MAX_IMAGES]  # Keep only the latest MAX_IMAGES

def update_image_list():
    """ Fetch existing JSON, append only new images, and save the latest MAX_IMAGES. """
    existing_images = fetch_existing_image_list()
    updated_images = list_new_images(existing_images)

    # Save updated list to JSON
    json_data = json.dumps({"images": updated_images}, indent=2)

    # Upload updated image list to S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=IMAGE_LIST_PATH,
        Body=json_data,
        ContentType="application/json"
    )

    print(f"✅ Updated {IMAGE_LIST_PATH} with {len(updated_images)} images.")

    return {"statusCode": 200, "body": "image-list.json updated"}

def lambda_handler(event, context):
    """ AWS Lambda handler """
    update_image_list()
    return {"statusCode": 200, "body": "Lambda executed successfully"}
