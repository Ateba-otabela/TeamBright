import httpx
from urllib.parse import quote


class FapshiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        definitive: bool = False,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.definitive = definitive
        self.status_code = status_code


class FapshiClient:
    def __init__(
        self,
        api_user: str,
        api_key: str,
        api_url: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_user = api_user
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.transport = transport

    def initiate_payment(self, payload: dict) -> dict:
        response = self._request("POST", "/initiate-pay", json=payload)
        if not isinstance(response, dict):
            raise FapshiError("Fapshi returned an invalid payment response")
        return response

    def get_payment_status(self, trans_id: str) -> dict:
        response = self._request(
            "GET", f"/payment-status/{quote(trans_id, safe='')}"
        )
        if not isinstance(response, dict):
            raise FapshiError("Fapshi returned an invalid status response")
        return response

    def get_transactions_by_user(self, user_id: str) -> list[dict]:
        response = self._request("GET", f"/transaction/{quote(user_id, safe='')}")
        if not isinstance(response, list) or not all(
            isinstance(item, dict) for item in response
        ):
            raise FapshiError("Fapshi returned an invalid transaction list")
        return response

    def expire_payment(self, trans_id: str) -> dict:
        response = self._request("POST", "/expire-pay", json={"transId": trans_id})
        if not isinstance(response, dict):
            raise FapshiError("Fapshi returned an invalid expiration response")
        return response

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
    ) -> dict | list:
        try:
            with httpx.Client(timeout=20, transport=self.transport) as client:
                response = client.request(
                    method,
                    f"{self.api_url}{path}",
                    headers={
                        "apiuser": self.api_user,
                        "apikey": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=json,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise FapshiError(
                "Fapshi rejected the request",
                definitive=status_code in {400, 401, 403, 404, 422, 429},
                status_code=status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise FapshiError("Could not reach Fapshi") from exc
        except ValueError as exc:
            raise FapshiError("Fapshi returned an invalid response") from exc

        if not isinstance(payload, (dict, list)):
            raise FapshiError("Fapshi returned an invalid response")
        return payload
