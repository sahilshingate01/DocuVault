
import argparse
import getpass
import json
from pathlib import Path

import requests
from nexus_cli.client import NexusClient


def get_client(args):
    client = NexusClient(args.url)
    email = args.email or input("Email: ")
    password = getpass.getpass("Password: ")
    client.login(email, password)
    return client


def show(data):
    print(json.dumps(data, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        prog="docuvault",
        description="Manage DocuVault documents from your terminal."
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--email")

    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="Search accessible documents")

    upload = commands.add_parser("upload", help="Upload a new document")
    upload.add_argument("file")
    upload.add_argument("--title", required=True)
    upload.add_argument("--number", required=True)
    upload.add_argument("--workspace", required=True)
    upload.add_argument("--classification", default="UNCLASSIFIED")
    upload.add_argument("--description", default="")

    update = commands.add_parser("upload-version", help="Upload a new document version")
    update.add_argument("document_id")
    update.add_argument("file")
    update.add_argument("--summary", default="Updated version")

    download = commands.add_parser("download", help="Download a document version")
    download.add_argument("document_id")
    download.add_argument("--version", type=int, default=1)
    download.add_argument("--output", required=True)

    verify = commands.add_parser("verify", help="Verify document integrity")
    verify.add_argument("document_id")
    verify.add_argument("--version", type=int, default=1)

    versions = commands.add_parser("versions", help="Show version history")
    versions.add_argument("document_id")

    args = parser.parse_args()

    try:
        client = get_client(args)

        if args.command == "list":
            show(client.request("GET", "/api/v1/search"))

        elif args.command == "upload":
            path = Path(args.file)
            if not path.is_file():
                raise FileNotFoundError(f"File not found: {path}")

            with path.open("rb") as file:
                result = client.request(
                    "POST",
                    "/api/v1/documents/upload",
                    files={"file": (path.name, file)},
                    data={
                        "title": args.title,
                        "document_number": args.number,
                        "workspace_id": args.workspace,
                        "classification": args.classification,
                        "description": args.description,
                        "tags_json": "[]",
                    },
                )
            show(result)

        elif args.command == "upload-version":
            path = Path(args.file)
            if not path.is_file():
                raise FileNotFoundError(f"File not found: {path}")

            with path.open("rb") as file:
                result = client.request(
                    "POST",
                    f"/api/v1/documents/{args.document_id}/versions",
                    files={"file": (path.name, file)},
                    data={"change_summary": args.summary},
                )
            show(result)

        elif args.command == "download":
            path = client.download(
                f"/api/v1/documents/{args.document_id}/versions/"
                f"{args.version}/download",
                args.output,
            )
            print(f"Downloaded: {path}")

        elif args.command == "verify":
            result = client.request(
                "GET",
                f"/api/v1/documents/{args.document_id}/versions/"
                f"{args.version}/verify",
            )
            show(result)
            print("Integrity check:", "PASSED" if result.get("is_intact") else "FAILED")

        elif args.command == "versions":
            result = client.request(
                "GET",
                f"/api/v1/documents/{args.document_id}",
            )
            show(result.get("versions", result))

    except requests.exceptions.ConnectionError:
        print("Cannot connect. Make sure the backend is running.")
        raise SystemExit(1)
    except requests.exceptions.HTTPError as error:
        print(f"API error: {error}")
        if error.response is not None:
            print(error.response.text)
        raise SystemExit(1)
    except Exception as error:
        print(f"Error: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
