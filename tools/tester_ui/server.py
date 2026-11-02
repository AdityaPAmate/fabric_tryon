"""Local development server for the Fabric Try-on Tester UI.

It serves the static UI, saves Cloudinary output images, and stores
self-contained testing feedback reports under the reports directory.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import shutil
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT / "outputs"
REPORTS_DIR = ROOT / "reports"
ALLOWED_IMAGE_HOST_SUFFIX = ".cloudinary.com"
EXTENSIONS = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp", "avif": "avif"}


def next_output_path(extension: str) -> Path:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    highest = 0
    for file_path in OUTPUTS_DIR.glob("generated_*.*"):
        match = re.fullmatch(r"generated_(\d+)\.[a-z0-9]+", file_path.name, re.IGNORECASE)
        if match:
            highest = max(highest, int(match.group(1)))
    return OUTPUTS_DIR / f"generated_{highest + 1:04d}.{extension}"


def is_cloudinary_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.hostname.endswith(ALLOWED_IMAGE_HOST_SUFFIX)


def save_data_url(image_data: dict | None, destination_dir: Path, base_name: str) -> dict | None:
    if not image_data:
        return None
    data_url = str(image_data.get("data_url", ""))
    original_name = Path(str(image_data.get("name", "image"))).name
    match = re.fullmatch(r"data:([^;]+);base64,(.+)", data_url, re.DOTALL)
    if not match:
        raise ValueError(f"{base_name} is not a valid image data URL.")
    mime_type, encoded = match.groups()
    extension = EXTENSIONS.get(mime_type.split("/")[-1].lower(), "jpg")
    destination = destination_dir / f"{base_name}.{extension}"
    destination.write_bytes(base64.b64decode(encoded, validate=True))
    return {"original_name": original_name, "saved_path": destination.name, "mime_type": mime_type}


def next_report_dir(garment_type: str) -> Path:
    safe_garment_type = re.sub(r"[^a-z0-9_-]", "_", garment_type.lower()) or "unknown"
    garment_dir = REPORTS_DIR / safe_garment_type
    garment_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S")
    sequence = 1
    while (garment_dir / f"{stamp}_{sequence:03d}").exists():
        sequence += 1
    report_dir = garment_dir / f"{stamp}_{sequence:03d}"
    report_dir.mkdir()
    return report_dir


def save_catalog_outputs(catalog: dict | None, report_dir: Path) -> dict | None:
    """Keep every successful view and failed-view diagnostic in the report set."""
    if not catalog:
        return None
    saved = dict(catalog)
    saved['images'] = []
    directory = report_dir / 'catalog_images'
    directory.mkdir()
    for index, image in enumerate(catalog.get('images', []), 1):
        item = dict(image)
        view = re.sub(r'[^a-z0-9_-]', '_', str(image.get('view', 'image')).lower())
        extension = EXTENSIONS.get(str(image.get('format', 'jpg')).lower(), 'jpg')
        destination = directory / f'{index:02d}_{view}.{extension}'
        item['report_output_path'] = None
        item['copy_error'] = None
        try:
            local = image.get('local_output_path')
            source = (ROOT / str(local)).resolve() if local else None
            if source and source.is_file() and OUTPUTS_DIR.resolve() in source.parents:
                shutil.copy2(source, destination)
            elif is_cloudinary_url(str(image.get('url', ''))):
                with urlopen(Request(image['url'], headers={'User-Agent': 'Fabric-Tryon-Tester/1.0'}), timeout=60) as remote:
                    destination.write_bytes(remote.read())
            else:
                raise ValueError('No saved local image or HTTPS Cloudinary URL available.')
            item['report_output_path'] = str(destination.relative_to(report_dir))
        except Exception as error:
            item['copy_error'] = str(error)
        saved['images'].append(item)
    return saved


class TesterRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path == "/save-output":
            self.save_output()
        elif self.path == "/save-report":
            self.save_report()
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(content_length))

    def save_output(self):
        try:
            payload = self.read_json_body()
            image_url = str(payload["url"])
            if not is_cloudinary_url(image_url):
                raise ValueError("Only HTTPS Cloudinary image URLs can be saved.")
            extension = EXTENSIONS.get(str(payload.get("format", "jpg")).lower(), "jpg")
            destination = next_output_path(extension)
            with urlopen(Request(image_url, headers={"User-Agent": "Fabric-Tryon-Tester/1.0"}), timeout=60) as remote_image:
                destination.write_bytes(remote_image.read())
            self.send_json(HTTPStatus.OK, {"filename": str(destination.relative_to(ROOT))})
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            self.send_json(HTTPStatus.BAD_GATEWAY, {"error": f"Could not save image: {error}"})

    def save_report(self):
        try:
            payload = self.read_json_body()
            issue_text = str(payload.get("issue_text", "")).strip()
            request_data = payload.get("request") or {}
            if not issue_text:
                raise ValueError("Write an issue or observation before saving a report.")
            if not request_data.get("garment_type"):
                raise ValueError("The report is missing garment type information.")

            report_dir = next_report_dir(str(request_data["garment_type"]))
            source_info = save_data_url(payload.get("source"), report_dir, "garment_source")
            person_info = save_data_url(payload.get("person"), report_dir, "person_original")
            face_info = save_data_url(payload.get("face"), report_dir, "face_reference")
            output_data = payload.get("output") or {}
            output_copy = None
            output_save_error = None
            local_output_path = payload.get("local_output_path")
            if local_output_path:
                source_output = (ROOT / str(local_output_path)).resolve()
                if source_output.is_file() and OUTPUTS_DIR.resolve() in source_output.parents:
                    output_copy = report_dir / f"generated_output{source_output.suffix.lower()}"
                    try:
                        shutil.copy2(source_output, output_copy)
                    except Exception as error:
                        output_save_error = str(error)
                        output_copy = None
            if output_copy is None and is_cloudinary_url(str(output_data.get("url", ""))):
                extension = EXTENSIONS.get(str(output_data.get("format", "jpg")).lower(), "jpg")
                output_copy = report_dir / f"generated_output.{extension}"
                try:
                    with urlopen(Request(output_data["url"], headers={"User-Agent": "Fabric-Tryon-Tester/1.0"}), timeout=60) as remote_image:
                        output_copy.write_bytes(remote_image.read())
                    output_save_error = None
                except Exception as error:
                    output_save_error = str(error)
                    output_copy.unlink(missing_ok=True)
                    output_copy = None

            (report_dir / "issue.txt").write_text(issue_text + "\n", encoding="utf-8")
            report_data = {
                "schema_version": 2,
                "report_id": report_dir.name,
                "created_at": datetime.now().astimezone().isoformat(),
                "issue_text": issue_text,
                "generation_error": payload.get("generation_error"),
                "generation_seed": payload.get("generation_seed"),
                "generation": payload.get("generation"),
                "provider_code": payload.get("provider_code"),
                "failure_type": payload.get("failure_type"),
                "http_status": payload.get("http_status"),
                "request_duration_ms": payload.get("request_duration_ms"),
                "request": request_data,
                "catalog": save_catalog_outputs(payload.get('catalog'), report_dir),
                "files": {
                    "garment_source": source_info,
                    "person": person_info,
                    "face_reference": face_info,
                    "generated_output": {
                        "cloudinary_url": output_data.get("url"),
                        "public_id": output_data.get("public_id"),
                        "format": output_data.get("format"),
                        "local_output_path": output_copy.name if output_copy else None,
                        "source_output_path": local_output_path,
                        "copy_error": output_save_error,
                    },
                },
            }
            report_path = str(report_dir.relative_to(ROOT))
            report_data["report_path"] = report_path
            (report_dir / "report.json").write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

            # One easy-to-read JSON file per garment type. Every new report is
            # appended here, while its full self-contained folder remains available.
            aggregate_path = report_dir.parent / "all_reports.json"
            try:
                existing_reports = json.loads(aggregate_path.read_text(encoding="utf-8")) if aggregate_path.exists() else []
            except json.JSONDecodeError:
                existing_reports = []
            if not isinstance(existing_reports, list):
                existing_reports = []
            existing_reports.append(report_data)
            temporary_aggregate = aggregate_path.with_suffix(".json.tmp")
            temporary_aggregate.write_text(json.dumps(existing_reports, indent=2, ensure_ascii=False), encoding="utf-8")
            temporary_aggregate.replace(aggregate_path)

            index_entry = {
                "report_id": report_dir.name,
                "garment_type": request_data["garment_type"],
                "created_at": report_data["created_at"],
                "issue_text": issue_text,
                "report_path": report_path,
                "aggregate_path": str(aggregate_path.relative_to(ROOT)),
                "generation_mode": request_data.get('generation_mode', 'single'),
                "fabric_type": request_data.get('fabric_type', 'unspecified'),
                "catalog_view": request_data.get('catalog_view'),
                "catalog_id": (payload.get('catalog') or {}).get('catalog_id'),
            }
            REPORTS_DIR.mkdir(exist_ok=True)
            with (REPORTS_DIR / "index.jsonl").open("a", encoding="utf-8") as index_file:
                index_file.write(json.dumps(index_entry, ensure_ascii=False) + "\n")
            response_data = {
                "report_path": report_path,
                "aggregate_path": str(aggregate_path.relative_to(ROOT)),
            }
            if output_save_error:
                response_data["warning"] = (
                    "Report and request data were saved, but the generated image "
                    f"could not be copied locally: {output_save_error}"
                )
            self.send_json(HTTPStatus.OK, response_data)
        except (KeyError, ValueError, json.JSONDecodeError, binascii.Error) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            self.send_json(HTTPStatus.BAD_GATEWAY, {"error": f"Could not save report: {error}"})

    def send_json(self, status: HTTPStatus, body: dict):
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5500), TesterRequestHandler)
    print("Fabric Try-on Tester UI: http://localhost:5500")
    print(f"Saved output images: {OUTPUTS_DIR}")
    print(f"Saved testing reports: {REPORTS_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


