# Contributor image for El Hidratador.
#
# The base image ships a "vscode" account with uid 1000. The workspace folder
# is bind mounted from the host, so the remote user needs uid 1000 to keep the
# checkout writable. The account is renamed instead of added, because a second
# account with the same uid cannot be created.

FROM mcr.microsoft.com/devcontainers/python:3.13

RUN set -eux; \
    groupmod --new-name hidratador vscode; \
    usermod --login hidratador --home /home/hidratador --move-home vscode; \
    if [ -f /etc/sudoers.d/vscode ]; then \
        sed 's/^vscode /hidratador /' /etc/sudoers.d/vscode > /etc/sudoers.d/hidratador; \
        rm -f /etc/sudoers.d/vscode; \
        chmod 0440 /etc/sudoers.d/hidratador; \
    fi
