IMAGE ?= pgc-imagery-utils:baseline
DOCKER ?= docker
PWD   := $(shell pwd)

# Platform detection (override with: make PLATFORM=linux/amd64)
UNAME_M := $(shell uname -m)
ifeq ($(UNAME_M),arm64)
  DETECTED_PLATFORM := linux/arm64/v8
else ifeq ($(UNAME_M),aarch64)
  DETECTED_PLATFORM := linux/arm64/v8
else
  DETECTED_PLATFORM := linux/amd64
endif
PLATFORM ?= $(DETECTED_PLATFORM)

.PHONY: build shell run-ortho qa-gdalinfo

build:
	$(DOCKER) buildx build --platform $(PLATFORM) --load -t $(IMAGE) .

shell: build
	$(DOCKER) run --platform $(PLATFORM) --rm -it --entrypoint /bin/bash -v "$(PWD)":/workspace -w /workspace $(IMAGE)

# Example: make run-ortho SRC=/data/src DST=/data/dst ARGS="-p auto -d auto"
run-ortho: build
	@test -n "$(SRC)" || (echo "Set SRC=/path and DST=/path" && exit 1)
	@test -n "$(DST)" || (echo "Set SRC=/path and DST=/path" && exit 1)
	$(DOCKER) run --platform $(PLATFORM) --rm -v "$(PWD)":/workspace -w /workspace --entrypoint python $(IMAGE) \
		/app/pgc_ortho.py $(ARGS) "$(SRC)" "$(DST)"

# Example: make qa-gdalinfo TARGETS="/workspace/out/*.tif" OUT=qa/gdalinfo.json
qa-gdalinfo: build
	@test -n "$(TARGETS)" || (echo "Set TARGETS=\"glob(s)\" of rasters" && exit 1)
	@mkdir -p qa
	$(DOCKER) run --platform $(PLATFORM) --rm -v "$(PWD)":/workspace -w /workspace --entrypoint python $(IMAGE) \
		/app/tools/collect_gdalinfo.py --out "$(OUT)" $(TARGETS)
