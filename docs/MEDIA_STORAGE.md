# Metadata-first media storage

Kizuna separates the production's creative record from its large media files. The server database remains the source of truth for story structure, characters, worlds, shots, edit decisions, approvals, lineage, checksums, and file locations. Lightweight thumbnails and editing proxies can stay in Kizuna so the production remains understandable even when a computer holding an original is offline.

## Media residency index

Every indexed asset has a stable asset key and one or more residency records. A residency describes:

- representation: original, proxy, or thumbnail;
- location: Kizuna server, Hive computer, S3-compatible vault, or an external source;
- checksum and byte size;
- availability state and last verification time; and
- an opaque vault object reference for Hive media.

Kizuna Node reports only files inside its dedicated Kizuna vault. It sends an opaque `vault://` object reference, checksum, size, and status—not an inventory of personal folders or a browsable filesystem path. The API rejects ordinary filesystem paths for Hive residency records.

## Storage policy

Each production can choose whether new originals should ultimately live on the Kizuna server, Hive computers, or S3-compatible storage. It can also select a preferred Hive computer, thumbnail and editing-proxy sizes, the number of verified replicas required, and whether server originals may be removed after replication.

Policy changes do not delete or move files immediately. The creator explicitly queues missing copies from the Production Vault. Server cleanup must require the requested number of checksum-matching original replicas first. This protects projects from an offline, replaced, or failed workstation.

## Automatic working media

Completed character, background, storyboard, composition, motion, voice, audio, animatic, and master outputs are registered with the residency index immediately. Kizuna produces lightweight JPEG image proxies, H.264 video proxies, and AAC audio proxies when the production policy keeps server proxies. Proxy conversion failure does not replace or modify the original.

The original and each working representation receive independent checksums and locations. Opening the Production Vault is no longer required to discover newly created media.

## Verified Hive transfers

The transfer queue assigns each original to a specific Hive computer and honors that device's pause, drain, schedule, concurrency, CPU, GPU, RAM, and allowed-work settings. A node leases one job at a time, streams the original into a temporary file, verifies its SHA-256 checksum and byte size, and only then atomically moves it into the local vault. Interrupted leases return to the queue and retry up to five times.

Each local vault has a small `vault_index.json` mapping opaque Kizuna object references to files inside that dedicated vault. Actual device paths are not sent back to the server. The companion can use a custom vault folder through `--vault` or `KIZUNA_VAULT_PATH`.

Existing generators and renderers still write their first original output to the server. The queue replicates those originals to Hive storage and marks assets eligible for cleanup only when checksum-matching reports are newer than the configured verification window. The Production Vault has a separate cleanup review where the creator may approve or revoke each eligible original. A changed checksum or stale/insufficient replica state invalidates approval.

Automatic server deletion remains disabled. Cleanup approval is a recorded decision for a future guarded cleanup executor; it does not remove the source file.
