import os
import requests


def UploadVideo(server_url: str, video_path: str, company_name: str) -> str:
    """Uploads a video file to the server and returns its URL."""
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    endpoint = f"{server_url.rstrip('/')}/upload"
    filename = os.path.basename(video_path)

    with open(video_path, "rb") as f:
        files = {"file": (filename, f, "video/webm")}
        data = {"company_name": company_name}
        response = requests.post(endpoint, files=files, data=data, timeout=60)

    response.raise_for_status()
    payload = response.json()
    return payload["video_url"]


def GetVideoURL(server_url: str, company_name: str) -> str:
    """Returns the video URL for the given company name."""
    endpoint = f"{server_url.rstrip('/')}/get_video_url"
    response = requests.get(endpoint, params={"company_name": company_name}, timeout=15)
    response.raise_for_status()
    payload = response.json()
    return payload["video_url"]
