
import requests


class NexusClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.token = None

    def login(self, email, password):
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        self.token = data.get("token")

        if not self.token:
            raise ValueError("Login response did not contain an authentication token.")

        return data

    def request(self, method, endpoint, **kwargs):
        headers = kwargs.pop("headers", {}).copy()

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = requests.request(
            method,
            f"{self.base_url}{endpoint}",
            headers=headers,
            timeout=60,
            **kwargs,
        )

        response.raise_for_status()
        return response.json() if response.content else {}

    def download(self, endpoint, destination):
        headers = {}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = requests.get(
            f"{self.base_url}{endpoint}",
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()

        with open(destination, "wb") as file:
            file.write(response.content)

        return destination
