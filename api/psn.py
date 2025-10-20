import os
import discord
import aiohttp
import json
import re
import secrets
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from psnawp_api import PSNAWP
from psnawp_api.core.psnawp_exceptions import PSNAWPNotFoundError as PSNAWPNotFound
from api.common import APIError

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

class PSNOperation(Enum):
    CHECK_AVATAR = 1
    ADD_TO_CART = 2
    REMOVE_FROM_CART = 3

@dataclass
class PSNRequest:
    region: str
    product_id: str
    pdccws_p: str | None = None
    npsso: str | None = None
    requested_by: str | None = None

class PSN:
    def __init__(self, npsso: str | None, default_pdc: str | None = None, env_path: str | Path | None = None):
        self.psnawp = None
        if npsso:
            try:
                self.psnawp = PSNAWP(npsso)
            except Exception:  # pragma: no cover - psnawp handles its own logging
                print("[psn] Failed to initialize PSNAWP with provided NPSSO; account lookups disabled.")

        self._fallback_pdc = default_pdc or os.getenv("PDC") or None
        self.env_path = Path(env_path).resolve() if env_path else None

        # for request
        self.url = ""
        self.headers = {}
        self.data_json = {}

        # for response
        self.res = {}

    @staticmethod
    def validate_request(req: PSNRequest):
        if req.product_id.count("-") != 2:
            raise APIError("Invalid product ID!")
    
    @staticmethod
    def _format_region_path(region: str) -> str:
        lang, sep, country = region.partition("-")
        if sep:
            return f"{country}/{lang}"
        return region.replace("-", "/")

    def _resolve_credentials(self, request: PSNRequest) -> tuple[str, str]:
        cookie_value = request.pdccws_p or self._read_env_cookie()
        npsso_value = request.npsso or self._generate_npsso()

        if request.pdccws_p:
            actor = request.requested_by or "manual override"
            print(f"[psn] Generated NPSSO for {actor}: {npsso_value}")

        if not cookie_value:
            raise APIError(
                "Missing pdccws_p cookie. Provide it in the command or set PDC in .env.",
                code="auth",
                hints={"cookie": True, "npsso": False},
            )

        return cookie_value, npsso_value

    def _read_env_cookie(self) -> str | None:
        if self.env_path and self.env_path.exists():
            load_dotenv(self.env_path, override=True)
            value = os.getenv("PDC")
            if value:
                return value
        return self._fallback_pdc

    @staticmethod
    def _generate_npsso() -> str:
        return secrets.token_hex(32)

    @staticmethod
    def _classify_auth_components(message: str | None, status: int | None = None) -> tuple[bool, bool]:
        if not message:
            # fall back to status-based hints
            if status in {401, 403}:
                return True, True
            return True, True

        lowered = message.lower()
        cookie_keywords = (
            "cookie",
            "pdccws",
            "session",
            "aka_a2",
            "gpdc",
            "pdc",
            "pdccws_p",
            "signin cookie",
            "access denied",
            "authorised",
            "unauthorized",
            "missing access",
            "forbidden",
        )
        npsso_keywords = (
            "npsso",
            "userinfo",
            "token",
            "authentication",
            "auth token",
            "credential",
            "login",
            "sign in",
            "oauth",
        )

        cookie = any(keyword in lowered for keyword in cookie_keywords)
        npsso = any(keyword in lowered for keyword in npsso_keywords)

        if not cookie and not npsso:
            if status in {401, 403}:
                return True, True
            return False, False

        if status in {401, 403}:
            return True, True

        return cookie, npsso

    @staticmethod
    def _looks_like_auth_error(message: str | None) -> bool:
        if not message:
            return False
        cookie, npsso = PSN._classify_auth_components(message, None)
        if cookie or npsso:
            return True
        lowered = message.lower()
        keywords = (
            "access denied",
            "unauthorized",
            "authorised",
            "missing access",
            "forbidden",
        )
        return any(keyword in lowered for keyword in keywords)

    async def _read_json(self, response: aiohttp.ClientResponse) -> dict:
        text = await response.text()

        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError as exc:
            raise APIError("Unexpected response from PlayStation API.", code=None) from exc

        if response.status >= 400:
            message = None
            if isinstance(data, dict):
                message = data.get("message") or data.get("error") or data.get("cause")
                if not message and data.get("errors"):
                    first = data["errors"][0]
                    if isinstance(first, dict):
                        message = first.get("message") or first.get("detail")
            if not message:
                message = f"PlayStation API returned status {response.status}."
            cookie_hint, npsso_hint = self._classify_auth_components(message, response.status)
            hints = {"cookie": cookie_hint, "npsso": npsso_hint}
            code = "auth" if response.status in {401, 403} or self._looks_like_auth_error(message) else None
            raise APIError(message, code=code, hints=hints)

        return data
        
    def get_error_cause(self) -> str:
        return self.res.get("cause")
    
    def get_error(self) -> str | None:
        if "subTotalPrice" in str(self.res):
            return None

        elif self.res.get("errors"):
            return self.res["errors"][0]["message"]
        return None

    def request_builder(self, request: PSNRequest, operation: PSNOperation) -> None:
        region_path = self._format_region_path(request.region)

        match operation:
            case PSNOperation.CHECK_AVATAR:
                self.url = f"https://store.playstation.com/store/api/chihiro/00_09_000/container/{region_path}/19/{request.product_id}/"
                self.headers = {
                "Origin": "https://checkout.playstation.com",
                "content-type": "application/json",
                "Accept-Language": request.region,
                }
                return

        cookie_value, npsso_value = self._resolve_credentials(request)

        match operation:
            case PSNOperation.ADD_TO_CART:
                self.url = "https://web.np.playstation.com/api/graphql/v1/op"
                self.headers = {
                "Origin": "https://checkout.playstation.com",
                "content-type": "application/json",
                "Accept-Language": request.region,
                "Cookie": f"AKA_A2=A; pdccws_p={cookie_value}; isSignedIn=true; userinfo={npsso_value}; p=0; gpdcTg=%5B1%5D"
                }
                self.data_json = {
                    "operationName": "addToCart",
                    "variables": {
                        "skus": [{"skuId": ""}]
                    },
                    "extensions": {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": "93eb198753e06cba3a30ed3a6cd3abc1f1214c11031ffc5b0a5ca6d08c77061f"
                        }
                    }
                }

            case PSNOperation.REMOVE_FROM_CART:
                self.url = "https://web.np.playstation.com/api/graphql/v1/op"
                self.headers = {
                "Origin": "https://checkout.playstation.com",
                "content-type": "application/json",
                "Accept-Language": request.region,
                "Cookie": f"AKA_A2=A; pdccws_p={cookie_value}; isSignedIn=true; userinfo={npsso_value}; p=0; gpdcTg=%5B1%5D"
                }
                self.data_json = {
                    "operationName": "removeFromCart",
                    "variables": {
                        "skuId": ""
                    },
                    "extensions": {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": "55e50c2157c33e84f409d2a52f3bb7c19db62b144fb49e75a1a9b0acad276bba"
                        }
                    }
                }
    
    def insert_skuId_deep(self, skuId: str) -> None:
        self.data_json["variables"]["skus"][0]["skuId"] = skuId
    
    def insert_skuId(self, sku_Id: str) -> None:
        self.data_json["variables"]["skuId"] = sku_Id

    async def check_avatar(self, request: PSNRequest, obtain_skuget_only: bool = False) -> str:
        self.validate_request(request)
        self.request_builder(request, PSNOperation.CHECK_AVATAR)

        async with aiohttp.ClientSession() as session:
            async with session.get(self.url, headers=self.headers) as response:
                self.res = await self._read_json(response)

        sku_get = self.res.get("default_sku", {}).get("id")
        if sku_get is None:
            message = self.get_error_cause() or "Unable to locate the requested avatar."
            cookie_hint, npsso_hint = self._classify_auth_components(message, None)
            code = "auth" if self._looks_like_auth_error(message) else None
            raise APIError(message, code=code, hints={"cookie": cookie_hint, "npsso": npsso_hint})
        if obtain_skuget_only:
            return sku_get
        
        region_path = self._format_region_path(request.region)
        picture_avatar = f"https://store.playstation.com/store/api/chihiro/00_09_000/container/{region_path}/19/{request.product_id}/image"
        return picture_avatar

    async def add_to_cart(self, request: PSNRequest) -> None:
        sku_id = await self.check_avatar(request, obtain_skuget_only=True)
        self.request_builder(request, PSNOperation.ADD_TO_CART)
        self.insert_skuId_deep(sku_id)
            
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=self.headers, json=self.data_json) as response:
                self.res = await self._read_json(response)

        err = self.get_error()
        if err is not None:
            cookie_hint, npsso_hint = self._classify_auth_components(err, None)
            code = "auth" if self._looks_like_auth_error(err) else None
            raise APIError(err, code=code, hints={"cookie": cookie_hint, "npsso": npsso_hint})

    async def remove_from_cart(self, request: PSNRequest) -> None:
        sku_id = await self.check_avatar(request, obtain_skuget_only=True)
        self.request_builder(request, PSNOperation.REMOVE_FROM_CART)
        self.insert_skuId(sku_id)

        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=self.headers, json=self.data_json) as response:
                self.res = await self._read_json(response)

        err = self.get_error()
        if err is not None:
            cookie_hint, npsso_hint = self._classify_auth_components(err, None)
            code = "auth" if self._looks_like_auth_error(err) else None
            raise APIError(err, code=code, hints={"cookie": cookie_hint, "npsso": npsso_hint})

    async def obtain_account_id(self, username: str) -> str:
        if self.psnawp is None:
            raise APIError(
                "NPSSO is not configured. Set NPSSO in the environment to enable account lookups.",
                code="auth",
                hints={"cookie": False, "npsso": True},
            )
        if len(username) < 3 or len(username) > 16:
            raise APIError("Invalid username!")
        elif not bool(USERNAME_PATTERN.fullmatch(username)):
            raise APIError("Invalid username!")
        
        try:
            user = self.psnawp.user(online_id=username)
        except PSNAWPNotFound:
            raise APIError("User not found!")
        
        user_id = hex(int(user.account_id)) # convert decimal to hex
        user_id = user_id[2:] # remove 0x
        user_id = user_id.zfill(16) # pad to 16 length with zeros
        return user_id
