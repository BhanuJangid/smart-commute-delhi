# Optional patches

`0001-update-fare-slabs-aug-2025.patch` updates the C++ engine's fare slabs to DMRC's 25 August 2025 revision
(Rs 11 / 21 / 32 / 43 / 54 / 64). It is optional and not applied by default. Apply it with:

```bash
git apply patches/0001-update-fare-slabs-aug-2025.patch
make
```

The engine still estimates distance as about 1.2 km per hop, so the fare stays an estimate.
