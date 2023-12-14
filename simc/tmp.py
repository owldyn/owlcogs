import time

import yaml
from kubernetes import client, config, watch

JOB_NAME = "simple-job"


def create_job_object():
    container = client.V1Container(name="busybox", image="busybox", args=["sleep", "6"])
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"name": "simple-job"}),
        spec=client.V1PodSpec(restart_policy="OnFailure", containers=[container]),
    )
    spec = client.V1JobSpec(template=template)
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=JOB_NAME),
        spec=spec,
    )
    return job


def create_job(api_instance, job):
    api_response = api_instance.create_namespaced_job(body=job, namespace="default")
    print("Job created. status='%s'" % str(api_response.status))


def delete_job(api_instance):
    api_response = api_instance.delete_namespaced_job(
        name=JOB_NAME,
        namespace="default",
        body=client.V1DeleteOptions(
            propagation_policy="Foreground", grace_period_seconds=0
        ),
    )
    print("Job deleted. status='%s'" % str(api_response.status))


config.load_incluster_config()
batch_v1 = client.BatchV1Api()
job = create_job_object()
create_job(batch_v1, job)
# time.sleep(10)
# delete_job(batch_v1)
