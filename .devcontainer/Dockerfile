FROM mcr.microsoft.com/vscode/devcontainers/universal:1-linux

# Add LDAP and python dependency build deps
USER root

RUN apt-get update && \
    apt-get -yq --no-install-recommends install gcc curl libsasl2-dev libldap2-dev libssl-dev

# [Option] Install Node.js
ARG INSTALL_NODE="true"
ARG NODE_VERSION="lts/*"
RUN if [ "${INSTALL_NODE}" = "true" ]; then su codespace -c "source /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

RUN npm install -g gulp

USER codespace
