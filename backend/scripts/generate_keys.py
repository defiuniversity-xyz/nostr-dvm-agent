#!/usr/bin/env python3
"""Generate a new Nostr keypair for the DVM agent."""

from nostr_sdk import Keys


def main() -> None:
    keys = Keys.generate()
    print("Generated new Nostr keypair for your DVM agent:\n")
    print(f"  Public key (hex):  {keys.public_key().to_hex()}")
    print(f"  Public key (npub): {keys.public_key().to_bech32()}")
    print(f"  Secret key (nsec): {keys.secret_key().to_bech32()}")
    print()
    print("Add the secret key to your backend/.env file:")
    print(f"  NOSTR_PRIVATE_KEY={keys.secret_key().to_bech32()}")
    print()
    print("Add the public key to your frontend/.env file:")
    print(f"  VITE_DVM_PUBKEY={keys.public_key().to_bech32()}")


if __name__ == "__main__":
    main()
