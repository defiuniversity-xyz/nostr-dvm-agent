from __future__ import annotations

import structlog
from nostr_sdk import Event, Keys, PublicKey, nip44_decrypt, nip44_encrypt

logger = structlog.get_logger()


def is_encrypted(event: Event) -> bool:
    """Check if a NIP-90 job request has an 'encrypted' tag."""
    for tag in event.tags().to_vec():
        tag_vec = tag.as_vec()
        if tag_vec and tag_vec[0] == "encrypted":
            return True
    return False


def decrypt_content(keys: Keys, sender_pubkey: PublicKey, ciphertext: str) -> str | None:
    """Decrypt NIP-44 v2 encrypted content using ECDH shared secret."""
    try:
        plaintext = nip44_decrypt(keys.secret_key(), sender_pubkey, ciphertext)
        logger.debug("nip44_decrypted", plaintext_len=len(plaintext))
        return plaintext
    except Exception:
        logger.exception("nip44_decrypt_failed")
        return None


def encrypt_content(keys: Keys, recipient_pubkey: PublicKey, plaintext: str) -> str | None:
    """Encrypt content using NIP-44 v2 for the recipient."""
    try:
        ciphertext = nip44_encrypt(keys.secret_key(), recipient_pubkey, plaintext)
        logger.debug("nip44_encrypted", ciphertext_len=len(ciphertext))
        return ciphertext
    except Exception:
        logger.exception("nip44_encrypt_failed")
        return None
