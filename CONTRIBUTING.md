# Contributing

This draft is not yet open for public contributions. Once the release is approved, contributions are welcome within the safety and licensing boundaries of this project.

## Rules

1. **Licensing & Provenance:** Kernel patches, DTS, and kernel modules must retain their applicable SPDX headers and upstream attribution. MIT for independently authored userspace/TUI/artwork is proposed pending owner approval. Do not contribute third-party code without verified provenance and permission.
2. **No Proprietary Blobs or PII:** Never commit Samsung/Broadcom firmware, NVRAM, EFS/IMEI dumps, private keys, personal IPs, or absolute local paths.
3. **Hardware Safety:** Do not submit changes that weaken authentication, bypass hardware thermal/battery limits, or write to S-Boot/PIT/EFS/modem partitions.
4. **Honest Testing:** Clearly distinguish offline-verified logic from live-hardware-verified behavior on `SM-G985F`.
