# onearth-import

A CLI that imports an MRF layer into a running local OnEarth
docker-compose stack. One command takes an `.mrf` header (plus its sibling
`.idx` and data file), figures out the rest, and leaves you with a serving
layer and URLs you can hit.

- Detects temporal vs static from the filename datestamp
- Distinguishes plain JPEG from Brunsli by peeking at tile bytes and wires
  up `mod_brunsli`'s `DBRUNSLI` filter when needed
- Warns if the chosen TileMatrixSet doesn't match the MRF's native grid
- Prompts for missing flags when run interactively; in scripts, failures
  are loud instead of silent
- Can stitch an entire level of tiles into one image, and optionally diff
  that against a direct-from-MRF render to validate the serving chain
  (works for JPEG and Brunsli payloads)

## Install

Python 3.12+ and a Docker daemon are required. From this directory:

```bash
pipx install .
# or, without pipx:
python3 -m pip install .
```

Dependencies: PyYAML, Pillow — pulled in automatically.

## Prerequisites

The stack must be running. From the repo root:

```bash
cd /path/to/onearth
source docker/set_env_vars_docker_compose.sh
docker compose -f docker/docker-compose.yml up -d
```

Wait for `onearth-tile-services`, `onearth-capabilities`, and
`onearth-time-service` to go healthy (`docker ps`). All three are required
for temporal layers; static layers only need the first two.

### Environment variables

The CLI reads the same routing env vars the stack uses, so URLs it
constructs match how you're actually running things:

| Var | Default | When to set |
|---|---|---|
| `USE_SSL` | `false` | Set to `true` if the stack is serving HTTPS on 443 |
| `SERVER_NAME` | `localhost` | Non-localhost hostnames |
| `ONEARTH_BASE_URL` | (derived from the above) | Fully custom routing (e.g. `http://my-proxy:8080`) |

Example: if your stack runs with `USE_SSL=false` (HTTP on port 80 via
`onearth-demo`), export `USE_SSL=false` before running the CLI so
post-import probes hit the right URL.

## First-time walkthrough

Have an `.mrf` with a sibling `.idx` and data file (`.pjg` / `.ppg` /
`.ptf` / `.pvt` / `.lrc`). Then:

```bash
$ onearth-import add-layer /path/to/my_layer.mrf
```

With no flags, the CLI will prompt you through the missing required
arguments:

```
Which projection endpoint do you want to register into?
   1. EPSG:3031  (profile: all)
   ...
  13. EPSG:4326  (profile: all)
  16. EPSG:4326  (profile: std)
Pick 1-16: 16

Which TileMatrixSet should this layer use? (CRS: EPSG:4326)
   1. 16km  (3 levels)
   2. 2km   (6 levels)
   ...
Pick 1-7: 2

Is this a temporal (time-varying) layer? [Y/n] y
Time config (period string like '2020-01-01/2020-12-31/P1D', or
  'DETECT' to scan idx files) [2020-01-01/2020-01-01/P1D]:
```

The temporal default is derived from a `YYYYDDDHHMMSS` filename stamp when
present. Hit Enter to accept. Output ends with:

```
Checking tile 0/0/0...
  http://localhost/wmts/epsg4326/std/my_layer/default/2020-01-01/2km/0/0/0.jpg
  PASS — HTTP 200, 36258 bytes

URLs:
  REST tile:       http://localhost/wmts/.../my_layer/default/2020-01-01/2km/0/0/0.jpg
  GetCapabilities: http://localhost/wmts/.../1.0.0/WMTSCapabilities.xml

To stitch all tiles into one image:
  onearth-import stitch my_layer --projection EPSG:4326 --tilematrixset 2km
```

Scripted flows still work — pass every required arg explicitly and stdin
non-TTY never hangs on a prompt:

```bash
onearth-import add-layer /path/to/my_layer-2020001000000.mrf \
    --layer-id my_layer \
    --projection EPSG:4326 --profile std \
    --tilematrixset 2km \
    --time-config "2020-01-01/2020-01-01/P1D"
```

## Commands

### `add-layer`

Register a new MRF layer.

```
onearth-import add-layer <mrf> [--layer-id ID] [--title STR]
    [--projection EPSG:NNNN] [--profile std]
    [--tilematrixset NAME]
    [--static | --time-config PERIOD]
```

| Flag | Effect |
|---|---|
| `<mrf>` | Path to the `.mrf` header. Sibling `.idx` + data file located automatically |
| `--layer-id` | Layer ID (defaults to the MRF filename base with any date stamp stripped) |
| `--title` | Human-readable title |
| `--projection` | `EPSG:4326` / `EPSG:3857` / `EPSG:3031` / `EPSG:3413` |
| `--profile` | Endpoint profile (default `std`) |
| `--tilematrixset` | TMS name, e.g. `2km`, `250m`, `GoogleMapsCompatible_Level6` |
| `--static` | Layer has no time dimension |
| `--time-config` | Period string `YYYY-MM-DD/YYYY-MM-DD/P1D` or `DETECT` (see below) |

**What happens end-to-end:**

1. Parse the `.mrf` header for size / page size / bands. Peek at the
   first tile's magic bytes to distinguish JPEG from Brunsli.
2. Refuse up front if the proposed layer ID would collide with an
   existing `MRF_RegExp` in any conf.d/* (mod_mrf regexes are
   unanchored, so `Foo` would match `Foo_Test`).
3. Refuse up front if the proposed projection endpoint YAML doesn't
   exist.
4. Compare the MRF's native tile grid to the chosen TMS. Print a
   warning (not a hard error) when no TMS level matches.
5. `docker cp` `.idx` → `onearth-tile-services:/onearth/idx/{proj}/{layer_id}/`
6. `docker cp` data file + `.mrf` → `onearth-tile-services:/onearth/layers/{proj}/{layer_id}/`
   (files are renamed to `{layer_id}[-datestamp].{ext}` so Apache's
   filename template resolves correctly).
7. Write the layer YAML into **both** `onearth-tile-services` and
   `onearth-capabilities` at
   `/etc/onearth/config/layers/{proj}/{profile}/{layer_id}.yaml`.
8. For temporal layers with an explicit period: seed Redis keys
   `{prefix}layer:{layer_id}:default` and `:periods` in
   `onearth-time-service` (prefix derived from the endpoint's
   `time_service_keys`, e.g. `epsg4326:`).
9. Run `oe2_wmts_configure.py` in tile-services and
   `make_gc_endpoint.lua` in capabilities against the endpoint YAML.
10. `httpd -k graceful` in both containers.
11. Fetch tile `0/0/0` and report PASS/FAIL.

### `stitch`

Fetch all tiles at a chosen TMS level and compose them into one image.

```
onearth-import stitch <layer-id> --projection EPSG:NNNN
    [--profile NAME] --tilematrixset NAME
    [--level N] [--date YYYY-MM-DD] [--out PATH]
    [--max-tiles N] [--diff]
```

Without `--level`, it lists the available levels and (on a TTY) prompts
you to pick one:

```
$ onearth-import stitch my_layer --projection EPSG:4326 --tilematrixset 2km
Available levels for layer 'my_layer' in 2km:
  level 0: 2 × 1 tiles  →  1024 × 512 px
  level 1: 3 × 2 tiles  →  1536 × 1024 px
  level 2: 5 × 3 tiles  →  2560 × 1536 px

Pick a level to stitch:
   1. level 0  (2 tiles, 1024×512 px)
   2. level 1  (6 tiles, 1536×1024 px)
   3. level 2  (15 tiles, 2560×1536 px)  (default)
Pick 1-3 [3]:
```

Alpha is preserved for PNG layers (RGBA canvas; transparent regions
stay transparent, not flattened black).

Omit `--profile` and the layer's profile is auto-detected under
`/etc/onearth/config/layers/{proj}/*/`.

#### `--diff`

```
onearth-import stitch my_layer --projection EPSG:4326 --tilematrixset 2km \
    --level 2 --out /tmp/mylayer --diff
```

Produces three files:

- `<prefix>-served.<ext>` — HTTP stitch (what the server produces)
- `<prefix>-source.<ext>` — direct-from-MRF render, bypassing Apache
- `<prefix>-diff.png` — grayscale per-pixel absolute difference

Reports mean / max per-channel delta and % of pixels that differ. A
healthy JPEG pipeline shows mean < 5, max < ~40; PNG (lossless) should
show mean ≈ 0. Brunsli layers use `libbrunslidec-c` inside the container
to decode source tiles before the comparison.

`--diff` refuses with a clear error for payload variants with no
available decoder (e.g. ZenJPEG once we know its magic bytes; until
then it falls into `UNKNOWN_JPEG_VARIANT` and is blocked).

### `verify`

```
onearth-import verify <layer-id> --projection EPSG:NNNN [--profile NAME]
    --tilematrixset NAME
```

Probes `0/0/0.jpg` then `.png`, coarsest then one up, reports the first
that returns 200. Auto-detects the profile when omitted.

### `list`

```
onearth-import list
```

Every layer YAML currently under `/etc/onearth/config/layers/` in
tile-services, grouped by `projection/profile`.

### `remove`

```
onearth-import remove <layer-id> --projection EPSG:NNNN --profile NAME
```

Deletes the MRF files, layer YAML (both containers), and Redis entries,
then regenerates configs and graceful-reloads Apache. Always pass
`--profile` explicitly for destructive ops.

### `doctor`

```
onearth-import doctor
```

- Reports which of the three containers is running.
- Repairs `tilematrixsets.xml` if it's missing (the file isn't in
  `sample_configs/conf/`; the authoritative copy lives in the gc_service
  module source inside the image — doctor copies it into place).
- Probes the front door to confirm Apache is reachable at `_base_url()`.

## How the tool talks to the stack

- **Writes** run as root in the container (`docker exec -u 0`), so
  `docker cp`-owned files (foreign uid) can be chmod'd to 0644 and the
  services (running as `www-data`/`apache`) can read them.
- **Apache reload** uses `httpd -k graceful` (SIGUSR1), not
  `-k restart` — the latter was spawning stale parent processes in
  this container and leaving old configs loaded.
- **URLs** are built from `USE_SSL` / `SERVER_NAME` env vars (or
  `ONEARTH_BASE_URL` override), so probe URLs match however you're
  actually accessing the stack.
- **Temporal URLs** use the layer's explicit default date (from the
  time-config or Redis), not the `default` keyword — the time service's
  default-keyword handling is unreliable for freshly-seeded layers.

## Troubleshooting

**`No space left on device` during `add-layer`.** The tile-services
container's writable layer fills up over repeated imports because
`docker cp`'d files live in the overlay and aren't reclaimed by `rm`
inside the container. `onearth-import remove` doesn't help. Recreate
the container (`docker compose down && docker compose up -d`), which
also wipes all imported layers — see DEFERRED.md for the bind-mount
plan that fixes this.

**Post-import PASS but stitch says "no tiles served".** Usually means
the wrong TMS is being consulted for URL construction. `stitch` filters
TileMatrixSets by CRS (multiple TMSes share names across projections —
there are three `1km` entries), so make sure `--projection` matches what
the layer was registered with.

**`"Invalid Layer"` from the time service for a fresh temporal
import.** Redis in `onearth-time-service` doesn't persist across
container restarts. If you bounced the stack, re-import or re-seed the
Redis keys. The URLs this tool prints use an explicit date instead of
the `default` keyword specifically to avoid time-service caching
issues that show up otherwise.

**`--diff` mean delta is huge (>50) or 83% of pixels differ.** Usually
a pyramid-level mapping bug hiding somewhere — the tool was saving
images from two *different* MRF levels and diffing them. Sanity check:
do `served` and `source` files look the same to the eye? If so, the
tool is correct and the diff is JPEG re-compression noise.

**`400 TileOutOfRange` on some tiles during stitch.** The TMS's matrix
at that level has more cells than the MRF's pyramid covers at that
resolution. Stitch leaves those cells blank and reports
`N/M tiles populated`. This is expected for layers whose extent
doesn't fill the full projection.

## Known limitations

See `DEFERRED.md` for items intentionally scoped out:

- `docker cp` file placement (overlay bloat; doesn't survive container
  recreation; a bind-mount strategy would fix both).
- Raster MRF only — no MVT / vector layers.
- The target projection endpoint YAML must already exist; the CLI
  won't create new endpoints.
- ZenJPEG payloads fall into `UNKNOWN_JPEG_VARIANT` until we know the
  magic bytes; served stitch still works via `mod_convert` but `--diff`
  refuses.
