# Use the official Apache Beam SDK image as the base
FROM apache/beam_python3.10_sdk:2.53.0

COPY --from=gcr.io/dataflow-templates-base/python311-template-launcher-base:20230622_RC00 /opt/google/dataflow/python_template_launcher /opt/google/dataflow/python_template_launcher

RUN apt-get update && apt-get install -y

# Install dependencies with specific versions
RUN pip install --no-cache-dir \
    paramiko \
    protobuf \
    pyarrow \ 
    google-cloud-storage

# Download and install rclone
# RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip \
#     && unzip rclone-current-linux-amd64.zip \
#     && cd rclone-*-linux-amd64 \
#     && cp rclone /usr/bin/ \
#     && chown root:root /usr/bin/rclone \
#     && chmod 755 /usr/bin/rclone \
#     && mkdir -p /usr/local/share/man/man1 \
#     && cp rclone.1 /usr/local/share/man/man1/
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

# Copy your Beam pipeline code into the container
ARG WORKDIR=/template
WORKDIR ${WORKDIR}

COPY main.py .
# COPY pyproject.toml .
# COPY requirements.txt .
# COPY setup.py .
COPY src src


ENV FLEX_TEMPLATE_PYTHON_PY_FILE="${WORKDIR}/main.py"


# You might want to set a default command to run your pipeline
ENTRYPOINT ["/opt/apache/beam/boot"]
