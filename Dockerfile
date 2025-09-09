# syntax=docker/dockerfile:1
FROM mambaorg/micromamba:1.5.8

ARG MAMBA_DOCKERFILE_ACTIVATE=1
SHELL ["/bin/bash", "-lc"]

# Create env consistent with README guidance (adjust pins as needed)
RUN micromamba create -y -n pgc -c conda-forge \
    python=3.11 gdal=3.6.4 numpy scipy pandas geopandas rasterio shapely \
    postgresql psycopg2 sqlalchemy configargparse lxml pathlib2 python-dateutil \
    pytest rtree xlsxwriter tqdm alive-progress pyperclip globus-sdk globus-cli \
    fastapi uvicorn jsonschema \
  && micromamba clean -a -y

ENV PATH=/opt/conda/envs/pgc/bin:$PATH
ENV GDAL_PAM_ENABLED=NO
ENV PROJ_LIB=/opt/conda/envs/pgc/share/proj
ENV GDAL_DATA=/opt/conda/envs/pgc/share/gdal

# Useful GDAL/PROJ defaults (conservative)
ENV CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif,.tiff,.vrt,.tar,.gz,.bz2,.zip,.img,.ntf,.jp2

WORKDIR /app
COPY . /app

# Default to bash; call scripts explicitly, e.g.:
# docker run --rm -v "$PWD":"/workspace" -w "/workspace" <image> \
#   python /app/pgc_ortho.py -p auto -d auto /data/src /data/dst
ENTRYPOINT ["bash"]
