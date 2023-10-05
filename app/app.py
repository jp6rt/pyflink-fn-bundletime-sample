import os
import json
from datetime import datetime, timedelta
from pyflink.datastream import StreamExecutionEnvironment, RuntimeExecutionMode
from pyflinkkinesis.kinesis import (
    FlinkKinesisConsumer,
    KinesisStreamsSink,
    PartitionKeyGenerator,
)

from pyflink.common import SimpleStringSchema
from pyflink.datastream.functions import MapFunction
from pyflink.common.typeinfo import Types


def get_application_properties(json_path):
    if os.path.isfile(json_path):
        with open(json_path, "r") as file:
            contents = file.read()
            properties = json.loads(contents)
            return properties
    else:
        print('A file at "{}" was not found'.format(json_path))


def property_map(props, property_group_id):
    for prop in props:
        if prop["PropertyGroupId"] == property_group_id:
            return prop["PropertyMap"]

class AddTimestampFunction(MapFunction):
    def map(self, value):
        value['flink_processing_eventtime'] = (datetime.now() + timedelta()).isoformat()
        return value

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_runtime_mode(RuntimeExecutionMode.STREAMING)

    properties_json_path = "/etc/flink/application_properties.json"  # on kda
    is_local = (
        True if os.environ.get("IS_LOCAL") else False
    )  # set this env var in your local environment or in PyCharm run configuration.

    if is_local:
        # only for local, overwrite variable to properties and pass in your jars delimited by a semicolon (;)
        CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
        properties_json_path = "application_properties.json"  # relative OK?
        jar_file = f"file:///{CURRENT_DIR}/lib/flink-sql-connector-kinesis-1.15.4.jar"
        env.add_jars(jar_file)

    props = get_application_properties(properties_json_path)

    input_property_map = property_map(props, "consumer.config.0")
    
    kinesis_consumer = FlinkKinesisConsumer(
        input_property_map["input.stream.name"],
        SimpleStringSchema(),  # DeserializationSchema.
        input_property_map
    )

    ds = (
        env.add_source(kinesis_consumer)
        .map(lambda x: json.loads(x))
        .map(AddTimestampFunction())
        .key_by(lambda x: x["session_id"])
        .map(lambda x: json.dumps(x), output_type=Types.STRING())
    )

    output_property_map = property_map(props, "producer.config.0")

    kds_sink = (
        KinesisStreamsSink.builder()
        .set_kinesis_client_properties(output_property_map)
        .set_serialization_schema(SimpleStringSchema())
        .set_partition_key_generator(PartitionKeyGenerator.random())
        .set_stream_name(output_property_map["output.stream.name"])
        .set_fail_on_error(True)
        # .set_max_batch_size(500) 
        # .set_max_in_flight_requests(50)
        # .set_max_buffered_requests(10000)
        # .set_max_batch_size_in_bytes(5 * 1024 * 1024)
        # .set_max_time_in_buffer_ms(5000) 
        # .set_max_record_size_in_bytes(1 * 1024 * 1024)
        .build()
    )
    ds.sink_to(kds_sink)


    # ds.print()
    env.execute("latency_tests")

# Binding test comment.
if __name__ == "__main__":
    main()
