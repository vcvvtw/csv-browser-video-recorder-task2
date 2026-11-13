import argparse
import csv
import os
import sys
import time
import qscript

DEFAULT_CSV_PATH = "input.csv"


def get_field(row, *possible_keys, default=""):
    """Fetch field value with fallback for whitespace variations in headers."""
    for key in possible_keys:
        if key in row and row[key] is not None:
            return str(row[key]).strip()
        for actual_k, v in row.items():
            if actual_k and actual_k.strip() == key.strip() and v is not None:
                return str(v).strip()
    return default


def preview_video(video_url: str, view_seconds: int):
    """Opens Chromium to preview the uploaded video, holding for view_seconds or until Enter."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.goto(video_url, wait_until="domcontentloaded")

        # Ensure video autoplays in browser preview
        try:
            page.evaluate("""() => {
                const v = document.querySelector('video');
                if (v) { v.muted = true; v.play().catch(() => {}); }
            }""")
        except Exception:
            pass

        if view_seconds > 0:
            time.sleep(view_seconds)
        else:
            try:
                input("Previewing video in browser. Press Enter to continue batch...")
            except EOFError:
                time.sleep(3)

        context.close()
        browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="CSV-driven browser automation video recorder with optional upload and preview."
    )
    parser.add_argument(
        "--server",
        type=str,
        default=None,
        help="Web service base URL (e.g. http://127.0.0.1:8000). If omitted, upload and preview are skipped."
    )
    parser.add_argument(
        "--view-seconds",
        type=int,
        default=5,
        help="Preview duration in seconds (>0 for timeout, 0 to keep browser open until Enter is pressed)."
    )
    parser.add_argument(
        "--video-dir",
        type=str,
        default="./video",
        help="Directory where recorded videos are saved (default: ./video)."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=DEFAULT_CSV_PATH,
        help="Path to input CSV file (default: input.csv)."
    )
    args = parser.parse_args()

    qscript.PATH_TO_VIDEO_FOLDER = args.video_dir

    upload_func = None
    if args.server:
        # Lazy import of HTTP client
        from video_client import UploadVideo
        upload_func = UploadVideo

    if not os.path.exists(args.csv):
        sys.stderr.write(f"Error: CSV file not found at {args.csv}\n")
        sys.exit(1)

    # Handle UTF-8 with or without BOM
    with open(args.csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        for row in reader:
            url = get_field(row, "URL")
            company_name = get_field(row, "Company Name")
            language = get_field(row, "Language")
            country = get_field(row, "Country")
            postcode = get_field(row, "Postcode")
            city = get_field(row, "City")
            street = get_field(row, "Street")
            house_no = get_field(row, "HouseNo")

            video_path = qscript.CaptureVideo_Magento(
                url=url,
                company_name=company_name,
                language=language,
                country=country,
                postcode=postcode,
                city=city,
                street=street,
                house_no=house_no,
            )
            print(video_path)

            if upload_func and video_path:
                try:
                    video_url = upload_func(args.server, video_path, company_name)
                    print(f"Uploaded video URL: {video_url}")
                    preview_video(video_url, args.view_seconds)
                except Exception as err:
                    sys.stderr.write(
                        f"Upload or preview failed for '{company_name}': {err}\n"
                    )


if __name__ == "__main__":
    main()
