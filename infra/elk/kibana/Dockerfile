ARG ELASTIC_VERSION

# https://www.docker.elastic.co/
FROM docker.elastic.co/kibana/kibana:${ELASTIC_VERSION}

# Add your kibana plugins setup here
# Example: RUN kibana-plugin install <name|url>
ENV KIBANA_PLUGIN_VERSION=${ELASTIC_VERSION}
RUN kibana-plugin install "https://github.com/meaningfy-ws/kibana-custom-theme-plugin/raw/main/builds/customKibanaTheme-${KIBANA_PLUGIN_VERSION}.zip"