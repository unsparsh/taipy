import pytest

from taipy.core.common.frequency import Frequency
from taipy.core.config.config import Config
from taipy.core.data.scope import Scope
from taipy.core.exceptions.exceptions import InvalidConfigurationId, LoadingError
from tests.core.config.named_temporary_file import NamedTemporaryFile


def test_read_error_node_can_not_appear_twice():
    config = NamedTemporaryFile(
        """
[JOB]
nb_of_workers = 40

[JOB]
parallel_execution = true
nb_of_workers = 10
    """
    )

    with pytest.raises(LoadingError, match="Can not load configuration"):
        Config._load(config.filename)


def test_read_skip_configuration_outside_nodes():
    config = NamedTemporaryFile(
        """
nb_of_workers = 10
    """
    )

    Config._load(config.filename)

    assert not Config.job_config.parallel_execution
    assert Config.job_config.nb_of_workers == 1


def test_write_configuration_file():
    expected_config = """
[TAIPY]
root_folder = "./taipy/"
storage_folder = ".data/"
clean_entities_enabled = true

[JOB]
mode = "standalone"
nb_of_workers = 1

[DATA_NODE.default]
storage_type = "in_memory"
scope = "SCENARIO"
cacheable = false
custom = "default_custom_prop"

[DATA_NODE.dn1]
storage_type = "pickle"
scope = "PIPELINE"
cacheable = false
custom = "custom property"
default_data = "dn1"

[DATA_NODE.dn2]
storage_type = "in_memory"
scope = "SCENARIO"
cacheable = false
custom = "default_custom_prop"
foo = "bar"
default_data = "dn2"

[TASK.default]
inputs = []
outputs = []

[TASK.t1]
inputs = [ "dn1",]
function = "<built-in function print>"
outputs = [ "dn2",]
description = "t1 description"

[PIPELINE.default]
tasks = []

[PIPELINE.p1]
tasks = [ "t1",]
cron = "daily"

[SCENARIO.default]
pipelines = []
frequency = "QUARTERLY"
owner = "Michel Platini"

[SCENARIO.s1]
pipelines = [ "p1",]
frequency = "QUARTERLY"
owner = "Raymond Kopa"
    """.strip()

    Config._set_global_config(clean_entities_enabled=True)
    Config._set_job_config(mode="standalone")
    Config._add_default_data_node(storage_type="in_memory", custom="default_custom_prop")
    dn1_cfg_v2 = Config._add_data_node(
        "dn1", storage_type="pickle", scope=Scope.PIPELINE, default_data="dn1", custom="custom property"
    )
    dn2_cfg_v2 = Config._add_data_node("dn2", storage_type="in_memory", foo="bar", default_data="dn2")
    t1_cfg_v2 = Config._add_task("t1", print, dn1_cfg_v2, dn2_cfg_v2, description="t1 description")
    p1_cfg_v2 = Config._add_pipeline("p1", t1_cfg_v2, cron="daily")
    Config._add_default_scenario([], Frequency.QUARTERLY, owner="Michel Platini")
    Config._add_scenario("s1", p1_cfg_v2, frequency=Frequency.QUARTERLY, owner="Raymond Kopa")
    tf = NamedTemporaryFile()
    Config._export(tf.filename)
    actual_config = tf.read().strip()

    assert actual_config == expected_config


def test_all_entities_use_valid_id():
    file_config = NamedTemporaryFile(
        """
        [DATA_NODE.default]
        has_header = true

        [DATA_NODE.my_datanode]
        path = "/data/csv"

        [DATA_NODE.my_datanode2]
        path = "/data2/csv"

        [TASK.my_task]
        inputs = ["my_datanode"]
        function = "<built-in function print>"
        outputs = ["my_datanode2"]
        description = "task description"

        [PIPELINE.my_pipeline]
        tasks = [ "my_Task",]
        cron = "daily"

        [SCENARIO.my_scenario]
        pipelines = [ "my_pipeline",]
        owner = "John Doe"
        """
    )
    Config._load(file_config.filename)
    data_node_1_config = Config._add_data_node(id="my_datanode")
    data_node_2_config = Config._add_data_node(id="my_datanode2")
    task_config = Config._add_task("my_task", print, data_node_1_config, data_node_2_config)
    pipeline_config = Config._add_pipeline("my_pipeline", task_config)
    Config._add_scenario("my_scenario", pipeline_config)

    assert len(Config.data_nodes) == 3
    assert Config.data_nodes["my_datanode"].path == "/data/csv"
    assert Config.data_nodes["my_datanode2"].path == "/data2/csv"
    assert Config.data_nodes["my_datanode"].id == "my_datanode"
    assert Config.data_nodes["my_datanode2"].id == "my_datanode2"

    assert len(Config.tasks) == 2
    assert Config.tasks["my_task"].id == "my_task"
    assert Config.tasks["my_task"].description == "task description"

    assert len(Config.pipelines) == 2
    assert Config.pipelines["my_pipeline"].id == "my_pipeline"
    assert Config.pipelines["my_pipeline"].cron == "daily"

    assert len(Config.scenarios) == 2
    assert Config.scenarios["my_scenario"].id == "my_scenario"
    assert Config.scenarios["my_scenario"].owner == "John Doe"


def test_all_entities_use_invalid_id():
    file_config = NamedTemporaryFile(
        """
        [DATA_NODE.default]
        has_header = true

        [DATA_NODE.1y_datanode]
        path = "/data/csv"

        [DATA_NODE.1y_datanode2]
        path = "/data2/csv"

        [TASK.my_task]
        inputs = ["1y_datanode"]
        function = "<built-in function print>"
        outputs = ["1y_datanode2"]
        description = "task description"

        [PIPELINE.1y_pipeline]
        tasks = [ "1y_Task",]
        cron = "daily"

        [SCENARIO.1y_scenario]
        pipelines = [ "1y_pipeline",]
        owner = "John Doe"
        """
    )
    with pytest.raises(InvalidConfigurationId):
        Config._load(file_config.filename)
