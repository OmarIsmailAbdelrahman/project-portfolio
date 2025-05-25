# Use the official Apache Beam SDK image as the base
FROM apache/beam_python3.10_sdk:2.53.0

RUN apt-get update && apt-get install -y

RUN pip install \
    google-cloud-pubsub \
    paramiko \
    google-cloud-secret-manager

# Download and install rclone
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip \
    && unzip rclone-current-linux-amd64.zip \
    && cd rclone-*-linux-amd64 \
    && cp rclone /usr/bin/ \
    && chown root:root /usr/bin/rclone \
    && chmod 755 /usr/bin/rclone \
    && mkdir -p /usr/local/share/man/man1 \
    && cp rclone.1 /usr/local/share/man/man1/
    # && mandb

# Fix protoco and gcp-storage problem
ENV PB_REL="https://github.com/protocolbuffers/protobuf/releases"
RUN curl -LO $PB_REL/download/v30.2/protoc-30.2-linux-x86_64.zip \
    && unzip protoc-30.2-linux-x86_64.zip -d /root/.local \
    && export PATH="$PATH:/root/.local/bin" \
    && pip install protobuf \
    && pip install --upgrade google-cloud-storage \
    && pip install --upgrade grpcio

# Set the working directory (optional, but good practice)
WORKDIR /app

# Copy your Beam pipeline code into the container
COPY ./pipeline.py /pipeline.py


# You might want to set a default command to run your pipeline
ENTRYPOINT ["/opt/apache/beam/boot"]
