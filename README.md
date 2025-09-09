# PGC Imagery Utils


## DEMO: Modernization preview for GAIA Task 1

> Task 1 - Enhancement of PGC ortho.py script: Enhance the existing `pgc_ortho.py` (or develop a new one if necessary) to support GAIA’s satellite image preprocessing, including projection, orthorectification, and related preprocessing functions.

This branch includes a minimal, backwards‑compatible preview of the architecture we propose for Task 1. It keeps today’s CLI workflows intact while demonstrating how we will stage and scale the system.

- Backwards compatible
  - Existing entry points (`pgc_ortho.py`, `pgc_mosaic*.py`, `pgc_ndvi.py`, `pgc_pansharpen.py`) are unchanged.
  - No behavioral changes to current tools.

- Containerized baseline (Phase 0)
  - `Dockerfile` pins a known‑good conda‑forge GDAL/PROJ stack.
  - `Makefile` auto‑detects platform (arm64/amd64) and provides:
    - `make build` – build the image
    - `make shell` – open an interactive shell in the image
    - `make run-ortho ...` – run `pgc_ortho.py` in the container

- FastAPI control plane (scaffold)
  - `tools/api/main.py` exposes:
    - `GET /health`
    - `POST /jobs/ortho` – validates requests against a JSON Schema and accepts a job
    - `GET /jobs/{id}` – returns recorded job status (in‑memory for demo)
  - Request schema: `tools/schemas/ortho_job.schema.json`
  - Example payload: `tools/schemas/examples/ortho_job.example.json`

- Staged package skeleton (no behavior changes yet)
  - `src/imagery_utils/` contains a staged runner and empty stage modules:
    - `context.py` (SceneCtx stub)
    - `runner.py` (stubbed `run_ortho()`)
    - `stages/` (ingest, dem_select, ortho, reproject, tiling, cog, qa stubs)
  - This is the foundation for the thin CLI shim and testable stages (to be implemented next).

- Sensor profile configuration (preview)
  - `tools/profiles/` contains a YAML schema stub and example profiles (e.g., WV03; Legion placeholder).

### Demo: run locally in a container

1) Build the image
```
make build
```

2) Run the API (serves on localhost:8000)
```
make api
```

3) Submit a demo job (in a separate terminal)
```
curl -s -X POST http://localhost:8000/jobs/ortho \
  -H 'Content-Type: application/json' \
  --data @tools/schemas/examples/ortho_job.example.json | jq
```

You should receive a 202/201 response with a `job_id`. For this demo the API validates and records the job, and returns a stub manifest; execution will be wired to a queue/worker next (Redis/Celery or Dask, plus PBS/Slurm adapters).

### Demo: execute existing orthorectification via staged runner

The staged `runner` now maps the JSON request into the argparse‑style parameters expected by the current library and calls `lib.ortho_functions.process_image` (backwards compatible). To run it on your data, set absolute paths in the example payload:

1) Edit `tools/schemas/examples/ortho_job.example.json`:
```
{
  "inputs": {
    "src": "/abs/path/to/src_dir_or_image",
    "dem": "auto",
    "config_file": "/app/doc/config.ini"
  },
  "output": { "dst": "/abs/path/to/dst_dir", "format": "GTiff", "gtiff_compression": "lzw" },
  "processing": { "epsg": "auto", "outtype": "Byte", "stretch": "rf", "resample": "near" },
  "execution": { "threads": 1, "parallel_processes": 1, "scratch": "/tmp/pgc" }
}
```

2) Submit and retrieve status/manifest:
```
curl -s -X POST http://localhost:8000/jobs/ortho \
  -H 'Content-Type: application/json' \
  --data @tools/schemas/examples/ortho_job.example.json | jq

curl -s http://localhost:8000/jobs/<job_id> | jq
```

Notes
- The runner currently handles single‑image flows; batching/HPC modes will be added next.
- When `dem` is set to `auto`, provide a valid `config_file` (see DEM Auto‑Selection below).
- Outputs are written under `output.dst`; the manifest includes timings, GDAL version, and output paths.

### SceneCtx (context object)

The staged pipeline passes a lightweight, immutable context (SceneCtx) between stages. Initial fields (to be expanded as stages are implemented):
- `sensor` (str|None): sensor identifier (e.g., WV03), from profiles or inferred metadata
- `rpc` (dict|None): parsed RPC metadata if available
- `epsg` (int|None): native EPSG code
- `footprints_wkt` (str|None): image footprint in WKT
- `pixel_size` (float|None): native pixel size (m)
- `chosen_dem` (str|None): URI/path of the selected DEM (when dem='auto')
- `param_hash` (str|None): stable hash of input parameters affecting outputs
- `meta` (dict): free‑form bag for stage‑specific annotations

SceneCtx enables clear, testable stages (ingest → DEM selection → orthorectify → reprojection → tiling → COG → QA) without changing today’s CLIs.

### STAC‑like manifest (output)

Each run emits a STAC‑like JSON manifest describing inputs, processing, provenance, and outputs. Example (truncated):
```
{
  "type": "Feature",
  "stac_version": "1.0.0",
  "id": "ortho-<uuid>",
  "properties": {
    "proj:epsg": 3031,
    "processing:stretch": "rf",
    "processing:outtype": "Byte",
    "processing:dem": "s3://…/pgc_dem.vrt",
    "provenance:gdal_version": "3060400",
    "provenance:timings": { "total_sec": 42.5, "stages": [ { "name": "orthorectify", "sec": 41.8 } ] }
  },
  "assets": {
    "ortho": { "href": "s3://bucket/path/output.tif", "type": "image/tiff; application=geotiff" },
    "cog":   { "href": "s3://bucket/path/output.cog.tif", "type": "image/tiff; application=geotiff; profile=cog" },
    "qa":    { "href": "s3://bucket/path/qa.json", "type": "application/json" }
  }
}
```
“STAC‑like” means we follow the Item shape and common fields, while including additional processing/provenance fields (e.g., timings, GDAL/PROJ versions, chosen DEM). Full STAC conformance can be added later.

## Task 5 – Support for Maxar Legion

To ensure GAIA can ingest future high‑resolution sources, we will add Legion support without breaking existing flows (WV2/WV3). The work builds directly on today’s orthorectification pipeline and the Task 1 staging.

Planned approach (backwards‑compatible)
- Profiles, not code: introduce a Legion sensor profile (YAML) alongside WV series (see `tools/profiles/`). The profile will define band maps/order, native pixel size, pan:MS ratio (if applicable), expected metadata sources (IMD/RPB/XML/PVL), and radiometric constants.
- Detection and metadata: extend the existing filename/metadata detection to recognize Legion; add a metadata parser that normalizes fields similarly to DG/GE/IK.
- RPC + DEM: reuse the current RPC+DEM path (`-rpc` with either `RPC_DEM` or `RPC_HEIGHT`) for terrain correction; ensure `extract_rpb` supports Legion packaging (e.g., .RPB or xml inside a container).
- Orthorectification: continue to use the current `lib/ortho_functions.process_image` pipeline with safe defaults; no changes required for users who do not process Legion.
- DEM selection policy: keep the existing GeoPackage‑driven `--dem auto` semantics, while allowing a configured priority (PGC DEM → Copernicus 30 m → SRTM); record the chosen DEM in the manifest.
- Azure‑ready output: provide optional `--to-cog` to produce COGs validated by `gdalinfo -json`; document VSICURL/Azure credential usage for reading/writing containers.
- Staged runner: the API/runner calls the same library functions and emits a STAC‑like manifest with inputs, Legion profile name/version, chosen DEM, timings, and outputs.

Validation plan
- Unit tests for detection, metadata parsing, and radiometric LUTs for Legion (based on vendor specs).
- E2E run on representative Legion samples: georeferencing tolerances (bbox/centroid/area), radiometric tolerances per band, and COG compliance.

Status (this branch)
- A Legion profile placeholder is included at `tools/profiles/LEGION.yaml`. When authoritative specs and samples are available, we will finalize detection, parsing, radiometry, and RPC handling and enable Legion end‑to‑end without breaking WV2/WV3 users.

### What comes next (without breaking users)
- Implement the staged runner and stages to call existing logic incrementally (ingest → DEM selection → orthorectification → optional reprojection → tiling → COG → QA), emitting a STAC‑like manifest.
- Add Redis + worker to execute jobs asynchronously; add PBS/Slurm adapters; optional Dask executor.
- Introduce YAML‑based sensor profiles and a DEM selection policy with multiple backends (local/HTTP COG/Azure), while preserving today’s `--dem auto` semantics.
- Keep current flags and outputs stable; new capabilities will be additive (e.g., `--sensor`, `--executor`, `--target-epsg`, `--target-res`, `--to-cog`, `--manifest`).


## Introduction
PGC Imagery Utils is a collection of commercial satellite imagery manipulation tools to handle batch processing of 
Geoeye and DigitalGlobe/Maxar imagery. The tools can:

1) Correct for terrain and radiometry
2) Mosaic several images into one set of tiles
3) Pansharpen a multispectral image with its panchromatic partner
4) Calculate an NDVI raster from a multispectral image.

These tools are build on the GDAL/OGR image processing API using Python.  The code is built to run primarily on a Linux 
HPC cluster running PBS or Slurm for queue management.  Some of the tools will work on a Windows platform.

The code is tightly coupled to the systems on which it was developed.  You should have no expectation of it running 
perfectly on another system without some patching.

## Utilites
Files starting with "qsub" and "slurm" are PBS and SLURM submission scripts.  See the script-specific documentation for 
more details on usage.

### pgc_ortho

The orthorectification script can correct for terrain displacement and radiometric settings as well as alter the bit 
depth of the imagery.  Using the --pbs or --slurm options will submit the jobs to a job scheduler.  Alternatively, 
using the --parallel-processes option will instruct the script to run multiple tasks in parallel.  Using --threads N 
will enable threading for gdalwarp, where N is the number of threads (or ALL_CPUS); this option will not work with 
--pbs/--slurm, and (threads * parallel processes) cannot exceed number of threads available on system.

Example:
```
python pgc_ortho.py --epsg 3031 --dem DEM.tif --format GTiff --stretch ns --outtype UInt16 input_dir output dir
```

This example will take all the nitf or tif files in the input_dir and orthorectify them using DEM.tif.  The output files
will be written to output_dir and be 16 bit (like the original image) GeoTiffs with no stretch applied with a spatial 
reference of EPSG 3031, or Antarctic Polar Stereographic -71.

#### DEM Auto-Selection Configuration (when using `--dem auto`)

When using the `--dem auto` setting in `pgc_ortho.py`, the script will automatically attempt to select an appropriate 
DEM based on image location and geometry. For this to work, a configuration file must be specified using the `--config`
option. This configuration file should contain a valid `gpkg_path` entry, which points to the GeoPackage file that holds
DEM coverage information.

**Configuration Requirements**

The config file should point to a file path for checking image overlap with reference dems. This path should locate a 
geopackage file which includes geometries of a list of reference DEMs. Each feature in each layer of the geopackage 
should have a field named 'dempath' pointing to the corresponding reference DEM.

1. **Config File Path**: Ensure that the config file exists at the specified path provided to the `--config` argument.
2. **`gpkg_path` Setting**: The config file should have a `gpkg_path` entry under the `[default]` section. This path 
should point to a GeoPackage file containing a 'dempath' field to the corresponding DEM. There is support for specific
Windows filepaths as well by adding a `gpkg_path` entry under the `[windows]` section.
3. **Valid DEM File**: The path specified by `dempath` should be accessible and valid. For Windows-like filepaths
the path specified by `windowspath` should be accessible and valid.

**Example Configuration File (`config.ini`)**

```ini
[default]
gpkg_path = /path/to/dem_list.gpkg

[windows]
gpkg_path = V:\path\to\dem_list.gpkg
```

### pgc_mosaic

The mosaicking toolset mosaics multiple input images into a set of non-overlapping output tile images.  It can sort the 
images according to several factors including cloud cover, sun elevation angle, off-nadir angle, probability of 
overexposure, and proximity to a specific date.  It consists of 3 scripts:

1. pgc_mosaic.py - initializes the output mosaic, creates cutlines, and run the subtile processes.
2. pgc_mosaic_query_index.py - takes mosaic parameters and a shapefile index and determines which images will contribute
to the resulting mosaic. The resulting list can be used to reduce the number of images that are run through the 
orthorectification script to those that will be eventually used.
3. pgc_mosaic_build_tile.py - builds an individual mosaic tile.  This script is invoked by pgc_mosaic.

Example:
```
python pgc_mosaic.py --slurm --bands 1 --tilesize 20000 20000 --resolution 0.5 0.5 input_dir output_mosaic_name
```

This example will evaluate all the 1-band images in input_dir and sort them according to their quality score.  It will 
submit a job to the cluster queue to build each tile of size 20,000 x 20,000 pixels at 0.5 meters resolution.  The 
output tiles will be Geotiffs named by appending a row and column identifier to the output_mosaic_name.

### pgc_pansharpen

The pansharpening utility applies the orthorectification process to both the pan and multi image in a pair and then 
pansharpens them using the GDAL tool gdal_pansharpen.  GDAL 2.1+ is required for this tool to function.  The --threads
flag will apply threading to both gdalwarp and gdal_pansharpen operations.

### pgc_ndvi

The NDVI utility calculates NDVI from multispectral image(s).  The tool is designed to run on data that have already
been run through the pgc_ortho utility.

## Miscellaneous Utility Scripts

### Building RGB Composite Landsat TIFs - stack_landsat.py

`stack_landsat.py` is a command line tool to combine individual Landsat band .tif files into a stacked RGB composite 
.tif. To run, set the input directory to a folder with the downloaded Landsat imagery you want to combine, with each of 
the bands as a separate .tiff file. The script will need to be run within the same environment as the other PGC 
utilities in this repo; it only uses standard python and gdal functionality, so there is nothing further to install.

Show tool help text:
```python C:\path\to\stack_landsat.py -h```

Example usage with long options:
```python C:\path\to\stack_landsat.py --input-dir C:\path\to\landsat\directory --output-dir C:\path\to\output\dir```

Example usage with short options:
```python C:\path\to\stack_landsat.py -i C:\path\to\landsat\directory -o C:\path\to\output\dir```

The script will:
 - Verify that the provided input directory exists and is, in fact, a directory
 - Create the output directory if it does not already exist
 - Find all the Landsat scenes in the input directory
 - Attempt to create a composite RGB TIF of the scenes it finds
 - Report the scenes it fails to build. For instance, an RGB TIF will not be built if all of bands 4, 3, and 2 do 
not exist
 - Write the console messages to a log file in the input directory (stack_landsat_{date}.log). There is no need to 
retain the logs long term if the script is operating smoothly

The script will not:
 - Know anything about previous runs. If you rerun the script, it will process whatever inputs are present, even if 
they have been run previously. It will also overwrite any corresponding outputs if pointed to the same output 
directory.

### Identifying Overaping Images - pgc_get_scene_overlap_standalone.py
`pgc_get_scene_overlap_standalone.py` is a tool to identify which images are stereo-photogrammetry. 
candidates.

## Installation and dependencies
PGC uses the Miniforge installer to build our Python/GDAL software stack.  You can find installers for your OS here:
https://github.com/conda-forge/miniforge?tab=readme-ov-file#miniforge3

Users should expect a recent (less than 1-2 years old) version of Python and GDAL to be compatible with tools in this 
repo.
The following conda/mamba environment likely contains more dependencies than are needed for tools in this repo, but 
should suffice:
```
mamba create --name pgc -c conda-forge git python=3.11 gdal=3.6.4 globus-sdk globus-cli numpy scipy pandas geopandas 
rasterio shapely postgresql psycopg2 sqlalchemy configargparse lxml pathlib2 python-dateutil pytest rtree xlsxwriter 
tqdm alive-progress pyperclip --yes
```

## Running Tests
Tests for imagery-utils use python's pytest. They require licensed commercial data that cannot be distributed freely
but is available to project contributors.

On Linux systems, make a symlink to the test data location:
```sh
# first time only
ln -s <test_data_location>/tests/testdata tests/

# run the tests
pytest
```

On Windows, you have to use the full network path and not a mounted drive letter path:
```sh
# first time only
mklink /d tests\testdata <\\server.school.edu\test_data_location>\tests\testdata

# run the tests
pytest
```

## Contact
To report any questions or issues, please open a github issue or contact the Polar Geospatial Center: 
pgc-support@umn.edu
