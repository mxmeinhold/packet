FROM mcr.microsoft.com/vscode/devcontainers/universal:1-linux

USER root

# Add LDAP and python dependency build deps
RUN apt-get update && \
    apt-get -yq --no-install-recommends install gcc curl libsasl2-dev libldap2-dev libssl-dev

# Install node and gulp
ARG NODE_VERSION="lts/*"
RUN su codespace -c "nvm install ${NODE_VERSION} && nvm use ${NODE_VERSION} && npm install -g gulp"

USER codespace
