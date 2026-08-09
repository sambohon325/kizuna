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

Policy changes do not delete or move files immediately. A future transfer queue will execute those decisions. Server cleanup must require the requested number of checksum-matching original replicas first. This protects projects from an offline, replaced, or failed workstation.

## Current transition state

Existing generators and renderers still write their original output to the server. The residency index now catalogs those files and produces lightweight image thumbnails. Hive companions can register verified local copies. The next scheduling work will use this index to place render and AI jobs near their inputs, transfer only necessary source files, and safely evict redundant server originals.
