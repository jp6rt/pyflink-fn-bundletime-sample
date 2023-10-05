# Pyflink 1.15 kinesis connectors latency

## Setup

### Prerequisites

- Ensure you can retrieve temporary credentials with access to the kinesis streams and export the short lived credentials as environment variables. This will be passed to the docker container that will host the job and task managers.

### Create the streams

```
aws kinesis create-stream --stream-name flink-source --shard-count 1 --region ap-southeast-1
aws kinesis create-stream --stream-name flink-sink --shard-count 1 --region ap-southeast-1
```

### Running the job and task managers (For local prototyping)

```sh
# Create a network for flink
docker network create flink-network

# Export the AWS temporary credentials
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_SESSION_TOKEN=""

# Run the containers in detached state
# Ensure you are in the root project folder to make sure the app binding works
docker compose up -d

# ssh to the docker container that host the job manager
docker exec -it container_id bash
cd /app
flink run -py app.py --pyFiles /app/deps
```

### Local kcl

```bash
pushd kcl

# Add venv if it doesn't exist. Use conda if preffered
python3.8 -m venv venv
. venv/bin/activate

python setup.py download_jars
python setup.py install

# Run the app
`amazon_kclpy_helper.py --print_command --java /usr/bin/java --properties myapp/myapp.properties` | cut -b 167- | grep kcl_log
```

## Packaging app for data analytics

### zip and upload

```bash
pushd app
zip -r FlinkApp.zip app.py lib deps
aws s3 cp FlinkApp.zip s3://yourbucket/prefix/FlinkApp.zip
popd
```

### Runtime properties

Copy these values to the flink runtime properties and adjust as needed.

```
[
  {
    "PropertyGroupId": "kinesis.analytics.flink.run.options",
    "PropertyMap": {
      "python": "app.py",
      "jarfile": "lib/flink-sql-connector-kinesis-1.15.4.jar"
    }
  },
  {
    "PropertyGroupId": "consumer.config.0",
    "PropertyMap": {
      "input.stream.name": "flink-source",
      "flink.stream.initpos": "LATEST",
      "aws.region": "ap-southeast-1",
      "flink.stream.recordpublisher": "EFO",
      "flink.stream.efo.consumername": "flink-efo-consumer"
    }
  },
  {
    "PropertyGroupId": "producer.config.0",
    "PropertyMap": {
      "output.stream.name": "flink-sink",
      "shard.count": "1",
      "aws.region": "ap-southeast-1"
    }
  }
]
```  
