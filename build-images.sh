#!/bin/bash

#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

# Terminate on error
set -e

# Prepare variables for later use
images=()
# The image will be pushed to the GitHub container registry
repobase="${REPOBASE:-ghcr.io/tebbiworld}"
# Configure the image name
reponame="arsnova"

# Pin the application images used at runtime. They are declared in the
# org.nethserver.images label so the node agent pre-pulls them and exposes
# their reference as ${<NAME>_IMAGE} (image name uppercased, non-alphanumeric
# turned into underscores). ARSnova/Particify is a microservice stack: a set
# of Spring-Boot services plus CouchDB, two PostgreSQL databases, a RabbitMQ
# STOMP broker, the Angular web client and the front reverse proxy.
#
#   docker.io/particify/couchdb:3.5                  -> COUCHDB_IMAGE
#   docker.io/library/postgres:13.8-alpine           -> POSTGRES_IMAGE
#   docker.io/particify/rabbitmq-stomp:3.11-alpine   -> RABBITMQ_STOMP_IMAGE
#   docker.io/particify/arsnova-server-authz:3.13    -> ARSNOVA_SERVER_AUTHZ_IMAGE
#   docker.io/particify/arsnova-server-core:3.13     -> ARSNOVA_SERVER_CORE_IMAGE
#   docker.io/particify/arsnova-server-comments:3.13 -> ARSNOVA_SERVER_COMMENTS_IMAGE
#   docker.io/particify/arsnova-server-websocket:3.13-> ARSNOVA_SERVER_WEBSOCKET_IMAGE
#   docker.io/particify/arsnova-server-gateway:3.13  -> ARSNOVA_SERVER_GATEWAY_IMAGE
#   docker.io/particify/arsnova-server-formatting:3.13-> ARSNOVA_SERVER_FORMATTING_IMAGE
#   docker.io/particify/arsnova-webclient:3.13       -> ARSNOVA_WEBCLIENT_IMAGE
#   docker.io/particify/arsnova-proxy:3.13           -> ARSNOVA_PROXY_IMAGE
# Fully pinned references: dated 3.13 builds where Particify publishes them,
# digests for the images that only have rolling tags (proxy 3.13, couchdb 3.5,
# rabbitmq-stomp 3.11-alpine).
runtime_images=(
    # particify/couchdb:3.5 (CouchDB 3.5.2), the version of Particify's own
    # 3.13 compose file; CouchDB 3.x upgrades its data files in place
    "docker.io/particify/couchdb@sha256:12486b4e09af3d37598bacae7d945c7d911370b6a3f027516979af0e5fe31014"
    "docker.io/library/postgres:13.8-alpine"
    "docker.io/particify/rabbitmq-stomp@sha256:411565bb5c984c65d3325ae8d12594004b4c304b93478d3710f444841ad99239"
    "docker.io/particify/arsnova-server-authz:3.13.20260613"
    "docker.io/particify/arsnova-server-core:3.13.20260613"
    "docker.io/particify/arsnova-server-comments:3.13.20260613"
    "docker.io/particify/arsnova-server-websocket:3.13.20260613"
    "docker.io/particify/arsnova-server-gateway:3.13.20260613"
    "docker.io/particify/arsnova-server-formatting:3.13.20260613"
    "docker.io/particify/arsnova-webclient:3.13.20260613"
    "docker.io/particify/arsnova-proxy@sha256:f431909169b6306f5ace6d876944a94a3747b594f229bc3e956f6b2e7382c0bc"
)

# Create a new empty container image
container=$(buildah from scratch)

# Reuse existing nodebuilder-arsnova container, to speed up builds
if ! buildah containers --format "{{.ContainerName}}" | grep -q nodebuilder-arsnova; then
    echo "Pulling NodeJS runtime..."
    buildah from --name nodebuilder-arsnova -v "${PWD}:/usr/src:Z" docker.io/library/node:24.16.0-slim
fi

echo "Build static UI files with node..."
buildah run \
    --workingdir=/usr/src/ui \
    --env="NODE_OPTIONS=--openssl-legacy-provider" \
    nodebuilder-arsnova \
    sh -c "yarn install && yarn build"

# Add imageroot and the compiled UI to the container image
buildah add "${container}" imageroot /imageroot
buildah add "${container}" ui/dist /ui
# Setup the entrypoint, reserve a single TCP port (the front proxy), declare the
# runtime images and mark the module as rootless.
buildah config --entrypoint=/ \
    --label="org.nethserver.authorizations=traefik@node:routeadm cluster:accountconsumer" \
    --label="org.nethserver.tcp-ports-demand=1" \
    --label="org.nethserver.rootfull=0" \
    --label="org.nethserver.images=${runtime_images[*]}" \
    "${container}"
# Commit the image
buildah commit "${container}" "${repobase}/${reponame}"

# Append the image URL to the images array
images+=("${repobase}/${reponame}")

#
# Setup CI when pushing to Github.
# Warning! docker::// protocol expects lowercase letters (,,)
if [[ -n "${CI}" ]]; then
    # Set output value for Github Actions
    printf "images=%s\n" "${images[*],,}" >> "${GITHUB_OUTPUT}"
else
    # Just print info for manual push
    printf "Publish the images with:\n\n"
    for image in "${images[@],,}"; do printf "  buildah push %s docker://%s:%s\n" "${image}" "${image}" "${IMAGETAG:-latest}" ; done
    printf "\n"
fi
