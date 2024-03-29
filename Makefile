SHELL=/bin/bash -o pipefail
BUILD_PRINT = \e[1;34mSTEP:
END_BUILD_PRINT = \e[0m

CURRENT_UID := $(shell id -u)
export CURRENT_UID
# These are constants used for make targets so we can start prod and staging services on the same machine
ENV_FILE := .env

# include .env files if they exist
-include .env

PROJECT_PATH = $(shell pwd)
AIRFLOW_INFRA_FOLDER ?= ${PROJECT_PATH}/.airflow
RML_MAPPER_PATH = ${PROJECT_PATH}/.rmlmapper/rmlmapper.jar
XML_PROCESSOR_PATH = ${PROJECT_PATH}/.saxon/saxon-he-10.6.jar
HOSTNAME = $(shell hostname)


#-----------------------------------------------------------------------------
# Dev commands
#-----------------------------------------------------------------------------
install:
	@ echo -e "$(BUILD_PRINT)Installing the requirements$(END_BUILD_PRINT)"
	@ python -m pip install --upgrade pip
	@ python -m pip install --no-cache-dir -r requirements.txt --force-reinstall --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.5.1/constraints-no-providers-3.8.txt"

install-dev:
	@ echo -e "$(BUILD_PRINT)Installing the dev requirements$(END_BUILD_PRINT)"
	@ python -m pip install --upgrade pip
	@ python -m pip install --no-cache-dir -r requirements.dev.txt --user --force-reinstall --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.5.1/constraints-no-providers-3.8.txt"

test: test-unit

test-unit:
	@ echo -e "$(BUILD_PRINT)Unit Testing ...$(END_BUILD_PRINT)"
	@ tox -e unit

test-features:
	@ echo -e "$(BUILD_PRINT)Gherkin Features Testing ...$(END_BUILD_PRINT)"
	@ tox -e features

test-e2e:
	@ echo -e "$(BUILD_PRINT)End to End Testing ...$(END_BUILD_PRINT)"
	@ tox -e e2e

test-all-parallel:
	@ echo -e "$(BUILD_PRINT)Complete Testing ...$(END_BUILD_PRINT)"
	@ tox -p

test-all:
	@ echo -e "$(BUILD_PRINT)Complete Testing ...$(END_BUILD_PRINT)"
	@ tox

build-externals:
	@ echo -e "$(BUILD_PRINT)Creating the necessary volumes, networks and folders and setting the special rights"
	@ docker network create proxy-net || true
	@ docker network create common-ext-${ENVIRONMENT} || true
#-----------------------------------------------------------------------------
# SERVER SERVICES
#-----------------------------------------------------------------------------
start-traefik: build-externals
	@ echo -e "$(BUILD_PRINT)Starting the Traefik services $(END_BUILD_PRINT)"
	@ docker-compose  --file ./infra/traefik/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-traefik:
	@ echo -e "$(BUILD_PRINT)Stopping the Traefik services $(END_BUILD_PRINT)"
	@ docker-compose  --file ./infra/traefik/docker-compose.yml --env-file ${ENV_FILE} down
#-----------------------------------------------------------------------------
# temporary
start-metabase: build-externals
	@ echo -e "$(BUILD_PRINT)Starting the Metabase services $(END_BUILD_PRINT)"
	@ docker-compose -p metabase-${ENVIRONMENT} --file ./infra/metabase/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-metabase:
	@ echo -e "$(BUILD_PRINT)Stopping the Metabase services $(END_BUILD_PRINT)"
	@ docker-compose -p metabase-${ENVIRONMENT} --file ./infra/metabase/docker-compose.yml --env-file ${ENV_FILE} down

#-----------------------------------------------------------------------------
# PROJECT SERVICES
#-----------------------------------------------------------------------------
create-env-airflow:
	@ echo -e "$(BUILD_PRINT) Create Airflow env $(END_BUILD_PRINT)"
	@ echo -e "$(BUILD_PRINT) ${AIRFLOW_INFRA_FOLDER} ${ENVIRONMENT} $(END_BUILD_PRINT)"
	@ mkdir -p ${AIRFLOW_INFRA_FOLDER}/logs ${AIRFLOW_INFRA_FOLDER}/plugins
	@ ln -s -f ${PROJECT_PATH}/.env ${AIRFLOW_INFRA_FOLDER}/.env
	@ ln -s -f -n ${PROJECT_PATH}/dags ${AIRFLOW_INFRA_FOLDER}/dags
	@ ln -s -f -n ${PROJECT_PATH}/ted_data_eu ${AIRFLOW_INFRA_FOLDER}/ted_data_eu
	@ chmod 777 ${AIRFLOW_INFRA_FOLDER}/logs ${AIRFLOW_INFRA_FOLDER}/plugins ${AIRFLOW_INFRA_FOLDER}/.env
	@ cp requirements.txt ./infra/airflow/

create-env-airflow-cluster:
	@ echo -e "$(BUILD_PRINT) Create Airflow env $(END_BUILD_PRINT)"
	@ echo -e "$(BUILD_PRINT) ${AIRFLOW_INFRA_FOLDER} ${ENVIRONMENT} $(END_BUILD_PRINT)"
	@ mkdir -p ${AIRFLOW_INFRA_FOLDER}/logs ${AIRFLOW_INFRA_FOLDER}/plugins ${AIRFLOW_INFRA_FOLDER}/.env
	@ ln -s -f -n ${PROJECT_PATH}/dags ${AIRFLOW_INFRA_FOLDER}/dags
	@ ln -s -f -n ${PROJECT_PATH}/ted_data_eu ${AIRFLOW_INFRA_FOLDER}/ted_data_eu
	@ chmod 777 ${AIRFLOW_INFRA_FOLDER}/logs ${AIRFLOW_INFRA_FOLDER}/plugins ${AIRFLOW_INFRA_FOLDER}/.env
	@ cp requirements.txt ./infra/airflow-cluster/

build-airflow: guard-ENVIRONMENT create-env-airflow build-externals
	@ echo -e "$(BUILD_PRINT) Build Airflow services $(END_BUILD_PRINT)"
	@ docker build -t meaningfy/airflow ./infra/airflow/
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/airflow/docker-compose.yaml --env-file ${ENV_FILE} up -d --force-recreate

start-airflow: build-externals
	@ echo -e "$(BUILD_PRINT)Starting Airflow services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/airflow/docker-compose.yaml --env-file ${ENV_FILE} up -d

stop-airflow:
	@ echo -e "$(BUILD_PRINT)Stopping Airflow services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/airflow/docker-compose.yaml --env-file ${ENV_FILE} down

build-airflow-cluster: guard-ENVIRONMENT create-env-airflow-cluster build-externals
	@ echo -e "$(BUILD_PRINT) Build Airflow Common Image $(END_BUILD_PRINT)"
	@ docker build -t meaningfy/airflow ./infra/airflow-cluster/

start-airflow-master: build-externals
	@ echo -e "$(BUILD_PRINT)Starting Airflow Master $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/airflow-cluster/docker-compose.yaml --env-file ${ENV_FILE} up -d --force-recreate

start-airflow-worker: build-externals
	@ echo -e "$(BUILD_PRINT)Starting Airflow Worker $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/airflow-cluster/docker-compose-worker.yaml --env-file ${ENV_FILE} up -d

stop-airflow-master:
	@ echo -e "$(BUILD_PRINT)Stopping Airflow Master $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/airflow-cluster/docker-compose.yaml --env-file ${ENV_FILE} down

stop-airflow-worker:
	@ echo -e "$(BUILD_PRINT)Stopping Airflow Worker $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/airflow-cluster/docker-compose-worker.yaml --env-file ${ENV_FILE} down


restart-airflow-master: stop-airflow-master create-env-airflow-cluster
	@ echo -e "$(BUILD_PRINT)Restart Airflow Master $(END_BUILD_PRINT)"
	@ git pull
	@ make build-airflow-cluster
	@ make start-airflow-master

restart-airflow-worker: stop-airflow-worker create-env-airflow-cluster
	@ echo -e "$(BUILD_PRINT)Restart Airflow Worker $(END_BUILD_PRINT)"
	@ git pull
	@ make build-airflow-cluster
	@ make start-airflow-worker

start-allegro-graph: build-externals
	@ echo -e "$(BUILD_PRINT)Starting Allegro-Graph services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/allegro-graph/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-allegro-graph:
	@ echo -e "$(BUILD_PRINT)Stopping Allegro-Graph services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/allegro-graph/docker-compose.yml --env-file ${ENV_FILE} down

#	------------------------
start-fuseki: build-externals
	@ echo -e "$(BUILD_PRINT)Starting Fuseki services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/fuseki/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-fuseki:
	@ echo -e "$(BUILD_PRINT)Stopping Fuseki services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/fuseki/docker-compose.yml --env-file ${ENV_FILE} down

#	------------------------
start-sftp: build-externals
	@ echo -e "$(BUILD_PRINT)Starting SFTP services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/sftp/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-sftp:
	@ echo -e "$(BUILD_PRINT)Stopping SFTP services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/sftp/docker-compose.yml --env-file ${ENV_FILE} down

start-minio: build-externals
	@ echo -e "$(BUILD_PRINT)Starting the Minio services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/minio/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-minio:
	@ echo -e "$(BUILD_PRINT)Stopping the Minio services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/minio/docker-compose.yml --env-file ${ENV_FILE} down

start-postgres: build-externals
	@ echo -e "$(BUILD_PRINT)Starting the Postgres services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/postgres/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-postgres:
	@ echo -e "$(BUILD_PRINT)Stopping the Postgres services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/postgres/docker-compose.yml --env-file ${ENV_FILE} down

#	------------------------
start-dash: build-externals
	@ echo -e "$(BUILD_PRINT)Starting Dash services $(END_BUILD_PRINT)"
	@ cp requirements.txt ./infra/dash/
	@ cp -R ${PROJECT_PATH}/dash ./infra/dash
	@ cp -R ${PROJECT_PATH}/dags/resources/sparql_queries ./infra/dash
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/dash/docker-compose.yml --env-file ${ENV_FILE} up -d --build
	@ rm -r ./infra/dash/dash
	@ rm -r ./infra/dash/sparql_queries
	@ rm ./infra/dash/requirements.txt

stop-dash:
	@ echo -e "$(BUILD_PRINT)Stopping Dash services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/dash/docker-compose.yml --env-file ${ENV_FILE} down


init-limes:
	@ echo -e "Limes folder initialisation!"
	@ mkdir -p ./.limes
	@ wget -c https://github.com/dice-group/LIMES/releases/download/1.7.9/limes.jar -P ./.limes


init-rml-mapper:
	@ echo -e "RMLMapper folder initialisation!"
	@ mkdir -p ./.rmlmapper
	@ wget -c https://github.com/RMLio/rmlmapper-java/releases/download/v6.0.0/rmlmapper-6.0.0-r363-all.jar -O ./.rmlmapper/rmlmapper.jar


init-saxon:
	@ echo -e "$(BUILD_PRINT)Saxon folder initialization $(END_BUILD_PRINT)"
	@ wget -c https://kumisystems.dl.sourceforge.net/project/saxon/Saxon-HE/10/Java/SaxonHE10-6J.zip -P .saxon/
	@ cd .saxon && unzip SaxonHE10-6J.zip && rm -rf SaxonHE10-6J.zip


start-common-project-services: | start-mongo start-sftp start-fuseki start-allegro-graph start-minio start-metabase start-graphdb start-elk
stop-common-project-services: | stop-mongo stop-sftp stop-fuseki stop-allegro-graph stop-minio stop-metabase stop-graphdb stop-elk

start-prod-project-services : | prod-dotenv-file create-env-airflow-cluster start-airflow-master start-common-project-services start-digest_service-api
stop-prod-project-services : | stop-airflow-master stop-common-project-services stop-digest_service-api

start-staging-project-services : | staging-dotenv-file create-env-airflow start-airflow start-common-project-services install-allure
stop-staging-project-services : | stop-airflow stop-common-project-services

start-dev-project-services : | dev-dotenv-file create-env-airflow start-airflow start-common-project-services
stop-dev-project-services : | stop-airflow stop-common-project-services


#-----------------------------------------------------------------------------
# VAULT SERVICES
#-----------------------------------------------------------------------------
# Testing whether an env variable is set or not
guard-%:
	@ if [ "${${*}}" = "" ]; then \
        echo -e "$(BUILD_PRINT)Environment variable $* not set $(END_BUILD_PRINT)"; \
        exit 1; \
	fi

# Testing that vault is installed
vault-installed: #; @which vault1 > /dev/null
	@ if ! hash vault 2>/dev/null; then \
        echo -e "$(BUILD_PRINT)Vault is not installed, refer to https://www.vaultproject.io/downloads $(END_BUILD_PRINT)"; \
        exit 1; \
	fi
# Get secrets in dotenv format

dev-dotenv-file: guard-VAULT_ADDR guard-VAULT_TOKEN vault-installed
	@ echo -e "$(BUILD_PRINT)Create .env file $(END_BUILD_PRINT)"
	@ echo VAULT_ADDR=${VAULT_ADDR} > .env
	@ echo VAULT_TOKEN=${VAULT_TOKEN} >> .env
	@ echo DOMAIN=localhost >> .env
	@ echo ENVIRONMENT=dev >> .env
	@ echo SUBDOMAIN= >> .env
	@ echo RML_MAPPER_PATH=${RML_MAPPER_PATH} >> .env
	@ echo XML_PROCESSOR_PATH=${XML_PROCESSOR_PATH} >> .env
	@ echo AIRFLOW_INFRA_FOLDER=${AIRFLOW_INFRA_FOLDER} >> .env
	@ echo AIRFLOW_WORKER_HOSTNAME=${HOSTNAME} >> .env
	@ vault kv get -format="json" ted-data-dev/airflow | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/mongo-db | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/agraph | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/metabase | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/fuseki | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/graphdb | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/elk | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/ted-sws | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/postgres-db | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/minio | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env


staging-dotenv-file: guard-VAULT_ADDR guard-VAULT_TOKEN vault-installed
	@ echo -e "$(BUILD_PRINT)Create .env file $(END_BUILD_PRINT)"
	@ echo VAULT_ADDR=${VAULT_ADDR} > .env
	@ echo VAULT_TOKEN=${VAULT_TOKEN} >> .env
	@ echo DOMAIN=ted-data.eu >> .env
	@ echo ENVIRONMENT=staging >> .env
	@ echo SUBDOMAIN=staging. >> .env
	@ echo RML_MAPPER_PATH=${RML_MAPPER_PATH} >> .env
	@ echo XML_PROCESSOR_PATH=${XML_PROCESSOR_PATH} >> .env
	@ echo AIRFLOW_INFRA_FOLDER=~/airflow-infra/ted-data-staging >> .env
	@ echo AIRFLOW_WORKER_HOSTNAME=${HOSTNAME} >> .env
	@ vault kv get -format="json" ted-data-dev/airflow | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/mongo-db | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/agraph | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/metabase | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/fuseki | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/graphdb | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/elk | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/ted-sws | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/postgres-db | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-dev/minio | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env

prod-dotenv-file: guard-VAULT_ADDR guard-VAULT_TOKEN vault-installed
	@ echo -e "$(BUILD_PRINT)Create .env file $(END_BUILD_PRINT)"
	@ echo VAULT_ADDR=${VAULT_ADDR} > .env
	@ echo VAULT_TOKEN=${VAULT_TOKEN} >> .env
	@ echo DOMAIN=ted-data.eu >> .env
	@ echo ENVIRONMENT=prod >> .env
	@ echo SUBDOMAIN= >> .env
	@ echo RML_MAPPER_PATH=${RML_MAPPER_PATH} >> .env
	@ echo XML_PROCESSOR_PATH=${XML_PROCESSOR_PATH} >> .env
	@ echo AIRFLOW_INFRA_FOLDER=~/airflow-infra/ted-data-prod >> .env
	@ echo AIRFLOW_WORKER_HOSTNAME=${HOSTNAME} >> .env
	@ echo AIRFLOW_CELERY_WORKER_CONCURRENCY=1 >> .env
	@ vault kv get -format="json" ted-data-prod/airflow | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/minio | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/metabase | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/mongo-db | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/fuseki | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/graphdb | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/elk | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/ted-sws | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/postgres-db | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env
	@ vault kv get -format="json" ted-data-prod/agraph | jq -r ".data.data | keys[] as \$$k | \"\(\$$k)=\(.[\$$k])\"" >> .env

local-dotenv-file: rml-mapper-path-add-dotenv-file

rml-mapper-path-add-dotenv-file:
	@ echo -e "$(BUILD_PRINT)Add rml-mapper path to local .env file $(END_BUILD_PRINT)"
	@ sed -i '/^RML_MAPPER_PATH/d' .env
	@ echo RML_MAPPER_PATH=${RML_MAPPER_PATH} >> .env


install-allure:
	@ echo -e "Start install Allure commandline."
	@ sudo apt -y install npm
	@ sudo npm install -g allure-commandline

create-env-digest-api:
	@ cp requirements.txt ./infra/digest_api/digest_service/project_requirements.txt
	@ mkdir "temp" && cd temp && git clone https://github.com/OP-TED/ted-rdf-conversion-pipeline.git
	@ cp -r temp/ted-rdf-conversion-pipeline/ted_sws ./infra/digest_api/
	@ rm -rf temp

build-digest_service-api: create-env-digest-api
	@ echo -e "$(BUILD_PRINT) Build digest_service API service $(END_BUILD_PRINT)"
	@ docker-compose -p common --file infra/digest_api/docker-compose.yml --env-file ${ENV_FILE} build --no-cache --force-rm
	@ rm -rf ./infra/digest_api/ted_sws || true
	@ docker-compose -p common --file infra/digest_api/docker-compose.yml --env-file ${ENV_FILE} up -d --force-recreate

start-digest_service-api:
	@ echo -e "$(BUILD_PRINT)Starting digest_service API service $(END_BUILD_PRINT)"
	@ docker-compose -p common --file infra/digest_api/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-digest_service-api:
	@ echo -e "$(BUILD_PRINT)Stopping digest_service API service $(END_BUILD_PRINT)"
	@ docker-compose -p common --file infra/digest_api/docker-compose.yml --env-file ${ENV_FILE} down

start-mongo: build-externals
	@ echo -e "$(BUILD_PRINT)Starting the Mongo services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/mongo/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-mongo:
	@ echo -e "$(BUILD_PRINT)Stopping the Mongo services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/mongo/docker-compose.yml --env-file ${ENV_FILE} down

start-graphdb: build-externals
	@ echo -e "$(BUILD_PRINT)Starting the GraphDB services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/graphdb/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-graphdb:
	@ echo -e "$(BUILD_PRINT)Stopping the GraphDB services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/graphdb/docker-compose.yml --env-file ${ENV_FILE} down

start-elk: build-externals
	@ echo -e "$(BUILD_PRINT)Starting the ELK services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/elk/docker-compose.yml --env-file ${ENV_FILE} up -d --build

stop-elk:
	@ echo -e "$(BUILD_PRINT)Stopping the ELK services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/elk/docker-compose.yml --env-file ${ENV_FILE} down

start-grafana: build-externals
	@ echo -e "$(BUILD_PRINT)Starting the Grafana services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/grafana/docker-compose.yml --env-file ${ENV_FILE} up -d

stop-grafana:
	@ echo -e "$(BUILD_PRINT)Stopping the Grafana services $(END_BUILD_PRINT)"
	@ docker-compose -p ${ENVIRONMENT} --file ./infra/grafana/docker-compose.yml --env-file ${ENV_FILE} down