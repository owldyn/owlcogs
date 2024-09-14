import asyncio
import logging
import time
from typing import Optional, cast

import yaml
from kubernetes import client, config, watch

try:
    config.load_incluster_config()
except Exception:
    config.load_kube_config("/workspaces/owlcogs/redbotdata/kube.config")


log = logging.getLogger("Kubernetes")


class KubernetesWrapper:
    def __init__(self, namespace: str, pvc_name: str) -> None:
        self.api = client.BatchV1Api()
        self.namespace = namespace
        self.pvc_name = pvc_name

    def create_job_object(self, name: str, args: Optional[list] = None):
        args_dict = {"args": args} if args else {}
        volume = client.V1Volume(
            name="redbot-simc",
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                "redbot-simc"
            ),
        )
        vol_mount = client.V1VolumeMount("/mnt/simc/", name="redbot-simc")
        container = client.V1Container(
            name=f"simc-{name}",
            image="simulationcraftorg/simc:latest",
            volume_mounts=[vol_mount],
            image_pull_policy="Always",
            **args_dict,
        )
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"name": name}),
            spec=client.V1PodSpec(
                restart_policy="Never",
                containers=[container],
                volumes=[volume],
            ),
        )
        spec = client.V1JobSpec(
            template=template, backoff_limit=2, ttl_seconds_after_finished=3000
        )
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=name),
            spec=spec,
        )
        return self.api.create_namespaced_job(body=job, namespace=self.namespace)

    async def watch(self, job: client.V1Job):
        times = 0
        wait = 5
        # fail loop at 1200 seconds (20 minutes) so it doesn't hang indefinitely.
        while times < 1200:
            for jorb in self.api.list_namespaced_job(self.namespace).items:
                if not jorb.metadata:
                    continue
                if jorb.metadata.name == job.metadata.name:
                    if (
                        jorb.status.completion_time
                        or jorb.status.succeeded
                        or jorb.status.failed
                    ):
                        return True
                    else:
                        continue
            await asyncio.sleep(wait)
            times += wait
        return False

    def delete_job(self, name: str):
        return self.api.delete_namespaced_job(
            name=name,
            namespace=self.namespace,
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=0
            ),
        )
