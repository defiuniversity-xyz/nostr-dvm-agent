#!/usr/bin/env python3
"""Send a test NIP-90 job request to verify the DVM agent is listening."""

import asyncio
import sys

from nostr_sdk import Client, EventBuilder, Keys, Kind, NostrSigner, Tag, Timestamp


async def main() -> None:
    relay_url = sys.argv[1] if len(sys.argv) > 1 else "wss://relay.damus.io"
    prompt = sys.argv[2] if len(sys.argv) > 2 else "What is Bitcoin in one sentence?"

    keys = Keys.generate()
    signer = NostrSigner.keys(keys)
    client = Client(signer)
    await client.add_relay(relay_url)
    await client.connect()

    print(f"Test client pubkey: {keys.public_key().to_bech32()}")
    print(f"Relay: {relay_url}")
    print(f"Prompt: {prompt}")
    print()

    tags = [
        Tag.parse(["i", prompt, "text"]),
        Tag.parse(["output", "text/plain"]),
    ]
    builder = EventBuilder(Kind(5001), "").tags(tags)
    output = await client.send_event_builder(builder)

    print(f"Job request published!")
    print(f"  Event ID: {output.id().to_hex()}")
    print()
    print("Now listening for Kind 7000 feedback and Kind 6001 results...")
    print("Press Ctrl+C to stop.\n")

    from nostr_sdk import Filter
    feedback_filter = Filter().kind(Kind(7000)).events([output.id()]).since(Timestamp.now())
    result_filter = Filter().kind(Kind(6001)).events([output.id()]).since(Timestamp.now())
    await client.subscribe([feedback_filter, result_filter], None)

    await client.handle_notifications(lambda relay, sub_id, event: handle_event(event))


async def handle_event(event) -> bool:
    kind = event.kind().as_u16()
    content = event.content()[:200]

    if kind == 7000:
        for tag in event.tags().to_vec():
            tv = tag.as_vec()
            if tv and tv[0] == "status":
                print(f"[Feedback] Status: {tv[1]}")
                break
        if content:
            print(f"  Content: {content}")

    elif kind == 6001:
        print(f"[Result] {content}...")

    return False


if __name__ == "__main__":
    asyncio.run(main())
