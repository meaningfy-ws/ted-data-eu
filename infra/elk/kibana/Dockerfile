ARG ELASTIC_VERSION
ARG KIBANA_PLUGIN_VERSION_URL
# https://www.docker.elastic.co/
FROM docker.elastic.co/kibana/kibana:${ELASTIC_VERSION}

# Add your kibana plugins setup here
# Example: RUN kibana-plugin install <name|url>

RUN kibana-plugin install KIBANA_PLUGIN_VERSION_URL