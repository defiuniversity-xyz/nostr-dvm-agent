from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    nostr_private_key: str = Field(description="Nostr private key (nsec or hex)")

    gemini_api_key: str = Field(description="Google Gemini API key")

    lightning_address: str = Field(
        default="defiuniversity@strike.me",
        description="Lightning address for receiving payments",
    )
    strike_api_key: str = Field(default="", description="Strike API key for payment verification")

    relay_urls: list[str] = Field(
        default=["wss://relay.damus.io", "wss://nos.lol", "wss://relay.nostr.band"],
        description="Nostr relay WebSocket URLs",
    )

    default_cost_msats: int = Field(default=1000, description="Default cost in millisatoshis")
    cost_text_generation_msats: int = Field(default=500)
    cost_image_generation_msats: int = Field(default=2000)
    cost_translation_msats: int = Field(default=300)
    cost_summarization_msats: int = Field(default=400)
    cost_text_extraction_msats: int = Field(default=200)

    payment_timeout_secs: int = Field(default=300, description="Seconds to wait for payment")
    log_level: str = Field(default="INFO")
    db_path: str = Field(default="dvm_agent.db")

    @property
    def ln_address_user(self) -> str:
        return self.lightning_address.split("@")[0]

    @property
    def ln_address_domain(self) -> str:
        return self.lightning_address.split("@")[1]

    @property
    def lnurlp_url(self) -> str:
        return f"https://{self.ln_address_domain}/.well-known/lnurlp/{self.ln_address_user}"

    def cost_for_kind(self, kind: int) -> int:
        mapping = {
            5000: self.cost_translation_msats,
            5001: self.cost_text_generation_msats,
            5002: self.cost_text_extraction_msats,
            5100: self.cost_image_generation_msats,
        }
        return mapping.get(kind, self.default_cost_msats)
